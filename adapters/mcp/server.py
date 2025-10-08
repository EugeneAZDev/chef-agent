"""
MCP (Model Context Protocol) server for Chef Agent.

This server provides tools for recipe finding and shopping list management
that can be used by AI agents.
"""

import asyncio
import json
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

        # Register tools
        self._register_tools()

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
                                        "vegetarian",
                                        "vegan",
                                        "gluten_free",
                                        "keto",
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
                if name == "recipe_finder":
                    result = await self._handle_recipe_finder(arguments)
                elif name == "shopping_list_manager":
                    result = await self._handle_shopping_list_manager(
                        arguments
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(result, indent=2),
                        )
                    ]
                )
            except Exception as e:  # noqa: BLE001
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
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

        # Search recipes using the proper search method with filters
        recipes = self.recipe_repo.search_recipes(
            query=query,
            diet_type=diet_type,
            difficulty=None,  # Not used in MCP interface
            max_prep_time=max_prep_time,
            limit=50,  # Reasonable limit for MCP
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
                    "diet_type": recipe.diet_type,
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

        if action == "create":
            # Create new shopping list
            shopping_list = ShoppingList(items=[])
            created_list = self.shopping_repo.create(shopping_list, thread_id)
            return {
                "action": "created",
                "list_id": created_list.id,
                "thread_id": thread_id,
                "items": [],
            }

        elif action == "get":
            # Get existing shopping list
            shopping_list = self.shopping_repo.get_by_thread_id(thread_id)
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
            shopping_list = self.shopping_repo.get_by_thread_id(thread_id)
            if not shopping_list:
                shopping_list = ShoppingList(items=[])
                shopping_list = self.shopping_repo.create(
                    shopping_list, thread_id
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

        elif action == "clear":
            # Clear shopping list
            self.shopping_repo.clear(thread_id)
            return {
                "action": "cleared",
                "thread_id": thread_id,
                "message": "Shopping list cleared",
            }

        elif action == "delete":
            # Delete shopping list
            shopping_list = self.shopping_repo.get_by_thread_id(thread_id)
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
