"""
MCP (Model Context Protocol) server for Chef Agent.

This server provides tools for recipe finding and shopping list management
that can be used by AI agents.
"""

import asyncio
import json
import signal
import sys
import time
from collections import defaultdict
from typing import Any, Dict

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from adapters.db import (
    Database,
    SQLiteRecipeRepository,
    SQLiteShoppingListRepository,
)
from domain.entities import ShoppingItem, ShoppingList


class ChefAgentMCPServer:
    """MCP server for Chef Agent tools."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("chef-agent")
        self.db = Database()
        self.recipe_repo = SQLiteRecipeRepository(self.db)
        self.shopping_repo = SQLiteShoppingListRepository(self.db)

        # Rate limiting: 100 requests per minute per client
        self.rate_limits = defaultdict(list)
        self.max_requests = 100
        self.time_window = 60  # seconds

        # Register tools
        self._register_tools()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers."""

        def signal_handler(signum, frame):
            print(f"Received signal {signum}, shutting down gracefully...")
            try:
                self.db.close()
            except Exception as e:
                print(f"Error closing database: {e}")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _get_client_id(self, arguments: Dict[str, Any]) -> str:
        """Get client identifier for rate limiting."""
        # Use user_id if available, otherwise use thread_id as fallback
        return arguments.get("user_id") or arguments.get(
            "thread_id", "anonymous"
        )

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        current_time = time.time()

        # Clean old requests outside time window
        self.rate_limits[client_id] = [
            req_time
            for req_time in self.rate_limits[client_id]
            if current_time - req_time < self.time_window
        ]

        # Check if client exceeded rate limit
        if len(self.rate_limits[client_id]) >= self.max_requests:
            return True

        # Add current request
        self.rate_limits[client_id].append(current_time)
        return False

    def _register_tools(self):
        """Register all available tools."""

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="recipe_finder",
                        description=(
                            "Find recipes by keywords, tags, diet type, "
                            "or ingredients"
                        ),
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": (
                                        "Search query (keywords, ingredients, "
                                        "etc.)"
                                    ),
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Filter by recipe tags",
                                },
                                "diet_type": {
                                    "type": "string",
                                    "enum": [
                                        "low-carb",
                                        "vegetarian",
                                        "vegan",
                                        "high-protein",
                                        "keto",
                                        "mediterranean",
                                        "gluten-free",
                                        "paleo",
                                    ],
                                    "description": "Filter by diet type",
                                },
                                "max_prep_time": {
                                    "type": "integer",
                                    "description": (
                                        "Maximum preparation time in minutes"
                                    ),
                                },
                                "max_cook_time": {
                                    "type": "integer",
                                    "description": (
                                        "Maximum cooking time in minutes"
                                    ),
                                },
                                "servings": {
                                    "type": "integer",
                                    "description": ("Number of servings"),
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": (
                                        "User ID to filter recipes by owner"
                                    ),
                                },
                            },
                        },
                    ),
                    Tool(
                        name="shopping_list_manager",
                        description=(
                            "Manage shopping lists for meal planning"
                        ),
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": [
                                        "create",
                                        "get",
                                        "add_items",
                                        "remove_items",
                                        "clear",
                                        "delete",
                                    ],
                                    "description": (
                                        "Action to perform on shopping list"
                                    ),
                                },
                                "thread_id": {
                                    "type": "string",
                                    "description": (
                                        "Thread ID for conversation context"
                                    ),
                                },
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "quantity": {"type": "string"},
                                            "unit": {"type": "string"},
                                            "category": {"type": "string"},
                                        },
                                    },
                                    "description": (
                                        "Items to add to shopping list"
                                    ),
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": (
                                        "User ID for shopping list ownership"
                                    ),
                                },
                            },
                            "required": ["action", "thread_id"],
                        },
                    ),
                ]
            )

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> CallToolResult:
            """Handle tool calls."""
            try:
                # Check rate limiting
                client_id = self._get_client_id(arguments)
                if self._is_rate_limited(client_id):
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "error": "Rate limit exceeded",
                                        "error_code": "RATE_LIMIT_EXCEEDED",
                                        "message": (
                                            f"Too many requests. Limit: "
                                            f"{self.max_requests} per "
                                            f"{self.time_window} seconds"
                                        ),
                                    },
                                    separators=(",", ":"),
                                ),
                            )
                        ]
                    )

                if name == "recipe_finder":
                    result = await self._handle_recipe_finder(arguments)
                elif name == "shopping_list_manager":
                    result = await self._handle_shopping_list_manager(
                        arguments
                    )
                else:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=json.dumps(
                                    {"error": f"Unknown tool: {name}"},
                                    separators=(",", ":"),
                                ),
                            )
                        ]
                    )

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(result, separators=(",", ":")),
                        )
                    ]
                )
            except ValueError as e:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": f"Invalid parameters: {str(e)}"},
                                separators=(",", ":"),
                            ),
                        )
                    ]
                )
            except Exception as e:  # noqa: BLE001
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": str(e)}, separators=(",", ":")
                            ),
                        )
                    ]
                )

    async def _handle_recipe_finder(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle recipe finder tool calls."""
        query = args.get("query", "")
        tags = args.get("tags", [])
        diet_type = args.get("diet_type")
        max_prep_time = args.get("max_prep_time")
        max_cook_time = args.get("max_cook_time")
        servings = args.get("servings")
        user_id = args.get("user_id")
        if not user_id:
            # Require explicit user_id for security
            return {
                "error": "user_id is required for recipe search",
                "recipes": [],
                "total_found": 0,
            }

        # Search recipes using the proper search method with filters
        # diet_type validation is handled in search_recipes method
        recipes = self.recipe_repo.search_recipes(
            query=query,
            diet_type=diet_type,
            difficulty=None,  # Not used in MCP interface
            max_prep_time=max_prep_time,
            limit=50,  # Reasonable limit for MCP
            user_id=user_id,  # Filter by user_id
        )

        # Apply additional filters that aren't handled by search_recipes
        if tags:
            recipes = [
                r for r in recipes if any(tag in r.tags for tag in tags)
            ]

        if max_cook_time is not None:
            recipes = [
                r
                for r in recipes
                if (
                    r.cook_time_minutes
                    and r.cook_time_minutes <= max_cook_time
                )
            ]

        if servings is not None:
            recipes = [
                r for r in recipes if r.servings and r.servings >= servings
            ]

            # Convert to
            # serializable format
        result = {
            "recipes": [
                {
                    "id": recipe.id,
                    "title": recipe.title,
                    "description": recipe.description,
                    "prep_time_minutes": recipe.prep_time_minutes,
                    "cook_time_minutes": recipe.cook_time_minutes,
                    "servings": recipe.servings,
                    "difficulty": recipe.difficulty,
                    "tags": recipe.tags,
                    "diet_type": (
                        recipe.diet_type.value if recipe.diet_type else None
                    ),
                    "ingredients": [
                        {
                            "name": ing.name,
                            "quantity": ing.quantity,
                            "unit": ing.unit,
                        }
                        for ing in recipe.ingredients
                    ],
                    "instructions": recipe.instructions,
                }
                for recipe in recipes
            ],
            "total_found": len(recipes),
        }

        return result

    async def _handle_shopping_list_manager(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shopping list manager tool calls."""
        action = args["action"]
        thread_id = args["thread_id"]
        items = args.get("items", [])
        # Get user_id from args, use None if not provided
        user_id = args.get("user_id")

        if action == "create":
            # Create new shopping list
            shopping_list = ShoppingList(items=[])
            created_list = self.shopping_repo.create(
                shopping_list, thread_id, user_id
            )
            return {
                "action": "created",
                "list_id": created_list.id,
                "thread_id": thread_id,
                "items": [],
            }

        elif action == "get":
            # Get existing shopping list
            shopping_list = self.shopping_repo.get_by_thread_id(
                thread_id, user_id
            )
            if shopping_list:
                return {
                    "action": "retrieved",
                    "list_id": shopping_list.id,
                    "thread_id": thread_id,
                    "items": [
                        {
                            "name": item.name,
                            "quantity": item.quantity,
                            "unit": item.unit,
                            "category": item.category,
                        }
                        for item in shopping_list.items
                    ],
                }
            else:
                return {
                    "action": "not_found",
                    "thread_id": thread_id,
                    "message": "No shopping list found for this thread",
                }

        elif action == "add_items":
            # Add items to shopping list
            shopping_list = self.shopping_repo.get_by_thread_id(
                thread_id, user_id
            )
            if not shopping_list:
                shopping_list = ShoppingList(items=[])
                shopping_list = self.shopping_repo.create(
                    shopping_list, thread_id, user_id
                )

            # Convert items to ShoppingItem objects with auto-categorization
            from domain.ingredient_categorizer import IngredientCategorizer

            new_items = []
            for item in items:
                # Use provided category or auto-detect
                category = item.get("category")
                if not category:
                    category = IngredientCategorizer.categorize_ingredient(
                        item["name"]
                    )

                new_items.append(
                    ShoppingItem(
                        name=item["name"],
                        quantity=item.get("quantity", "1"),
                        unit=item.get("unit", ""),
                        category=category,
                    )
                )

            # Add items to existing list
            for item in new_items:
                shopping_list.add_item(item)

            # Update in database
            updated_list = self.shopping_repo.update(shopping_list, thread_id)

            return {
                "action": "items_added",
                "list_id": updated_list.id,
                "thread_id": thread_id,
                "added_items": len(new_items),
                "total_items": len(updated_list.items),
            }

        elif action == "remove_items":
            # Remove specific items from shopping list
            shopping_list = self.shopping_repo.get_by_thread_id(
                thread_id, user_id
            )
            if not shopping_list:
                return {
                    "action": "not_found",
                    "thread_id": thread_id,
                    "message": "No shopping list found to remove items from",
                }

            # Convert items to ShoppingItem objects for comparison
            items_to_remove = []
            for item in items:
                items_to_remove.append(
                    ShoppingItem(
                        name=item["name"],
                        quantity=item.get("quantity", "1"),
                        unit=item.get("unit", ""),
                        category=item.get("category", "other"),
                    )
                )

            # Remove items from the list
            removed_count = 0
            for item_to_remove in items_to_remove:
                # Find and remove matching items
                items_to_keep = []
                for existing_item in shopping_list.items:
                    if (
                        existing_item.name.lower()
                        == item_to_remove.name.lower()
                        and existing_item.quantity == item_to_remove.quantity
                        and existing_item.unit == item_to_remove.unit
                    ):
                        removed_count += 1
                    else:
                        items_to_keep.append(existing_item)

                shopping_list.items = items_to_keep

            # Update in database
            updated_list = self.shopping_repo.update(shopping_list, thread_id)

            return {
                "action": "items_removed",
                "list_id": updated_list.id,
                "thread_id": thread_id,
                "removed_items": removed_count,
                "total_items": len(updated_list.items),
            }

        elif action == "clear":
            # Clear shopping list
            self.shopping_repo.clear(thread_id, user_id)
            return {
                "action": "cleared",
                "thread_id": thread_id,
                "message": "Shopping list cleared",
            }

        elif action == "delete":
            # Delete shopping list
            shopping_list = self.shopping_repo.get_by_thread_id(
                thread_id, user_id
            )
            if shopping_list:
                self.shopping_repo.delete(shopping_list.id)
                return {
                    "action": "deleted",
                    "list_id": shopping_list.id,
                    "thread_id": thread_id,
                }
            else:
                return {
                    "action": "not_found",
                    "thread_id": thread_id,
                    "message": "No shopping list found to delete",
                }

        else:
            return {"error": f"Unknown action: {action}"}

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="chef-agent",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None, experimental_capabilities={}
                    ),
                ),
            )


async def main():
    """Main entry point for MCP server."""
    server = ChefAgentMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
