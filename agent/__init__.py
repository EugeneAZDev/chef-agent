"""
Chef Agent package.

This package contains the LangGraph-based AI agent for meal planning
and shopping list management.
"""

from .graph import ChefAgentGraph
from .memory import MemoryManager, SQLiteMemorySaver
from .models import (
    AgentState,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    MealPlanRequest,
    MenuDayResponse,
    ShoppingListResponse,
    ToolCall,
    ToolResult,
)
from .tools import create_chef_tools

__all__ = [
    # Models
    "ChatRequest",
    "ChatResponse",
    "AgentState",
    "ToolCall",
    "ToolResult",
    "MealPlanRequest",
    "MenuDayResponse",
    "ShoppingListResponse",
    "ErrorResponse",
    # Memory
    "SQLiteMemorySaver",
    "MemoryManager",
    # Tools
    "ChefAgentTools",
    "create_chef_tools",
    # Graph
    "ChefAgentGraph",
]
