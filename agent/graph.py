"""
LangGraph agent for the Chef Agent.

This module implements the main agent workflow using LangGraph
with nodes for planning, tool execution, and response generation.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from domain.entities import MealPlan

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from adapters.i18n import translate
from adapters.llm import LLMFactory
from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from agent.memory import MemoryManager
from agent.models import (
    AgentState,
    ChatRequest,
    ChatResponse,
    ConversationState,
)
from agent.simple_memory import SimpleMemorySaver
from agent.tools import create_chef_tools
from prompts import prompt_loader


class ChefAgentGraph:
    """Main LangGraph agent for the Chef Agent."""

    def __init__(
        self,
        llm_provider: str,
        api_key: str,
        mcp_client: Optional[ChefAgentHTTPMCPClient] = None,
        model: Optional[str] = None,
    ):
        """Initialize the agent graph."""
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.mcp_client = mcp_client
        self.memory_manager = MemoryManager()
        # Use simple memory saver for LangGraph compatibility
        self.memory_manager.memory_saver = SimpleMemorySaver()

        # Initialize LLM using factory
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            api_key=api_key,
            model=model,
            temperature=0.7,
            max_tokens=2048,
        )

        # Create tools (with fallback when no MCP client)
        self.tools = create_chef_tools(mcp_client)
        print(
            f"DEBUG: Agent has {len(self.tools)} tools: "
            f"{[tool.name for tool in self.tools]}"
        )
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Create tool node
        self.tool_node = ToolNode(self.tools)

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("tools", self._tools_node)
        workflow.add_node("responder", self._responder_node)

        # Add edges
        workflow.add_edge("planner", "tools")
        workflow.add_edge("tools", "responder")
        workflow.add_edge("responder", END)

        # Set entry point
        workflow.set_entry_point("planner")

        # Compile with memory
        return workflow.compile(
            checkpointer=self.memory_manager.memory_saver,
        )

    async def _planner_node(self, state: AgentState) -> AgentState:
        """Plan the agent's actions based on user input and current state."""
        try:
            # Extract user input
            user_message = self._extract_user_input(state)

            # Process based on current conversation state
            if state.conversation_state == ConversationState.INITIAL:
                return await self._handle_initial_state(state, user_message)
            elif (
                state.conversation_state == ConversationState.WAITING_FOR_DIET
            ):
                return await self._handle_diet_input(state, user_message)
            elif (
                state.conversation_state == ConversationState.WAITING_FOR_DAYS
            ):
                return await self._handle_days_input(state, user_message)
            elif state.conversation_state == ConversationState.GENERATING_PLAN:
                print("Calling _handle_plan_generation")
                return await self._handle_plan_generation(state)
            elif (
                state.conversation_state
                == ConversationState.WAITING_FOR_RECIPE_REPLACEMENT
            ):
                return await self._handle_recipe_replacement_input(
                    state, user_message
                )
            elif state.conversation_state == ConversationState.COMPLETED:
                # Handle completed state - should not happen in normal flow
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            "The meal plan is already completed. "
                            "Please start a new conversation if you need "
                            "another meal plan."
                        ),
                    }
                )
                return state
            else:
                # This should not happen - log error and handle gracefully
                state.error = (
                    f"Unknown conversation state: {state.conversation_state}"
                )
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            "I encountered an unexpected error. "
                            "Please try again or start a new conversation."
                        ),
                    }
                )
                return state

        except asyncio.TimeoutError as e:
            state.error = f"Planning timeout: {str(e)}"
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        "I apologize, but the request timed out. "
                        "Please try again with a simpler request."
                    ),
                }
            )
            return state
        except Exception as e:
            state.error = f"Planning error: {str(e)}"
            return state

    def _extract_user_input(self, state: AgentState) -> str:
        """Extract user message from state."""
        return state.messages[-1]["content"] if state.messages else ""

    async def _handle_initial_state(
        self, state: AgentState, user_message: str
    ) -> AgentState:
        """Handle initial conversation state - ask about diet goals."""
        # Check if user already provided diet information
        diet_goal = self._extract_diet_goal(user_message)
        if diet_goal:
            state.diet_goal = diet_goal

            # Check if user also provided days count
            days_count, is_valid = self._extract_days_count(user_message)
            if days_count and is_valid:
                state.days_count = days_count
                state.conversation_state = ConversationState.GENERATING_PLAN
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"Perfect! I'll create a {diet_goal} meal plan "
                            f"for {days_count} days. Let me work on that for you."
                        ),
                    }
                )

                # Immediately try to generate meal plan
                return await self._handle_plan_generation(state)
            else:
                state.conversation_state = ConversationState.WAITING_FOR_DAYS
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"Great! I see you're interested in {diet_goal} "
                            f"meals. How many days would you like me to plan for? "
                            f"(3-7 days)"
                        ),
                    }
                )
        else:
            state.conversation_state = ConversationState.WAITING_FOR_DIET
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        "I'd be happy to help you plan your meals! "
                        "What are your dietary goals? For example: "
                        "vegetarian, vegan, low-carb, high-protein, keto, "
                        "gluten-free, or mediterranean?"
                    ),
                }
            )
        return state

    async def _handle_diet_input(
        self, state: AgentState, user_message: str
    ) -> AgentState:
        """Handle diet goal input."""
        diet_goal = self._extract_diet_goal(user_message)
        if diet_goal:
            state.diet_goal = diet_goal
            state.conversation_state = ConversationState.WAITING_FOR_DAYS
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        f"Perfect! I'll help you plan {diet_goal} meals. "
                        f"How many days would you like me to plan for? "
                        f"(3-7 days)"
                    ),
                }
            )
        else:
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        "I didn't quite catch your dietary preference. "
                        "Could you please specify? For example: vegetarian, "
                        "vegan, low-carb, high-protein, keto, gluten-free, "
                        "or mediterranean?"
                    ),
                }
            )
        return state

    async def _handle_days_input(
        self, state: AgentState, user_message: str
    ) -> AgentState:
        """Handle days count input."""
        days_count, is_valid = self._extract_days_count(user_message)

        if days_count is not None and is_valid:
            # Valid number in range 3-7
            state.days_count = days_count
            state.conversation_state = ConversationState.GENERATING_PLAN
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        f"Excellent! I'll create a {days_count}-day "
                        f"{state.diet_goal} meal plan for you. Let me search "
                        f"for suitable recipes..."
                    ),
                }
            )
            # Trigger recipe search
            state.tool_calls = [
                {
                    "name": "search_recipes",
                    "args": {"diet_type": state.diet_goal, "limit": 20},
                }
            ]
        elif days_count is not None and not is_valid:
            # Found a number but it's not in valid range
            if days_count < 3:
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"I see you mentioned {days_count} days, but I need "
                            f"at least 3 days to create a meaningful meal plan. "
                            f"Please choose 3 to 7 days."
                        ),
                    }
                )
            else:
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"I see you mentioned {days_count} days, but I can "
                            f"only plan for 3 to 7 days. Please choose a number "
                            f"between 3 and 7 days."
                        ),
                    }
                )
            # Keep the same conversation state to ask again
            state.conversation_state = ConversationState.WAITING_FOR_DAYS
        else:
            # No number found at all
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        "I didn't catch the number of days. Please specify "
                        "how many days you'd like me to plan for (between 3 "
                        "and 7 days)."
                    ),
                }
            )
            # Keep conversation state as WAITING_FOR_DAYS to allow retry
            state.conversation_state = ConversationState.WAITING_FOR_DAYS
        return state

    async def _handle_plan_generation(self, state: AgentState) -> AgentState:
        """Handle meal plan generation after recipes are found."""
        print(
            f"Handle plan generation - found_recipes: "
            f"{len(state.found_recipes) if state.found_recipes else 0}"
        )
        print(f"Days count: {state.days_count}")
        print(f"Conversation state: {state.conversation_state}")

        # If we have recipes and days count, generate the meal plan
        if state.found_recipes and state.days_count is not None:
            try:
                from domain.meal_plan_generator import MealPlanGenerator

                meal_plan, fallback_used = (
                    MealPlanGenerator.generate_meal_plan(
                        recipes=state.found_recipes,
                        diet_goal=state.diet_goal,
                        days_count=state.days_count,
                    )
                )
                state.menu_plan = meal_plan
                state.fallback_used = fallback_used
                state.conversation_state = ConversationState.COMPLETED

                # Generate shopping list
                state.tool_calls = [
                    {
                        "name": "create_shopping_list",
                        "args": {
                            "thread_id": state.thread_id,
                        },
                    }
                ]

                # Add ingredients from meal plan to shopping list
                ingredients = []
                for day in meal_plan.days:
                    for meal in day.meals:
                        for ingredient in meal.recipe.ingredients:
                            ingredients.append(
                                {
                                    "name": ingredient.name,
                                    "quantity": ingredient.quantity,
                                    "unit": ingredient.unit,
                                    "category": "general",
                                }
                            )

                if ingredients:
                    state.tool_calls.append(
                        {
                            "name": "add_to_shopping_list",
                            "args": {
                                "thread_id": state.thread_id,
                                "items": ingredients,
                            },
                        }
                    )

                print(f"Generated meal plan with {len(meal_plan.days)} days")
                return state

            except ValueError as e:
                state.error = str(e)
                state.conversation_state = ConversationState.COMPLETED
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"I'm sorry, but I couldn't generate a meal plan: {e}. "
                            "Please try a different diet goal or contact support."
                        ),
                    }
                )
                return state
            except Exception as e:
                state.error = f"Meal plan generation failed: {str(e)}"
                state.conversation_state = ConversationState.COMPLETED
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"I'm sorry, but I encountered an error while generating "
                            f"your meal plan: {str(e)}"
                        ),
                    }
                )
                return state

        # If no recipes found, create them directly
        if not state.found_recipes:
            if state.recipe_search_attempts < 2:
                state.recipe_search_attempts += 1

                # Start recipe search
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            "I'm searching for recipes for your meal plan. "
                            "Please wait..."
                        ),
                    }
                )
                state.tool_calls = [
                    {
                        "name": "search_recipes",
                        "args": {
                            "diet_type": state.diet_goal,
                            "limit": 20,
                        },
                    }
                ]

                # Execute search_recipes immediately
                try:
                    search_tool = None
                    for tool in self.tools:
                        if tool.name == "search_recipes":
                            search_tool = tool
                            break

                    if search_tool:
                        result = await search_tool.ainvoke(
                            {
                                "diet_type": state.diet_goal,
                                "limit": 20,
                            }
                        )

                        # Check if recipes were found
                        if (
                            result
                            and result.get("success")
                            and result.get("recipes")
                        ):
                            state.found_recipes = result["recipes"]
                            print(f"Found {len(state.found_recipes)} recipes")
                        else:
                            print("No recipes found, will create them")
                            # Don't increment here, just proceed to creation
                except Exception as e:
                    print(f"Search failed: {e}")
                    state.recipe_search_attempts = 2  # Skip to creation

            # If still no recipes after search attempts, create them
            if not state.found_recipes and state.recipe_search_attempts >= 1:
                print("Creating custom recipes...")
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            f"I couldn't find existing recipes for your "
                            f"{state.diet_goal} meal plan, so I'll create some "
                            f"custom recipes for you!"
                        ),
                    }
                )

                # Create custom recipes for the meal plan
                state.tool_calls = []
                # Create 6-9 base recipes that can be used across all days
                import time

                timestamp = int(time.time())
                base_recipes = [
                    (
                        f"Vegetarian Breakfast Bowl {timestamp}",
                        "A nutritious vegetarian breakfast with grains and vegetables",
                    ),
                    (
                        f"Vegetarian Lunch Salad {timestamp}",
                        "A fresh and healthy vegetarian salad",
                    ),
                    (
                        f"Vegetarian Dinner Pasta {timestamp}",
                        "A hearty vegetarian pasta dish",
                    ),
                    (
                        f"Vegetarian Soup {timestamp}",
                        "A warming vegetarian soup",
                    ),
                    (
                        f"Vegetarian Stir Fry {timestamp}",
                        "A quick and easy vegetarian stir fry",
                    ),
                    (
                        f"Vegetarian Curry {timestamp}",
                        "A flavorful vegetarian curry",
                    ),
                    (
                        f"Vegetarian Sandwich {timestamp}",
                        "A satisfying vegetarian sandwich",
                    ),
                    (
                        f"Vegetarian Wrap {timestamp}",
                        "A healthy vegetarian wrap",
                    ),
                    (
                        f"Vegetarian Smoothie {timestamp}",
                        "A refreshing vegetarian smoothie",
                    ),
                ]

                for i, (title, description) in enumerate(
                    base_recipes[:6]
                ):  # Use first 6 recipes
                    recipe_instructions = (
                        f"Prepare this delicious {state.diet_goal} dish "
                        f"following standard cooking methods"
                    )

                    # Create basic ingredients based on diet type
                    ingredients = []
                    if state.diet_goal.lower() in ["vegetarian", "vegan"]:
                        ingredients = [
                            {
                                "name": "vegetables",
                                "quantity": "200",
                                "unit": "g",
                            },
                            {"name": "grains", "quantity": "100", "unit": "g"},
                            {"name": "herbs", "quantity": "1", "unit": "tbsp"},
                        ]
                    elif state.diet_goal.lower() in ["low-carb", "keto"]:
                        ingredients = [
                            {
                                "name": "protein",
                                "quantity": "150",
                                "unit": "g",
                            },
                            {
                                "name": "vegetables",
                                "quantity": "100",
                                "unit": "g",
                            },
                            {
                                "name": "healthy fats",
                                "quantity": "2",
                                "unit": "tbsp",
                            },
                        ]
                    else:
                        ingredients = [
                            {
                                "name": "main ingredient",
                                "quantity": "200",
                                "unit": "g",
                            },
                            {
                                "name": "seasoning",
                                "quantity": "1",
                                "unit": "tsp",
                            },
                            {"name": "oil", "quantity": "1", "unit": "tbsp"},
                        ]

                    state.tool_calls.append(
                        {
                            "name": "create_recipe",
                            "args": {
                                "title": title,
                                "description": description,
                                "instructions": recipe_instructions,
                                "diet_type": state.diet_goal,
                                "prep_time_minutes": 15,
                                "cook_time_minutes": 20,
                                "servings": 2,
                                "difficulty": "easy",
                                "ingredients": ingredients,
                                "user_id": "test_user",
                            },
                        }
                    )

                print(
                    f"Created {len(state.tool_calls)} recipe creation tool calls"
                )

                # Execute recipe creation immediately
                try:
                    created_recipes = []
                    create_tool = None
                    if self.tools:  # Only if tools are available
                        for tool in self.tools:
                            if tool.name == "create_recipe":
                                create_tool = tool
                                break

                    if create_tool:
                        # Use tool if available
                        for tool_call in state.tool_calls:
                            try:
                                result = await create_tool.ainvoke(
                                    tool_call["args"]
                                )
                                if result and result.get("success"):
                                    created_recipes.append(result["recipe"])
                            except Exception as e:
                                print(f"Tool creation failed: {e}")
                                # Fall back to direct database creation
                                pass

                    # If no recipes were created via tools, try direct database creation
                    if not created_recipes:
                        # Fallback: create recipes directly in database
                        from adapters.db.database import Database
                        from adapters.db.recipe_repository import (
                            SQLiteRecipeRepository,
                        )
                        from domain.entities import (
                            DietType,
                            Ingredient,
                            Recipe,
                        )

                        db = Database()
                        recipe_repo = SQLiteRecipeRepository(db)

                        for tool_call in state.tool_calls:
                            try:
                                args = tool_call["args"]

                                # Convert ingredients
                                ingredients = []
                                for ing_dict in args.get("ingredients", []):
                                    ingredients.append(
                                        Ingredient(
                                            name=ing_dict["name"],
                                            quantity=ing_dict["quantity"],
                                            unit=ing_dict["unit"],
                                        )
                                    )

                                # Convert diet_type string to DietType enum
                                diet_type_str = args.get(
                                    "diet_type", "regular"
                                )
                                diet_type = None
                                if diet_type_str.lower() == "vegetarian":
                                    diet_type = DietType.VEGETARIAN
                                elif diet_type_str.lower() == "vegan":
                                    diet_type = DietType.VEGAN
                                elif diet_type_str.lower() == "low-carb":
                                    diet_type = DietType.LOW_CARB
                                elif diet_type_str.lower() == "keto":
                                    diet_type = DietType.KETO
                                elif diet_type_str.lower() == "high-protein":
                                    diet_type = DietType.HIGH_PROTEIN
                                elif diet_type_str.lower() == "mediterranean":
                                    diet_type = DietType.MEDITERRANEAN
                                elif diet_type_str.lower() == "paleo":
                                    diet_type = DietType.PALEO
                                elif diet_type_str.lower() == "traditional":
                                    diet_type = DietType.TRADITIONAL
                                else:
                                    diet_type = DietType.REGULAR

                                # Create recipe object
                                recipe = Recipe(
                                    id=None,  # Will be set by database
                                    title=args["title"],
                                    description=args.get("description", ""),
                                    ingredients=ingredients,
                                    instructions=args.get("instructions", ""),
                                    prep_time_minutes=args.get(
                                        "prep_time_minutes"
                                    ),
                                    cook_time_minutes=args.get(
                                        "cook_time_minutes"
                                    ),
                                    servings=args.get("servings"),
                                    difficulty=args.get("difficulty"),
                                    diet_type=diet_type,
                                    user_id=args.get("user_id"),
                                    tags=args.get("tags", []),
                                    allergens=args.get("allergens", []),
                                )

                                # Save to database
                                saved_recipe = recipe_repo.save(recipe)
                                if saved_recipe:
                                    created_recipes.append(
                                        {
                                            "id": saved_recipe.id,
                                            "title": saved_recipe.title,
                                            "description": saved_recipe.description,
                                            "ingredients": [
                                                {
                                                    "name": ing.name,
                                                    "quantity": ing.quantity,
                                                    "unit": ing.unit,
                                                }
                                                for ing in saved_recipe.ingredients
                                            ],
                                            "instructions": saved_recipe.instructions,
                                            "prep_time_minutes": (
                                                saved_recipe.prep_time_minutes
                                            ),
                                            "cook_time_minutes": (
                                                saved_recipe.cook_time_minutes
                                            ),
                                            "servings": saved_recipe.servings,
                                            "difficulty": saved_recipe.difficulty,
                                            "diet_type": (
                                                saved_recipe.diet_type.value
                                                if saved_recipe.diet_type
                                                else "regular"
                                            ),
                                            "user_id": saved_recipe.user_id,
                                            "tags": saved_recipe.tags,
                                            "allergens": saved_recipe.allergens,
                                        }
                                    )
                            except Exception as e:
                                print(
                                    f"Failed to create recipe "
                                    f"{tool_call['args']['title']}: {e}"
                                )
                                continue

                    if created_recipes:
                        # Convert dict recipes to Recipe objects
                        from domain.entities import (
                            DietType,
                            Ingredient,
                            Recipe,
                        )

                        recipe_objects = []
                        for recipe_dict in created_recipes:
                            # Convert ingredients
                            ingredients = []
                            for ing_dict in recipe_dict.get("ingredients", []):
                                ingredients.append(
                                    Ingredient(
                                        name=ing_dict["name"],
                                        quantity=ing_dict["quantity"],
                                        unit=ing_dict["unit"],
                                    )
                                )

                            # Convert diet_type string to DietType enum
                            diet_type_str = recipe_dict.get(
                                "diet_type", "regular"
                            )
                            diet_type = None
                            if diet_type_str.lower() == "vegetarian":
                                diet_type = DietType.VEGETARIAN
                            elif diet_type_str.lower() == "vegan":
                                diet_type = DietType.VEGAN
                            elif diet_type_str.lower() == "low-carb":
                                diet_type = DietType.LOW_CARB
                            elif diet_type_str.lower() == "keto":
                                diet_type = DietType.KETO
                            elif diet_type_str.lower() == "high-protein":
                                diet_type = DietType.HIGH_PROTEIN
                            elif diet_type_str.lower() == "mediterranean":
                                diet_type = DietType.MEDITERRANEAN
                            elif diet_type_str.lower() == "paleo":
                                diet_type = DietType.PALEO
                            elif diet_type_str.lower() == "traditional":
                                diet_type = DietType.TRADITIONAL
                            else:
                                diet_type = DietType.REGULAR

                            recipe_obj = Recipe(
                                id=recipe_dict.get("id"),
                                title=recipe_dict["title"],
                                description=recipe_dict.get("description"),
                                ingredients=ingredients,
                                instructions=recipe_dict.get(
                                    "instructions", ""
                                ),
                                prep_time_minutes=recipe_dict.get(
                                    "prep_time_minutes"
                                ),
                                cook_time_minutes=recipe_dict.get(
                                    "cook_time_minutes"
                                ),
                                servings=recipe_dict.get("servings"),
                                difficulty=recipe_dict.get("difficulty"),
                                diet_type=diet_type,
                                user_id=recipe_dict.get("user_id"),
                                tags=recipe_dict.get("tags", []),
                                allergens=recipe_dict.get("allergens", []),
                            )
                            recipe_objects.append(recipe_obj)

                        state.found_recipes = recipe_objects
                        print(
                            f"Successfully created {len(recipe_objects)} recipe objects"
                        )

                        # Now generate meal plan with created recipes
                        try:
                            from domain.meal_plan_generator import (
                                MealPlanGenerator,
                            )

                            meal_plan, fallback_used = (
                                MealPlanGenerator.generate_meal_plan(
                                    recipes=state.found_recipes,
                                    diet_goal=state.diet_goal,
                                    days_count=state.days_count,
                                )
                            )
                            state.menu_plan = meal_plan
                            state.fallback_used = fallback_used
                            state.conversation_state = (
                                ConversationState.COMPLETED
                            )

                            print(
                                f"Generated meal plan with {len(meal_plan.days)} days"
                            )

                            # Generate shopping list
                            try:
                                # Create shopping list using built-in method
                                shopping_list = meal_plan.get_shopping_list()
                                state.shopping_list = shopping_list

                                print(
                                    f"Created shopping list with "
                                    f"{len(shopping_list.items)} items"
                                )

                            except Exception as e:
                                print(f"Shopping list creation failed: {e}")

                            return state

                        except Exception as e:
                            print(f"Meal plan generation failed: {e}")
                            state.error = (
                                f"Meal plan generation failed: {str(e)}"
                            )
                            state.conversation_state = (
                                ConversationState.COMPLETED
                            )
                            state.add_message(
                                {
                                    "role": "assistant",
                                    "content": (
                                        f"I'm sorry, but I encountered an error "
                                        f"while generating your meal plan: {str(e)}"
                                    ),
                                }
                            )
                            return state
                    else:
                        print("Failed to create recipes")
                        state.error = "Failed to create recipes"
                        state.conversation_state = ConversationState.COMPLETED
                        state.add_message(
                            {
                                "role": "assistant",
                                "content": (
                                    "I'm sorry, but I couldn't create recipes for your "
                                    "meal plan. Please try again or contact support."
                                ),
                            }
                        )
                        return state

                except Exception as e:
                    print(f"Recipe creation failed: {e}")

            # If we now have recipes, generate meal plan
            if state.found_recipes and state.days_count is not None:
                try:
                    from domain.meal_plan_generator import MealPlanGenerator

                    meal_plan, fallback_used = (
                        MealPlanGenerator.generate_meal_plan(
                            recipes=state.found_recipes,
                            diet_goal=state.diet_goal,
                            days_count=state.days_count,
                        )
                    )
                    state.menu_plan = meal_plan
                    state.fallback_used = fallback_used
                    state.conversation_state = ConversationState.COMPLETED

                    print(
                        f"Generated meal plan with {len(meal_plan.days)} days"
                    )

                    # Generate shopping list
                    try:
                        # Create shopping list using the meal plan's built-in method
                        shopping_list = meal_plan.get_shopping_list()
                        state.shopping_list = shopping_list

                        # Also try to create via MCP if available
                        shopping_tool = None
                        for tool in self.tools:
                            if tool.name == "create_shopping_list":
                                shopping_tool = tool
                                break

                        if shopping_tool:
                            await shopping_tool.ainvoke(
                                {
                                    "thread_id": state.thread_id,
                                }
                            )

                            # Add ingredients to shopping list
                            add_tool = None
                            for tool in self.tools:
                                if tool.name == "add_to_shopping_list":
                                    add_tool = tool
                                    break

                            if add_tool:
                                ingredients = []
                                for day in meal_plan.days:
                                    for meal in day.meals:
                                        for (
                                            ingredient
                                        ) in meal.recipe.ingredients:
                                            ingredients.append(
                                                {
                                                    "name": ingredient.name,
                                                    "quantity": ingredient.quantity,
                                                    "unit": ingredient.unit,
                                                    "category": "general",
                                                }
                                            )

                                if ingredients:
                                    await add_tool.ainvoke(
                                        {
                                            "thread_id": state.thread_id,
                                            "items": ingredients,
                                        }
                                    )
                                    print(
                                        f"Added {len(ingredients)} ingredients "
                                        f"to shopping list"
                                    )

                    except Exception as e:
                        print(f"Shopping list creation failed: {e}")

                    return state

                except Exception as e:
                    print(f"Meal plan generation failed: {e}")
                    state.error = f"Meal plan generation failed: {str(e)}"
                    state.conversation_state = ConversationState.COMPLETED
                    state.add_message(
                        {
                            "role": "assistant",
                            "content": (
                                f"I'm sorry, but I encountered an error while "
                                f"generating your meal plan: {str(e)}"
                            ),
                        }
                    )
                    return state

            return state

        # If we reach here with no recipes and no days count, handle error
        state.error = "Missing recipes or days count for meal plan generation"
        state.add_message(
            {
                "role": "assistant",
                "content": (
                    "I'm sorry, but I need both recipes and days count to create "
                    "a meal plan. Please try again."
                ),
            }
        )
        state.conversation_state = ConversationState.COMPLETED
        return state

    async def _handle_recipe_replacement_input(
        self, state: AgentState, user_message: str
    ) -> AgentState:
        """Handle recipe replacement retry input."""
        if not state.recipe_replacement_context:
            state.error = "Missing recipe replacement context"
            return state

        # Extract replacement details from context
        day_number = state.recipe_replacement_context.get("day_number")
        meal_type = state.recipe_replacement_context.get("meal_type")
        diet_type = state.recipe_replacement_context.get("diet_type")

        # Try to replace recipe with new query
        state.tool_calls = [
            {
                "name": "replace_recipe_in_meal_plan",
                "args": {
                    "day_number": day_number,
                    "meal_type": meal_type,
                    "new_query": user_message,
                    "thread_id": state.thread_id,
                    "diet_type": diet_type,
                },
            }
        ]

        return state

    async def _process_with_llm(
        self, state: AgentState, user_message: str
    ) -> AgentState:
        """Process with LLM for non-MVP flows."""
        messages = self._prepare_llm_messages(user_message, state.language)
        response = await self._call_llm(messages)
        self._update_state_from_llm(state, response)
        return state

    def _extract_diet_goal(self, message: str) -> Optional[str]:
        """Extract diet goal from user message using NLP."""
        message_lower = message.lower()

        # Extended diet keywords with natural language patterns
        diet_keywords = {
            "vegan": [
                "vegan",
                "no dairy",
                "no eggs",
                "no animal products",
                "plant only",
                "strict vegetarian",
            ],
            "vegetarian": [
                "vegetarian",
                "veggie",
                "no meat",
                "plant based",
                "vegetables only",
                "herbivore",
                "no animal products",
            ],
            "low-carb": [
                "low-carb",
                "low carb",
                "low carb",
                "lose weight",
                "weight loss",
                "slimming",
                "low sugar",
                "no carbs",
                "carb free",
                "atkins",
            ],
            "keto": [
                "keto",
                "ketogenic",
                "ketosis",
                "high fat",
                "low carb high fat",
            ],
            "high-protein": [
                "high-protein",
                "high protein",
                "protein",
                "muscle building",
                "gains",
                "bodybuilding",
                "protein rich",
                "lean protein",
            ],
            "gluten-free": [
                "gluten-free",
                "gluten free",
                "gluten",
                "celiac",
                "no gluten",
                "gluten intolerant",
                "wheat free",
            ],
            "mediterranean": [
                "mediterranean",
                "mediterranean",
                "olive oil",
                "fish",
                "heart healthy",
                "mediterranean diet",
            ],
            "paleo": [
                "paleo",
                "paleolithic",
                "caveman",
                "primal",
                "stone age",
                "ancestral",
                "hunter gatherer",
            ],
            "traditional": [
                "traditional",
                "traditional cooking",
                "traditional ukrainian",
                "traditional ukrainian cooking",
                "ukrainian cooking",
                "ukrainian cuisine",
                "classic",
                "classic cooking",
                "homestyle",
                "comfort food",
            ],
            "regular": [
                "regular",
                "normal",
                "balanced",
                "healthy",
                "general",
                "standard",
                "typical",
                "everyday",
                "family",
                "kids",
                "children",
            ],
        }

        # Check for exact matches first
        for diet, keywords in diet_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return diet

        # Check for weight loss patterns that might indicate low-carb
        weight_loss_patterns = [
            "lose weight",
            "weight loss",
            "slimming",
            "slim down",
            "diet",
            "healthy eating",
            "cut calories",
            "burn fat",
            "get in shape",
            "похудеть",
            "сбросить вес",
            "похудение",
            "диета для похудения",
            "здоровое питание",
            "сжигание жира",
        ]
        if any(pattern in message_lower for pattern in weight_loss_patterns):
            return "low-carb"

        # Check for muscle building patterns that might indicate high-protein
        muscle_patterns = [
            "build muscle",
            "muscle mass",
            "strength",
            "gains",
            "workout",
            "fitness",
            "gym",
            "training",
            "набрать мышечную массу",
            "тренировки",
            "качаться",
            "силовые тренировки",
        ]
        if any(pattern in message_lower for pattern in muscle_patterns):
            return "high-protein"

        # Check for general health patterns
        health_patterns = [
            "healthy",
            "health",
            "wellness",
            "balanced",
            "здоровый",
            "здоровье",
            "сбалансированное питание",
        ]
        if any(pattern in message_lower for pattern in health_patterns):
            return (
                "mediterranean"  # Default to Mediterranean for general health
            )

        return None

    def _extract_days_count(self, message: str) -> tuple[Optional[int], bool]:
        """Extract number of days from user message using natural language
        patterns.

        Returns:
            tuple: (number, is_valid) where is_valid indicates if number is in
                range 3-7
        """
        import re

        message_lower = message.lower()

        # Natural language patterns for days
        day_patterns = {
            "week": 7,
            "full week": 7,
            "entire week": 7,
            "whole week": 7,
            "weekend": 3,  # Map weekend to minimum valid days
            "few days": 5,  # Default to middle
            "several days": 5,
            "couple of days": 3,
            "couple days": 3,
            "short plan": 3,
            "long plan": 7,
        }

        # Check for natural language patterns first
        for pattern, days in day_patterns.items():
            if pattern in message_lower:
                return days, True

        # Look for numbers in the message with context
        # Pattern to find numbers that are likely to be days count
        day_context_patterns = [
            r"(\d+)\s*days?",  # "3 days", "5 day"
            r"(\d+)\s*day\s*plan",  # "3 day plan"
            r"(\d+)\s*day\s*meal",  # "3 day meal"
            r"for\s*(\d+)\s*days?",  # "for 3 days"
            r"(\d+)\s*days?\s*and",  # "3 days and" (but not "2 days and 5 nights")
            r"(\d+)\s*days?\s*of",  # "3 days of"
            r"(\d+)\s*days?\s*worth",  # "3 days worth"
        ]

        # Try context-aware patterns first
        for pattern in day_context_patterns:
            matches = re.findall(pattern, message_lower)
            if matches:
                num = int(matches[0])
                if 3 <= num <= 7:
                    return num, True
                elif num < 3:
                    # If number is too small, it's likely not the main days count
                    continue
                else:
                    # Number is too large, but might be the intended count
                    return num, False

        # Fallback: look for any numbers in the message
        numbers = re.findall(r"\b(\d+)\b", message)

        # First, try to find a valid number in range 3-7
        for num_str in numbers:
            num = int(num_str)
            if 3 <= num <= 7:
                return num, True

        # If no valid number found, return None instead of first invalid number
        return None, False

    def _prepare_llm_messages(self, user_message: str, language: str) -> list:
        """Prepare messages for LLM including system prompt."""
        system_prompt = self._create_system_prompt(language)

        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

    async def _call_llm(self, messages: list) -> Any:
        """Call LLM with prepared messages."""
        import asyncio

        # Set timeout for LLM calls (30 seconds)
        try:
            return await asyncio.wait_for(
                self.llm_with_tools.ainvoke(messages), timeout=30.0
            )
        except asyncio.TimeoutError as e:
            # Re-raise as TimeoutError to be handled by process_request
            raise asyncio.TimeoutError(
                "LLM call timed out after 30 seconds"
            ) from e

    def _update_state_from_llm(self, state: AgentState, response: Any) -> None:
        """Update state with LLM response and extract tool calls."""
        # Add assistant message to state
        state.add_message({"role": "assistant", "content": response.content})

        # Handle tool calls from LLM response
        if hasattr(response, "tool_calls") and response.tool_calls is not None:
            # Replace existing tool calls with new ones to avoid duplication
            state.tool_calls = response.tool_calls or []
        else:
            # Clear tool calls if no new ones provided
            state.tool_calls = []

    async def _tools_node(self, state: AgentState) -> AgentState:
        """Execute tool calls."""
        print(
            f"Tools node - tool calls: "
            f"{len(state.tool_calls) if state.tool_calls else 0}"
        )
        print(
            f"Found recipes: {len(state.found_recipes) if state.found_recipes else 0}"
        )
        print(f"Days count: {state.days_count}")

        if not getattr(state, "tool_calls", None):
            # If no tool calls but we have recipes and days, try to generate meal plan
            if (
                state.found_recipes
                and state.days_count
                and state.conversation_state
                == ConversationState.GENERATING_PLAN
            ):

                print(
                    "No tool calls but have recipes and days, generating meal plan..."
                )
                await self._generate_meal_plan_from_state(state)
                return state

            return state

        # Limit tool_calls to prevent memory leaks
        MAX_TOOL_CALLS = 10
        if len(state.tool_calls) > MAX_TOOL_CALLS:
            state.tool_calls = state.tool_calls[:MAX_TOOL_CALLS]

        # Execute tool calls
        tool_results = []
        failed_tools = []

        for tool_call in state.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})

            print(f"DEBUG: Executing tool: {tool_name} with args: {tool_args}")

            try:
                # Find and execute the tool
                tool_result = await self._execute_tool(tool_name, tool_args)
                tool_results.append(tool_result)
            except Exception as e:
                # Log the error and add it to results
                error_result = {
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e),
                    "result": None,
                }
                tool_results.append(error_result)
                failed_tools.append(tool_name)

        # Update state with tool results
        state.tool_results = tool_results

        # Handle failed tools
        if failed_tools:
            state.error = f"Failed to execute tools: {', '.join(failed_tools)}"
            # Continue execution to allow responder to handle errors gracefully

        # Process tool results for any additional actions
        for tool_result in tool_results:
            if tool_result.get("success"):
                print(
                    f"Tool {tool_result.get('tool_name', 'unknown')} "
                    f"executed successfully"
                )
            else:
                print(
                    f"Tool {tool_result.get('tool_name', 'unknown')} "
                    f"failed: {tool_result.get('error', 'unknown error')}"
                )

        # Clear tool_calls after execution to prevent memory leaks
        state.tool_calls = []

        return state

    async def _generate_meal_plan_from_state(self, state: AgentState) -> None:
        """Generate meal plan from existing state."""
        try:
            from domain.meal_plan_generator import MealPlanGenerator

            meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
                recipes=state.found_recipes,
                diet_goal=state.diet_goal or "regular",
                days_count=state.days_count,
            )

            state.menu_plan = meal_plan
            state.fallback_used = fallback_used
            state.conversation_state = ConversationState.COMPLETED

            print(f"Generated meal plan with {len(meal_plan.days)} days")

            # Generate shopping list
            if meal_plan:
                shopping_list = meal_plan.get_shopping_list()
                state.shopping_list = shopping_list

                # Create shopping list via MCP
                if self.mcp_client:
                    try:
                        # Create shopping list
                        await self.mcp_client.create_shopping_list(
                            state.thread_id
                        )

                        # Add ingredients
                        if shopping_list and shopping_list.items:
                            items_data = []
                            for item in shopping_list.items:
                                items_data.append(
                                    {
                                        "name": item.name,
                                        "quantity": item.quantity,
                                        "unit": item.unit,
                                        "category": getattr(
                                            item, "category", "general"
                                        ),
                                    }
                                )

                            if items_data:
                                await self.mcp_client.add_to_shopping_list(
                                    state.thread_id, items_data
                                )
                                print(
                                    f"Created shopping list with "
                                    f"{len(items_data)} items"
                                )
                    except Exception as e:
                        print(f"Failed to create shopping list via MCP: {e}")
                        # Don't fail the whole process if MCP fails

        except Exception as e:
            print(f"Meal plan generation failed: {e}")
            state.error = f"Meal plan generation failed: {str(e)}"
            state.conversation_state = ConversationState.COMPLETED

    async def _responder_node(self, state: AgentState) -> AgentState:
        """Generate final response based on tool results."""
        try:
            # Create response based on tool results
            response_content = await self._generate_response(state)

            # Update state
            state.add_message(
                {"role": "assistant", "content": response_content}
            )

            return state

        except Exception as e:
            state.error = f"Response generation error: {str(e)}"
            return state

    async def _execute_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific tool."""
        try:
            # Find the tool
            tool_func = None
            for tool in self.tools:
                if tool.name == tool_name:
                    tool_func = tool
                    break

            if not tool_func:
                print(
                    f"DEBUG: Tool {tool_name} not found, available tools: "
                    f"{[tool.name for tool in self.tools]}"
                )
                return {"error": f"Tool {tool_name} not found"}

            # Execute the tool
            result = await tool_func.ainvoke(tool_args)
            return result

        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    async def _generate_response(self, state: AgentState) -> str:
        """Generate response based on current state."""
        try:
            # Get language from the last user message or default to English
            language = "en"
            if state.messages:
                for msg in reversed(state.messages):
                    if msg.get("role") == "user" and "language" in msg:
                        language = msg.get("language", "en")
                        break

            # If there's an error, return error message
            if state.error:
                error_msg = translate("error_occurred", language)
                return f"{error_msg}: {state.error}"

            # If meal plan is completed, provide final response
            if (
                state.conversation_state == ConversationState.COMPLETED
                and state.menu_plan
            ):
                # If there are pending tool calls, process them first
                if state.tool_calls:
                    # Execute tool calls to create shopping list
                    tool_results = []
                    for tool_call in state.tool_calls:
                        try:
                            result = await self._execute_tool(
                                tool_call["name"], tool_call["args"]
                            )
                            tool_results.append(result)
                        except Exception as e:
                            tool_results.append(
                                {
                                    "success": False,
                                    "error": str(e),
                                    "tool_name": tool_call["name"],
                                }
                            )

                    # Update state with tool results
                    state.tool_results = tool_results
                    state.tool_calls = []  # Clear tool calls

                    # Process tool results to populate shopping list
                    for tool_result in tool_results:
                        if (
                            tool_result.get("success")
                            and "shopping_list" in tool_result
                        ):
                            state.shopping_list = tool_result["shopping_list"]
                            break

                response_content = self._generate_meal_plan_response(
                    state, language
                )
                # Add the response to messages so it appears in API response
                state.add_message(
                    {"role": "assistant", "content": response_content}
                )
                return response_content

            # If we have tool results, process them
            if hasattr(state, "tool_results") and state.tool_results:
                return await self._process_tool_results(state)

            # Handle different conversation states
            if state.conversation_state == ConversationState.WAITING_FOR_DAYS:
                # Return the message that was already added by planner
                if state.messages and len(state.messages) >= 2:
                    return state.messages[-1]["content"]
                else:
                    return (
                        "Great! I see you're interested in vegetarian meals. "
                        "How many days would you like me to plan for? (3-7 days)"
                    )
            elif (
                state.conversation_state == ConversationState.WAITING_FOR_DIET
            ):
                # Return the message that was already added by planner
                if state.messages and len(state.messages) >= 2:
                    return state.messages[-1]["content"]
                else:
                    return (
                        "I'm here to help you plan your meals! What are your "
                        "dietary goals? For example: vegetarian, vegan, "
                        "low-carb, high-protein, keto, gluten-free, or mediterranean?"
                    )
            elif state.conversation_state == ConversationState.GENERATING_PLAN:
                # Return the message that was already added by planner
                if state.messages and len(state.messages) >= 2:
                    return state.messages[-1]["content"]
                else:
                    return "I'm working on creating your meal plan. Please wait..."
            elif (
                state.conversation_state
                == ConversationState.WAITING_FOR_RECIPE_REPLACEMENT
            ):
                return "Please let me know which recipe you'd like to replace."

            # Default response - this should not be reached in MVP flow
            return (
                "I'm here to help you plan your meals! Please tell me about "
                "your dietary goals and how many days you'd like to plan for."
            )

        except Exception as e:
            return (
                f"I apologize, but I encountered an error while generating "
                f"a response: {str(e)}"
            )

    async def _process_tool_results(self, state: AgentState) -> str:
        """Process tool results and generate appropriate response."""
        try:
            response_parts = []

            for tool_result in state.tool_results:
                if tool_result.get("success"):
                    if "recipes" in tool_result:
                        # Handle recipe search results
                        recipes = tool_result["recipes"]
                        if recipes:
                            response_parts.append(
                                f"I found {len(recipes)} recipes for you:"
                            )
                            for i, recipe in enumerate(
                                recipes[:3], 1
                            ):  # Show first 3
                                response_parts.append(f"{i}. {recipe.title}")
                        else:
                            response_parts.append(
                                "I couldn't find any recipes matching your "
                                "criteria."
                            )

                    elif "shopping_list" in tool_result:
                        # Handle shopping list results
                        shopping_list = tool_result["shopping_list"]
                        if "items" in shopping_list and shopping_list["items"]:
                            response_parts.append(
                                f"I've added "
                                f"{len(shopping_list['items'])} items "
                                f"to your shopping list."
                            )
                        else:
                            response_parts.append(
                                "I've updated your shopping list."
                            )
                        # Store shopping list in state for response
                        state.shopping_list = shopping_list

                    elif "new_recipe" in tool_result:
                        # Handle recipe replacement results
                        new_recipe = tool_result["new_recipe"]
                        day_number = tool_result["day_number"]
                        meal_type = tool_result["meal_type"]

                        # Update the meal plan
                        if hasattr(state, "menu_plan") and state.menu_plan:
                            old_recipe = self._update_meal_plan_recipe(
                                state.menu_plan,
                                day_number,
                                meal_type,
                                new_recipe,
                            )

                            # Prepare tool calls for shopping list update
                            tool_calls = []

                            # First, remove old ingredients if there was an old
                            # recipe
                            if old_recipe:
                                tool_calls.append(
                                    {
                                        "name": "remove_ingredients_from_"
                                        "shopping_list",
                                        "args": {
                                            "thread_id": state.thread_id,
                                            # Using thread_id as user_id
                                            "user_id": state.thread_id,
                                            "ingredients": [
                                                {
                                                    "name": ing.name,
                                                    "quantity": ing.quantity,
                                                    "unit": ing.unit,
                                                }
                                                for ing in (
                                                    old_recipe.ingredients
                                                )
                                            ],
                                        },
                                    }
                                )

                            # Then, add new ingredients
                            tool_calls.append(
                                {
                                    "name": "add_to_shopping_list",
                                    "args": {
                                        "thread_id": state.thread_id,
                                        # Using thread_id as user_id
                                        "user_id": state.thread_id,
                                        "items": [
                                            {
                                                "name": ing.name,
                                                "quantity": ing.quantity,
                                                "unit": ing.unit,
                                            }
                                            for ing in new_recipe.ingredients
                                        ],
                                    },
                                }
                            )

                            state.tool_calls = tool_calls

                        response_parts.append(
                            f"I've replaced the {meal_type} recipe for day "
                            f"{day_number} with: {new_recipe.title}"
                        )

                else:
                    # Handle tool errors
                    error_msg = tool_result.get("error", "Unknown error")
                    error_type = tool_result.get("error_type")

                    if error_type == "recipe_not_found":
                        # Special handling for recipe replacement errors
                        suggestions = tool_result.get("suggestions", [])

                        # Set up context for retry
                        if (
                            "day_number" in tool_result
                            and "meal_type" in tool_result
                        ):
                            state.recipe_replacement_context = {
                                "day_number": tool_result["day_number"],
                                "meal_type": tool_result["meal_type"],
                                "diet_type": tool_result.get("diet_type"),
                            }
                            state.conversation_state = (
                                ConversationState.WAITING_FOR_RECIPE_REPLACEMENT
                            )

                            response_parts.append(
                                f"I couldn't find a recipe for "
                                f"'{tool_result.get('query', 'your request')}'"
                                f". Please try a different search term for "
                                f"the "
                                f"{tool_result['meal_type']} recipe on day "
                                f"{tool_result['day_number']}."
                            )

                            if suggestions:
                                response_parts.append("Suggestions:")
                                for suggestion in suggestions:
                                    response_parts.append(f"• {suggestion}")
                        else:
                            response_parts.append(
                                f"I encountered an issue: {error_msg}"
                            )
                    else:
                        response_parts.append(
                            f"I encountered an issue: {error_msg}"
                        )

            return (
                "\\n\\n".join(response_parts)
                if response_parts
                else "I've completed the requested actions."
            )

        except Exception as e:
            return (
                f"I apologize, but I encountered an error while processing "
                f"the results: {str(e)}"
            )

    def _generate_meal_plan_response(
        self, state: AgentState, language: str = "en"
    ) -> str:
        """Generate response for completed meal plan."""
        if not state.menu_plan:
            return translate("error_occurred", language)

        response_parts = [
            translate("meal_plan_generated", language),
            "",
        ]

        # Add fallback notification if applicable
        if state.fallback_used:
            response_parts.extend(
                [
                    "Note: I couldn't find enough recipes specifically for "
                    f"your {state.diet_goal} diet, so I've included recipes "
                    "from our general collection. You can modify them to "
                    "better fit your dietary preferences.",
                    "",
                ]
            )

        response_parts.append("Meal Plan:")

        for day in state.menu_plan.days:
            response_parts.append(f"\nDay {day.day_number}:")
            for meal in day.meals:
                response_parts.append(
                    f"• {meal.name.title()}: {meal.recipe.title}"
                )
                if meal.notes:
                    response_parts.append(f"  ({meal.notes})")

        response_parts.extend(
            [
                "",
                "Shopping List:",
                "I've also created a shopping list with all the ingredients "
                "you'll need.",
            ]
        )

        return "\n".join(response_parts)

    def _create_system_prompt(self, language: str = "en") -> str:
        """Create system prompt based on language."""
        return prompt_loader.get_system_prompt(language)

    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request and return a response."""
        try:
            # Try to load existing state from memory
            config = {
                "thread_id": request.thread_id,
                "recursion_limit": 10,  # Prevent infinite loops
            }

            # Get existing state or create new one
            try:
                existing_state = await self.graph.aget_state(config)
                if existing_state and existing_state.values:
                    # Load existing state and add new message
                    initial_state = existing_state.values
                    initial_state.messages.append(
                        {"role": "user", "content": request.message}
                    )
                else:
                    # Create new state
                    initial_state = AgentState(
                        thread_id=request.thread_id,
                        messages=[
                            {"role": "user", "content": request.message}
                        ],
                        language=request.language,
                    )
            except Exception:
                # If loading fails, create new state
                initial_state = AgentState(
                    thread_id=request.thread_id,
                    messages=[{"role": "user", "content": request.message}],
                    language=request.language,
                )

            # Process through the graph (LangGraph handles memory via
            # checkpointer)

            # Set timeout for entire graph execution (2 minutes)
            import asyncio

            final_state = await asyncio.wait_for(
                self.graph.ainvoke(initial_state, config=config), timeout=120.0
            )

            # Extract response
            # final_state can be AddableValuesDict, AgentState, or None
            if final_state is None:
                messages = []
            elif hasattr(final_state, "get"):
                messages = final_state.get("messages", [])
            else:
                messages = getattr(final_state, "messages", [])

            response_message = (
                messages[-1]["content"]
                if messages
                else (
                    "I apologize, but I encountered an error processing "
                    "your request."
                )
            )

            # Create response
            response = ChatResponse(
                message=response_message, thread_id=request.thread_id
            )

            # Add menu plan and shopping list if available
            if final_state is None:
                menu_plan = None
                shopping_list = None
            elif hasattr(final_state, "get"):
                menu_plan = final_state.get("menu_plan")
                shopping_list = final_state.get("shopping_list")
            else:
                menu_plan = getattr(final_state, "menu_plan", None)
                shopping_list = getattr(final_state, "shopping_list", None)

            if menu_plan:
                response.menu_plan = menu_plan

            if shopping_list:
                response.shopping_list = shopping_list

            return response

        except asyncio.TimeoutError:
            return ChatResponse(
                message=(
                    "I apologize, but the request timed out. "
                    "Please try again with a simpler request."
                ),
                thread_id=request.thread_id,
            )
        except Exception as e:
            return ChatResponse(
                message=(f"I apologize, but I encountered an error: {str(e)}"),
                thread_id=request.thread_id,
            )

    def _update_meal_plan_recipe(
        self,
        meal_plan: "MealPlan",
        day_number: int,
        meal_type: str,
        new_recipe,
    ) -> Optional[object]:
        """Update a recipe in the meal plan and return the old recipe."""
        from domain.entities import Meal

        # Find the day
        target_day = None
        for day in meal_plan.days:
            if day.day_number == day_number:
                target_day = day
                break

        # If day doesn't exist, return None (no old recipe to remove)
        if target_day is None:
            return None

        # Find the meal
        for meal in target_day.meals:
            if meal.name.lower() == meal_type.lower():
                # Store old recipe before replacing
                old_recipe = meal.recipe
                # Replace the recipe
                meal.recipe = new_recipe
                return old_recipe

        # If meal not found, add it
        new_meal = Meal(
            name=meal_type,
            recipe=new_recipe,
            notes=f"Replaced recipe for {meal_type}",
        )
        target_day.meals.append(new_meal)
        return None  # No old recipe to remove

    async def close(self):
        """Close the agent and clean up resources."""
        if self.mcp_client:
            await self.mcp_client.disconnect()
        self.memory_manager.memory_saver.close()
