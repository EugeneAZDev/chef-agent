"""
Pydantic models for the Chef Agent.

This module defines the data structures used by the LangGraph agent
for processing user requests and generating responses.
"""

from typing import Any, Dict, List, Literal, Optional

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


class AgentState(BaseModel):
    """State model for LangGraph agent."""

    model_config = {"arbitrary_types_allowed": True}

    thread_id: str = Field(..., description="Conversation thread ID")
    messages: List[Dict[str, str]] = Field(
        default_factory=list, description="Conversation messages"
    )
    user_request: Optional[str] = Field(
        None, description="Current user request"
    )
    diet_goal: Optional[str] = Field(None, description="User's diet goal")
    days_count: Optional[int] = Field(
        None, description="Number of days for meal plan"
    )
    found_recipes: List[Recipe] = Field(
        default_factory=list, description="Recipes found by tools"
    )
    menu_plan: Optional[MealPlan] = Field(
        None, description="Generated meal plan"
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
        ..., ge=1, le=14, description="Number of days for meal plan"
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
