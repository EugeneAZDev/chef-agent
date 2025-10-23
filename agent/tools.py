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
    difficulty: Optional[str] = None,
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
        difficulty: Difficulty level filter (easy, medium, hard)
        max_prep_time: Maximum preparation time in minutes
        max_cook_time: Maximum cooking time in minutes
        servings: Number of servings
        limit: Maximum number of recipes to return

    Returns:
        Dictionary containing found recipes and metadata
    """
    if not _mcp_client:
        # Fallback to direct database access when MCP client is not available
        try:
            from adapters.db import Database
            from adapters.db.recipe_repository import SQLiteRecipeRepository

            db = Database()
            print(f"DEBUG: Using database: {db.db_path}")
            recipe_repo = SQLiteRecipeRepository(db)

            print(
                f"DEBUG: Searching recipes with diet_type='{diet_type}', difficulty='{difficulty}', user_id=None"
            )

            # Search recipes directly from database
            # In fallback mode, search all recipes (no user_id filter)
            recipes = recipe_repo.search_recipes(
                query=query,
                diet_type=diet_type,
                difficulty=difficulty,
                max_prep_time=max_prep_time,
                limit=limit,
                user_id=None,  # Search all recipes in fallback mode
            )

            print(f"DEBUG: Found {len(recipes)} recipes")
            for recipe in recipes:
                print(
                    f"DEBUG: Recipe: {recipe.title}, diet_type: {recipe.diet_type}, difficulty: {recipe.difficulty}"
                )
            
            # Debug: Check if recipes match the diet_type filter
            if diet_type:
                matching_recipes = [r for r in recipes if r.diet_type == diet_type]
                print(f"DEBUG: Recipes matching diet_type '{diet_type}': {len(matching_recipes)}")
                for recipe in matching_recipes:
                    print(f"DEBUG: Matching recipe: {recipe.title}")

            # Apply additional filters
            if tags:
                recipes = [
                    r for r in recipes if any(tag in r.tags for tag in tags)
                ]

            if max_cook_time is not None:
                recipes = [
                    r
                    for r in recipes
                    if r.cook_time_minutes
                    and r.cook_time_minutes <= max_cook_time
                ]

            if servings is not None:
                recipes = [
                    r for r in recipes if r.servings and r.servings >= servings
                ]

            return {
                "success": True,
                "recipes": recipes,
                "total_found": len(recipes),
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
                "error": f"Database fallback failed: {str(e)}",
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

        # Ensure result is a dict, not a coroutine
        if hasattr(result, "__await__"):
            result = await result
        elif hasattr(result, "_mock_name") and "AsyncMock" in str(
            type(result)
        ):
            # Handle AsyncMock that might not be awaited
            result = await result

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
        # Fallback to direct database access when MCP client is not available
        try:
            from adapters.db import Database
            from adapters.db.shopping_list_repository import (
                SQLiteShoppingListRepository,
            )

            db = Database()
            shopping_repo = SQLiteShoppingListRepository(db)

            # Create shopping list directly in database
            shopping_list = shopping_repo.create_shopping_list(
                thread_id=thread_id,
                user_id=None,  # Use None for fallback mode
            )

            return {
                "success": True,
                "shopping_list": shopping_list,
                "message": f"Shopping list created for thread {thread_id}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Database fallback failed: {str(e)}",
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
        # Fallback to direct database access when MCP client is not available
        try:
            from adapters.db import Database
            from adapters.db.shopping_list_repository import (
                SQLiteShoppingListRepository,
            )

            db = Database()
            shopping_repo = SQLiteShoppingListRepository(db)

            # Add items directly to database
            result = shopping_repo.add_items_to_shopping_list(
                thread_id=thread_id,
                items=items,
                user_id=None,  # Use None for fallback mode
            )

            return {
                "success": True,
                "shopping_list": result,
                "message": f"Added {len(items)} items to shopping list",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Database fallback failed: {str(e)}",
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
async def create_recipe(
    title: str,
    description: str,
    instructions: str,
    diet_type: Optional[str] = None,
    prep_time_minutes: Optional[int] = None,
    cook_time_minutes: Optional[int] = None,
    servings: Optional[int] = None,
    difficulty: Optional[str] = None,
    ingredients: Optional[List[Dict[str, str]]] = None,
    user_id: str = "test_user",
) -> Dict[str, Any]:
    """
    Create a new recipe and add it to the database.

    Args:
        title: Recipe title
        description: Recipe description
        instructions: Cooking instructions
        diet_type: Diet type (vegetarian, vegan, low-carb, etc.)
        prep_time_minutes: Preparation time in minutes
        cook_time_minutes: Cooking time in minutes
        servings: Number of servings
        difficulty: Difficulty level (easy, medium, hard)
        ingredients: List of ingredients with name, quantity, unit
        user_id: User ID for recipe ownership

    Returns:
        Dictionary containing created recipe data
    """
    # Always use direct database access for create_recipe
    # MCP client doesn't have create_recipe method
    try:
        from adapters.db import Database
        from adapters.db.recipe_repository import SQLiteRecipeRepository
        from domain.entities import DietType, Ingredient, Recipe

        db = Database()
        recipe_repo = SQLiteRecipeRepository(db)

        # Convert diet_type string to enum
        diet_type_enum = None
        if diet_type:
            try:
                diet_type_enum = DietType(diet_type.lower())
            except ValueError:
                # If diet_type is not valid, use None
                diet_type_enum = None

        # Create ingredients list
        ingredients_list = []
        if ingredients:
            for ing_data in ingredients:
                ingredient = Ingredient(
                    name=ing_data.get("name", ""),
                    quantity=ing_data.get("quantity", ""),
                    unit=ing_data.get("unit", ""),
                    )
                ingredients_list.append(ingredient)

        # Create recipe object
        recipe = Recipe(
            id=None,
            title=title,
            description=description,
            instructions=instructions,
            prep_time_minutes=prep_time_minutes,
            cook_time_minutes=cook_time_minutes,
            servings=servings,
            difficulty=difficulty,
            tags=[],  # Empty tags for now
            diet_type=diet_type_enum,
            ingredients=ingredients_list,
            user_id=user_id,
        )

        # Save recipe to database
        created_recipe = recipe_repo.save(recipe)

        return {
            "success": True,
            "recipe": {
                "id": created_recipe.id,
                "title": created_recipe.title,
                "description": created_recipe.description,
                "instructions": created_recipe.instructions,
                "prep_time_minutes": created_recipe.prep_time_minutes,
                "cook_time_minutes": created_recipe.cook_time_minutes,
                "servings": created_recipe.servings,
                "difficulty": created_recipe.difficulty,
                "diet_type": (
                    created_recipe.diet_type.value
                    if created_recipe.diet_type
                    else None
                ),
                "ingredients": [
                    {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.unit,
                    }
                    for ing in created_recipe.ingredients
                ],
            },
            "message": f"Recipe '{title}' created successfully",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Database fallback failed: {str(e)}",
            "message": "Failed to create recipe",
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


@tool
async def create_fallback_recipes(
    diet_type: str = "vegetarian",
    limit: int = 5,
    query: str = "",
) -> Dict[str, Any]:
    """
    Create fallback recipes when MCP client is not available.

    Args:
        diet_type: Diet type for recipes
        limit: Number of recipes to create
        query: Search query (used for recipe names)

    Returns:
        Dictionary containing created recipes
    """
    return {
        "success": False,
        "error": "MCP client not available - cannot create recipes without proper recipe dataset",
        "recipes": [],
        "total_found": 0,
        "message": "Please ensure MCP server is running for recipe access"
    }


def create_chef_tools(
    mcp_client: Optional[ChefAgentHTTPMCPClient] = None,
) -> List:
    """Create and return all chef agent tools."""
    if mcp_client:
        set_mcp_client(mcp_client)
        return [
            search_recipes,
            create_recipe,
            create_shopping_list,
            add_to_shopping_list,
            get_shopping_list,
            clear_shopping_list,
            replace_recipe_in_meal_plan,
        ]
    else:
        # Return fallback tools when no MCP client
        set_mcp_client(None)
        return [
            search_recipes,
            create_recipe,
            create_shopping_list,
            add_to_shopping_list,
            create_fallback_recipes,
        ]
