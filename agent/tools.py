"""
Tools for the Chef Agent.

This module provides LangChain tools that the agent can use
to interact with the MCP server and perform various tasks.
"""

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from domain.entities import Ingredient, Recipe

# Global MCP client instance for tools
_mcp_client: Optional[ChefAgentHTTPMCPClient] = None


def set_mcp_client(mcp_client: ChefAgentHTTPMCPClient) -> None:
    """Set the global MCP client for tools."""
    global _mcp_client
    _mcp_client = mcp_client


@tool
async def search_recipes(
    query: str = "",
    tags: Optional[List[str]] = None,
    diet_type: Optional[str] = None,
    max_prep_time: Optional[int] = None,
    max_cook_time: Optional[int] = None,
    servings: Optional[int] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search for recipes based on various criteria.

    Args:
        query: Search query (keywords, ingredients, etc.)
        tags: List of recipe tags to filter by
        diet_type: Diet type filter (vegetarian, vegan, etc.)
        max_prep_time: Maximum preparation time in minutes
        max_cook_time: Maximum cooking time in minutes
        servings: Number of servings
        limit: Maximum number of recipes to return

    Returns:
        Dictionary containing found recipes and metadata
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "recipes": [],
            "total_found": 0,
        }

    try:
        result = await _mcp_client.find_recipes(
            query=query,
            tags=tags,
            diet_type=diet_type,
            max_prep_time=max_prep_time,
            max_cook_time=max_cook_time,
            servings=servings,
        )

        # Convert to Recipe objects
        recipes = []
        for recipe_data in result.get("recipes", []):
            recipe = Recipe(
                id=recipe_data.get("id"),
                title=recipe_data.get("title", ""),
                description=recipe_data.get("description"),
                instructions=recipe_data.get("instructions", ""),
                prep_time_minutes=recipe_data.get("prep_time_minutes"),
                cook_time_minutes=recipe_data.get("cook_time_minutes"),
                servings=recipe_data.get("servings"),
                difficulty=recipe_data.get("difficulty"),
                tags=recipe_data.get("tags", []),
                diet_type=recipe_data.get("diet_type"),
                ingredients=[
                    Ingredient(
                        name=ing.get("name", ""),
                        quantity=ing.get("quantity", ""),
                        unit=ing.get("unit", ""),
                    )
                    for ing in recipe_data.get("ingredients", [])
                ],
            )
            recipes.append(recipe)

        return {
            "success": True,
            "recipes": recipes,
            "total_found": result.get("total_found", 0),
            "query": query,
            "filters": {
                "tags": tags,
                "diet_type": diet_type,
                "max_prep_time": max_prep_time,
                "max_cook_time": max_cook_time,
                "servings": servings,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "recipes": [],
            "total_found": 0,
        }


@tool
async def create_shopping_list(thread_id: str) -> Dict[str, Any]:
    """
    Create a new shopping list for a conversation thread.

    Args:
        thread_id: Unique conversation thread ID

    Returns:
        Dictionary containing shopping list creation result
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "message": "Failed to create shopping list",
        }

    try:
        result = await _mcp_client.create_shopping_list(thread_id)
        return {
            "success": True,
            "shopping_list": result,
            "message": f"Shopping list created for thread {thread_id}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create shopping list: {str(e)}",
        }


@tool
async def add_to_shopping_list(
    thread_id: str, items: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Add items to an existing shopping list.

    Args:
        thread_id: Unique conversation thread ID
        items: List of items to add, each with name, quantity, unit, category

    Returns:
        Dictionary containing shopping list update result
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "message": "Failed to add items to shopping list",
        }

    try:
        result = await _mcp_client.add_to_shopping_list(thread_id, items)
        return {
            "success": True,
            "shopping_list": result,
            "message": f"Added {len(items)} items to shopping list",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add items to shopping list: {str(e)}",
        }


@tool
async def get_shopping_list(thread_id: str) -> Dict[str, Any]:
    """
    Get the current shopping list for a conversation thread.

    Args:
        thread_id: Unique conversation thread ID

    Returns:
        Dictionary containing shopping list data
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "message": "Failed to get shopping list",
        }

    try:
        result = await _mcp_client.get_shopping_list(thread_id)
        return {
            "success": True,
            "shopping_list": result,
            "message": "Shopping list retrieved successfully",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get shopping list: {str(e)}",
        }


