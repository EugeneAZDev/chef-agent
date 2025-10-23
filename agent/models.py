"""
Pydantic models for the Chef Agent.

This module defines the data structures used by the LangGraph agent
for processing user requests and generating responses.
"""

from enum import Enum
from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from domain.entities import MealPlan, Recipe, ShoppingList


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    thread_id: str = Field(..., description="Unique conversation thread ID")
    message: str = Field(..., description="User message")
    language: Literal["en", "de", "fr"] = Field(
        default="en", description="Language preference"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    model_config = {"arbitrary_types_allowed": True}

    message: str = Field(..., description="Agent response message")
    menu_plan: Optional[MealPlan] = Field(
        None, description="Generated meal plan"
    )
    shopping_list: Optional[ShoppingList] = Field(
        None, description="Generated shopping list"
    )
    thread_id: str = Field(..., description="Conversation thread ID")


class ConversationState(Enum):
    """States for conversation flow."""

    INITIAL = "initial"
    WAITING_FOR_DIET = "waiting_for_diet"
    WAITING_FOR_DAYS = "waiting_for_days"
    GENERATING_PLAN = "generating_plan"
    WAITING_FOR_RECIPE_REPLACEMENT = "waiting_for_recipe_replacement"
    COMPLETED = "completed"


class AgentState(BaseModel):
    """State model for LangGraph agent."""

    model_config = {"arbitrary_types_allowed": True}

    thread_id: str = Field(..., description="Conversation thread ID")
    messages: List[Dict[str, str]] = Field(
        default_factory=list, description="Conversation messages"
    )

    # Maximum number of messages to keep in memory
    MAX_MESSAGES: ClassVar[int] = 100
    user_request: Optional[str] = Field(
        None, description="Current user request"
    )
    diet_goal: Optional[str] = Field(None, description="User's diet goal")
    difficulty: Optional[str] = Field(
        None, description="Recipe difficulty level"
    )
    days_count: Optional[int] = Field(
        None, ge=3, le=7, description="Number of days for meal plan (3-7)"
    )
    conversation_state: ConversationState = Field(
        default=ConversationState.INITIAL,
        description="Current conversation state",
    )
    found_recipes: List[Recipe] = Field(
        default_factory=list, description="Recipes found by tools"
    )
    menu_plan: Optional[MealPlan] = Field(
        None, description="Generated meal plan"
    )
    fallback_used: bool = Field(
        False, description="Whether fallback recipes were used"
    )
    recipe_search_attempts: int = Field(
        default=0, description="Number of recipe search attempts"
    )
    recipe_replacement_context: Optional[Dict[str, Any]] = Field(
        None, description="Context for recipe replacement retry"
    )
    shopping_list: Optional[ShoppingList] = Field(
        None, description="Generated shopping list"
    )
    language: str = Field(default="en", description="Current language")
    error: Optional[str] = Field(None, description="Error message if any")
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tool calls to execute"
    )
    tool_results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tool execution results"
    )

    def add_message(self, message: Dict[str, str]) -> None:
        """Add a message and maintain message limit."""
        self.messages.append(message)
        # Keep only the last MAX_MESSAGES messages
        if len(self.messages) > self.MAX_MESSAGES:
            # Keep the first message (usually system) and the last MAX_MESSAGES-1
            if len(self.messages) > 1:
                self.messages = [self.messages[0]] + self.messages[
                    -(self.MAX_MESSAGES - 1) :
                ]
            else:
                self.messages = self.messages[-self.MAX_MESSAGES :]

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Custom serialization to handle enum values and complex objects."""
        data = super().model_dump(**kwargs)
        # Convert enum to string for JSON serialization
        if "conversation_state" in data and data["conversation_state"]:
            data["conversation_state"] = data["conversation_state"].value

        # Handle complex objects that need custom serialization
        if "found_recipes" in data and data["found_recipes"]:
            data["found_recipes"] = [
                (
                    recipe.model_dump()
                    if hasattr(recipe, "model_dump")
                    else (
                        recipe.__dict__
                        if hasattr(recipe, "__dict__")
                        else recipe
                    )
                )
                for recipe in data["found_recipes"]
            ]

        if "menu_plan" in data and data["menu_plan"]:
            if hasattr(data["menu_plan"], "model_dump"):
                data["menu_plan"] = data["menu_plan"].model_dump()
            elif hasattr(data["menu_plan"], "__dict__"):
                data["menu_plan"] = data["menu_plan"].__dict__

        if "shopping_list" in data and data["shopping_list"]:
            if hasattr(data["shopping_list"], "model_dump"):
                data["shopping_list"] = data["shopping_list"].model_dump()
            elif hasattr(data["shopping_list"], "__dict__"):
                data["shopping_list"] = data["shopping_list"].__dict__

        return data

    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> "AgentState":
        """Custom deserialization to handle enum values and complex objects."""
        # Convert string back to enum
        if "conversation_state" in data and isinstance(
            data["conversation_state"], str
        ):
            data["conversation_state"] = ConversationState(
                data["conversation_state"]
            )

        # Handle complex objects that need custom deserialization
        if "found_recipes" in data and data["found_recipes"]:
            from domain.entities import Ingredient, Recipe

            deserialized_recipes = []
            for recipe_data in data["found_recipes"]:
                if isinstance(recipe_data, dict):
                    # Deserialize ingredients
                    ingredients = []
                    if (
                        "ingredients" in recipe_data
                        and recipe_data["ingredients"]
                    ):
                        for ing_data in recipe_data["ingredients"]:
                            if isinstance(ing_data, dict):
                                ingredients.append(
                                    Ingredient(
                                        name=ing_data.get("name", ""),
                                        quantity=ing_data.get("quantity", ""),
                                        unit=ing_data.get("unit", ""),
                                    )
                                )

                    # Create Recipe object
                    recipe = Recipe(
                        id=recipe_data.get("id"),
                        title=recipe_data.get("title", ""),
                        description=recipe_data.get("description"),
                        ingredients=ingredients,
                        instructions=recipe_data.get("instructions", ""),
                        prep_time_minutes=recipe_data.get("prep_time_minutes"),
                        cook_time_minutes=recipe_data.get("cook_time_minutes"),
                        servings=recipe_data.get("servings"),
                        difficulty=recipe_data.get("difficulty"),
                        tags=recipe_data.get("tags", []),
                        diet_type=recipe_data.get("diet_type"),
                        user_id=recipe_data.get("user_id"),
                    )
                    deserialized_recipes.append(recipe)
                else:
                    deserialized_recipes.append(recipe_data)
            data["found_recipes"] = deserialized_recipes

        if (
            "menu_plan" in data
            and data["menu_plan"]
            and isinstance(data["menu_plan"], dict)
        ):
            # For now, just pass through the dict - complex deserialization
            # would be needed for full MenuDay and Meal objects
            pass

        if (
            "shopping_list" in data
            and data["shopping_list"]
            and isinstance(data["shopping_list"], dict)
        ):
            from domain.entities import ShoppingItem, ShoppingList

            shopping_data = data["shopping_list"]
            items = []
            if "items" in shopping_data and shopping_data["items"]:
                for item_data in shopping_data["items"]:
                    if isinstance(item_data, dict):
                        items.append(
                            ShoppingItem(
                                name=item_data.get("name", ""),
                                quantity=item_data.get("quantity", ""),
                                unit=item_data.get("unit", ""),
                                category=item_data.get("category"),
                                purchased=item_data.get("purchased", False),
                            )
                        )
            data["shopping_list"] = ShoppingList(items=items)

        return super().model_validate(data)


class ToolCall(BaseModel):
    """Model for tool calls."""

    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")


class ToolResult(BaseModel):
    """Model for tool results."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    success: bool = Field(
        ..., description="Whether the tool call was successful"
    )
    result: Any = Field(..., description="Tool result data")
    error: Optional[str] = Field(
        None, description="Error message if tool call failed"
    )


