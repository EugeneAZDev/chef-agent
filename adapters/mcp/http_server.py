"""
HTTP-based MCP server for Chef Agent.

This server provides tools for recipe finding and shopping list management
that can be used by AI agents via HTTP API.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from adapters.db import (
    Database,
    SQLiteRecipeRepository,
    SQLiteShoppingListRepository,
)
from domain.entities import ShoppingItem, ShoppingList


class RecipeSearchRequest(BaseModel):
    """Request model for recipe search."""

    query: str = ""
    tags: Optional[List[str]] = None
    diet_type: Optional[str] = None
    max_prep_time: Optional[int] = None
    max_cook_time: Optional[int] = None
    servings: Optional[int] = None
    limit: int = 10


class ShoppingListRequest(BaseModel):
    """Request model for shopping list operations."""

    action: str  # create, add, get, clear, delete
    thread_id: str
    items: Optional[List[Dict[str, str]]] = None


class ChefAgentHTTPMCPServer:
    """HTTP-based MCP server for Chef Agent tools."""

    def __init__(self):
        """Initialize the HTTP MCP server."""
        self.app = FastAPI(title="Chef Agent MCP Server", version="1.0.0")
        self.db = Database()
        self.recipe_repo = SQLiteRecipeRepository(self.db)
        self.shopping_repo = SQLiteShoppingListRepository(self.db)

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register API routes."""

        @self.app.post("/tools/recipe_finder")
        async def recipe_finder(
            request: RecipeSearchRequest,
        ) -> Dict[str, Any]:
            """Find recipes based on criteria."""
            try:
                # Search recipes
                recipes = self.recipe_repo.search_recipes(
                    query=request.query,
                    diet_type=request.diet_type,
                    max_prep_time=request.max_prep_time,
                    servings=request.servings,
                    limit=request.limit,
                )

                # Convert to dict format
                recipe_dicts = []
                for recipe in recipes:
                    recipe_dicts.append(
                        {
                            "id": recipe.id,
                            "title": recipe.title,
                            "description": recipe.description,
                            "ingredients": [
                                {
                                    "name": ing.name,
                                    "quantity": ing.quantity,
                                    "unit": ing.unit,
                                }
                                for ing in recipe.ingredients
                            ],
                            "instructions": recipe.instructions,
                            "prep_time_minutes": recipe.prep_time_minutes,
                            "cook_time_minutes": recipe.cook_time_minutes,
                            "servings": recipe.servings,
                            "difficulty": recipe.difficulty,
                            "tags": recipe.tags,
                            "diet_type": (
                                recipe.diet_type.value
                                if recipe.diet_type
                                else None
                            ),
                        }
                    )

                return {
                    "success": True,
                    "recipes": recipe_dicts,
                    "total_found": len(recipe_dicts),
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "recipes": [],
                    "total_found": 0,
                }

        @self.app.post("/tools/shopping_list_manager")
        async def shopping_list_manager(
            request: ShoppingListRequest,
        ) -> Dict[str, Any]:
            """Manage shopping lists."""
            try:
                if request.action == "create":
                    # Create empty shopping list
                    empty_shopping_list = ShoppingList(items=[])
                    result = self.shopping_repo.create(
                        shopping_list=empty_shopping_list,
                        thread_id=request.thread_id,
                    )
                    return {
                        "success": True,
                        "message": (
                            f"Shopping list created for thread "
                            f"{request.thread_id}"
                        ),
                        "thread_id": request.thread_id,
                    }

                elif request.action == "add":
                    if not request.items:
                        return {
                            "success": False,
                            "error": "No items provided for adding",
                        }

                    # Convert items to ShoppingItem objects
                    shopping_items = []
                    for item in request.items:
                        shopping_items.append(
                            ShoppingItem(
                                name=item.get("name", ""),
                                quantity=item.get("quantity", ""),
                                unit=item.get("unit", ""),
                                category=item.get("category"),
                                purchased=item.get("purchased", False),
                            )
                        )

                    result = self.shopping_repo.add_items(
                        thread_id=request.thread_id, items=shopping_items
                    )
                    return {
                        "success": True,
                        "message": (
                            f"Added {len(shopping_items)} items to "
                            f"shopping list"
                        ),
                        "thread_id": request.thread_id,
                    }

                elif request.action == "get":
                    shopping_list = self.shopping_repo.get_by_thread_id(
                        request.thread_id
                    )
                    if shopping_list:
                        items = [
                            {
                                "name": item.name,
                                "quantity": item.quantity,
                                "unit": item.unit,
                                "category": item.category,
                                "purchased": item.purchased,
                            }
                            for item in shopping_list.items
                        ]
                        return {
                            "success": True,
                            "shopping_list": {
                                "thread_id": request.thread_id,
                                "items": items,
                                "total_items": len(items),
                            },
                        }
                    else:
                        return {
                            "success": False,
                            "error": (
                                f"No shopping list found for thread "
                                f"{request.thread_id}"
                            ),
                        }

                elif request.action == "clear":
                    self.shopping_repo.clear(thread_id=request.thread_id)
                    return {
                        "success": True,
                        "message": (
                            f"Shopping list cleared for thread "
                            f"{request.thread_id}"
                        ),
                        "thread_id": request.thread_id,
                    }

                elif request.action == "delete":
                    # First get the shopping list to get its ID
                    shopping_list = self.shopping_repo.get_by_thread_id(
                        request.thread_id
                    )
                    if shopping_list:
                        result = self.shopping_repo.delete(shopping_list.id)
                        if result:
                            return {
                                "success": True,
                                "message": (
                                    f"Shopping list deleted for thread "
                                    f"{request.thread_id}"
                                ),
                                "thread_id": request.thread_id,
                            }
                        else:
                            return {
                                "success": False,
                                "error": "Failed to delete shopping list",
                            }
                    else:
                        return {
                            "success": False,
                            "error": (
                                f"No shopping list found for thread "
                                f"{request.thread_id}"
                            ),
                        }

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {request.action}",
                    }

            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "service": "chef-agent-mcp-server"}

    def run(self, host: str = "localhost", port: int = 8072):
        """Run the HTTP MCP server."""
        import uvicorn

        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    server = ChefAgentHTTPMCPServer()
    server.run()
