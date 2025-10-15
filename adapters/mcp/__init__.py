"""
MCP (Model Context Protocol) adapters for Chef Agent.

This module provides MCP server and client implementations for
recipe finding and shopping list management tools.
"""

from .client import ChefAgentMCPClient
from .server import ChefAgentMCPServer

__all__ = ["ChefAgentMCPClient", "ChefAgentMCPServer"]