@tool
async def clear_shopping_list(thread_id: str) -> Dict[str, Any]:
    """
    Clear all items from the shopping list.

    Args:
        thread_id: Unique conversation thread ID

    Returns:
        Dictionary containing clearing result
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "message": "Failed to clear shopping list",
        }

    try:
        result = await _mcp_client.clear_shopping_list(thread_id)
        return {
            "success": True,
            "shopping_list": result,
            "message": "Shopping list cleared successfully",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to clear shopping list: {str(e)}",
        }


@tool
async def remove_ingredients_from_shopping_list(
    thread_id: str,
    ingredients: List[Dict[str, str]],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Remove specific ingredients from the shopping list.

    Args:
        thread_id: Conversation thread ID
        ingredients: List of ingredients to remove
        user_id: User ID for shopping list ownership (optional)

    Returns:
        Dictionary containing removal result
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "message": "Failed to remove ingredients",
        }

    try:
        # Call MCP server to remove ingredients
        result = await _mcp_client.manage_shopping_list(
            action="remove_items",
            thread_id=thread_id,
            items=ingredients,
        )

        return {
            "success": True,
            "message": f"Removed {len(ingredients)} ingredients from "
            f"shopping list",
            "result": result,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to remove ingredients: {str(e)}",
            "message": "Error removing ingredients from shopping list",
        }


@tool
async def replace_recipe_in_meal_plan(
    day_number: int,
    meal_type: str,
    new_query: str,
    thread_id: str,
    diet_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Replace a recipe in the meal plan for a specific day and meal.

    Args:
        day_number: Day number in the meal plan (1-based)
        meal_type: Type of meal (breakfast, lunch, dinner)
        new_query: Search query for the new recipe
        thread_id: Conversation thread ID
        diet_type: Diet type filter for the new recipe

    Returns:
        Dictionary containing replacement result and updated meal plan
    """
    if not _mcp_client:
        return {
            "success": False,
            "error": "MCP client not initialized",
            "message": "Failed to replace recipe",
        }

    try:
        # Search for new recipe
        search_result = await _mcp_client.find_recipes(
            query=new_query,
            diet_type=diet_type,
            limit=1,
        )

        if not search_result.get("recipes"):
            return {
                "success": False,
                "error": f"No recipes found for query: {new_query}",
                "error_type": "recipe_not_found",
                "message": "Failed to find replacement recipe",
                "day_number": day_number,
                "meal_type": meal_type,
                "diet_type": diet_type,
                "query": new_query,
                "suggestions": [
                    "Try a different search term",
                    "Use more general keywords",
                    "Check if the recipe exists in our database",
                ],
            }

        new_recipe_data = search_result["recipes"][0]

        # Convert to Recipe object
        new_recipe = Recipe(
            id=new_recipe_data.get("id"),
            title=new_recipe_data.get("title", ""),
            description=new_recipe_data.get("description"),
            instructions=new_recipe_data.get("instructions", ""),
            prep_time_minutes=new_recipe_data.get("prep_time_minutes"),
            cook_time_minutes=new_recipe_data.get("cook_time_minutes"),
            servings=new_recipe_data.get("servings"),
            difficulty=new_recipe_data.get("difficulty"),
            tags=new_recipe_data.get("tags", []),
            diet_type=new_recipe_data.get("diet_type"),
            ingredients=[
                Ingredient(
                    name=ing.get("name", ""),
                    quantity=ing.get("quantity", ""),
                    unit=ing.get("unit", ""),
                )
                for ing in new_recipe_data.get("ingredients", [])
            ],
        )

        return {
            "success": True,
            "new_recipe": {
                "id": new_recipe.id,
                "title": new_recipe.title,
                "description": new_recipe.description,
                "instructions": new_recipe.instructions,
                "prep_time_minutes": new_recipe.prep_time_minutes,
                "cook_time_minutes": new_recipe.cook_time_minutes,
                "servings": new_recipe.servings,
                "difficulty": new_recipe.difficulty,
                "tags": new_recipe.tags,
                "diet_type": (
                    new_recipe.diet_type if new_recipe.diet_type else None
                ),
                "ingredients": [
                    {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.unit,
                    }
                    for ing in new_recipe.ingredients
                ],
            },
            "day_number": day_number,
            "meal_type": meal_type,
            "message": f"Found replacement recipe: {new_recipe.title}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to replace recipe: {str(e)}",
        }


def create_chef_tools(
    mcp_client: Optional[ChefAgentHTTPMCPClient] = None,
) -> List:
    """Create and return all chef agent tools."""
    if mcp_client:
        set_mcp_client(mcp_client)
        return [
            search_recipes,
            create_shopping_list,
            add_to_shopping_list,
            get_shopping_list,
            clear_shopping_list,
            replace_recipe_in_meal_plan,
        ]
    else:
        # Return empty list when no MCP client
        return []