class MealPlanRequest(BaseModel):
    """Model for meal plan generation requests."""

    diet_goal: str = Field(
        ..., description="Diet goal (e.g., 'low-carb', 'vegetarian')"
    )
    days_count: int = Field(
        ..., ge=3, le=7, description="Number of days for meal plan (3-7)"
    )
    preferences: Optional[List[str]] = Field(
        default_factory=list, description="Additional preferences"
    )
    language: str = Field(default="en", description="Language for responses")


class MenuDayResponse(BaseModel):
    """Model for menu day response."""

    day_number: int = Field(..., description="Day number")
    meals: List[Dict[str, str]] = Field(..., description="Meals for the day")
    total_calories: Optional[int] = Field(
        None, description="Estimated total calories"
    )


class ShoppingListResponse(BaseModel):
    """Model for shopping list response."""

    items: List[Dict[str, str]] = Field(..., description="Shopping list items")
    total_items: int = Field(..., description="Total number of items")
    categories: List[str] = Field(..., description="Item categories")


class ErrorResponse(BaseModel):
    """Model for error responses."""

    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


__all__ = [
    "ConversationState",
    "AgentState",
    "ChatRequest",
    "ChatResponse",
    "ToolCall",
    "ToolResult",
    "MealPlanRequest",
    "MenuDayResponse",
    "ShoppingListResponse",
    "ErrorResponse",
]
