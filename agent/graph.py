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

        # Create tools (empty list if no MCP client)
        if mcp_client:
            self.tools = create_chef_tools(mcp_client)
        else:
            self.tools = []  # Empty tools list when no MCP client
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
        if not state.found_recipes:
            # No recipes found - handle based on search attempts
            state.recipe_search_attempts += 1

            if state.recipe_search_attempts < 2:
                # Try broader search
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            "I couldn't find enough recipes for your meal "
                            "plan. "
                            "Let me try a broader search..."
                        ),
                    }
                )
                state.tool_calls = [
                    {
                        "name": "search_recipes",
                        "args": {"limit": 50},  # Broader search
                    }
                ]
            else:
                # Give up after 2 attempts
                state.add_message(
                    {
                        "role": "assistant",
                        "content": (
                            "I'm sorry, but I couldn't find any recipes for "
                            f"your {state.diet_goal} meal plan. This might be "
                            "because our recipe database doesn't have enough "
                            "recipes for this specific diet. Please try a "
                            "different diet goal or contact support if you "
                            "need "
                            "help."
                        ),
                    }
                )
                state.conversation_state = ConversationState.COMPLETED
                state.error = "No recipes found after multiple search attempts"
            return state

        if state.days_count is None:
            # This should not happen in normal flow, but handle gracefully
            state.error = "Missing days count for meal plan generation"
            state.add_message(
                {
                    "role": "assistant",
                    "content": (
                        "I'm sorry, but I need to know how many days to plan "
                        "for. Please specify the number of days (3-7)."
                    ),
                }
            )
            state.conversation_state = ConversationState.WAITING_FOR_DAYS
            return state

        # We have both recipes and days_count
        if state.found_recipes and state.days_count is not None:
            try:
                # Generate meal plan using found recipes
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
                            "meal_plan": meal_plan,
                            "thread_id": state.thread_id,
                        },
                    }
                ]
            except ValueError as e:
                # Handle empty recipe list or other validation errors
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
        if not getattr(state, "tool_calls", None):
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

        # Store found recipes in state for meal plan generation
        for tool_result in tool_results:
            if tool_result.get("success") and "recipes" in tool_result:
                state.found_recipes = tool_result["recipes"]
                break

        # Clear tool_calls after execution to prevent memory leaks
        state.tool_calls = []

        return state

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
                return {"error": f"Tool {tool_name} not found"}

            # Execute the tool
            result = tool_func.invoke(tool_args)
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

            # Default response - this should not be reached in MVP flow
            return (
                "I'm here to help you plan your meals! Please tell me about "
                "your dietary goals and how many days you'd like to plan for."
            )

        except Exception as e:
            return (
                f"I apologize, but I encountered an error while generating a "
                f"response: {str(e)}"
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
                    "better fit your "
                    "dietary preferences.",
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
            # Create initial state
            initial_state = AgentState(
                thread_id=request.thread_id,
                messages=[{"role": "user", "content": request.message}],
                language=request.language,
            )

            # Process through the graph (LangGraph handles memory via
            # checkpointer)
            config = {
                "thread_id": request.thread_id,
                "recursion_limit": 10,  # Prevent infinite loops
            }

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
                else "I apologize, but I encountered an error processing your request."
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
                message=f"I apologize, but I encountered an error: {str(e)}",
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
