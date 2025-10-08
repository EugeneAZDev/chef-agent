"""
API package for Chef Agent.

This package contains FastAPI endpoints and related functionality
for the Chef Agent web API.
"""

from .chat import router as chat_router
from .health import router as health_router
from .recipes import router as recipes_router
from .shopping import router as shopping_router

__all__ = ["chat_router", "health_router", "recipes_router", "shopping_router"]
