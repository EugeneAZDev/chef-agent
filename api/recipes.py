"""
Recipe management API endpoints.

This module provides REST API endpoints for recipe operations,
including search, creation, and management.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from adapters.db import Database, SQLiteRecipeRepository
from domain.entities import DietType, Ingredient, Recipe

from .models import RecipeCreate

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])

# Global database instance
db = Database()
recipe_repo = SQLiteRecipeRepository(db)


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Search recipes",
    description="Search recipes with optional filters",
)
async def search_recipes(
    query: Optional[str] = Query(None, description="Search query"),
    diet_type: Optional[DietType] = Query(
        None, description="Diet type filter"
    ),
    difficulty: Optional[str] = Query(None, description="Difficulty level"),
    max_prep_time: Optional[int] = Query(
        None, description="Maximum prep time in minutes"
    ),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of results"
    ),
    user_id: Optional[str] = Query(
        None, description="User ID for filtering user's recipes"
    ),
) -> Dict[str, Any]:
    """
    Search for recipes with optional filters.

    Returns a list of recipes matching the search criteria.
    """
    try:
        logger.info(f"Searching recipes with query: {query}")

        # Build search parameters
        search_params = {}
        if query:
            search_params["query"] = query
        if diet_type:
            search_params["diet_type"] = diet_type.value
        if difficulty:
            search_params["difficulty"] = difficulty
        if max_prep_time:
            search_params["max_prep_time"] = max_prep_time

        # Search recipes
        recipes = recipe_repo.search_recipes(**search_params, user_id=user_id)

        # Limit results
        if limit and len(recipes) > limit:
            recipes = recipes[:limit]

        # Serialize recipes properly
        recipes_data = []
        for recipe in recipes:
            recipe_data = {
                "id": recipe.id,
                "title": recipe.title,
                "description": recipe.description,
                "instructions": recipe.instructions,
                "prep_time_minutes": recipe.prep_time_minutes,
                "cook_time_minutes": recipe.cook_time_minutes,
                "servings": recipe.servings,
                "difficulty": recipe.difficulty,
                "diet_type": recipe.diet_type,
                "user_id": recipe.user_id,
                "ingredients": (
                    [
                        {
                            "name": ing.name,
                            "quantity": ing.quantity,
                            "unit": ing.unit,
                        }
                        for ing in recipe.ingredients
                    ]
                    if recipe.ingredients
                    else []
                ),
                "tags": recipe.tags or [],
            }
            recipes_data.append(recipe_data)

        return {
            "recipes": recipes_data,
            "total": len(recipes_data),
            "filters": search_params,
        }

    except Exception as e:
        logger.error(f"Error searching recipes: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search recipes: {str(e)}"
        )


@router.get(
    "/{recipe_id}",
    response_model=Dict[str, Any],
    summary="Get recipe by ID",
    description="Retrieve a specific recipe by its ID",
)
async def get_recipe(recipe_id: int) -> Dict[str, Any]:
    """
    Get a specific recipe by ID.

        recipe = recipe_repo.get_by_id(recipe_id)
    """
    try:
        logger.info(f"Getting recipe with ID: {recipe_id}")

        recipe = recipe_repo.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=404, detail=f"Recipe with ID {recipe_id} not found"
            )

        # Serialize recipe properly
        recipe_data = {
            "id": recipe.id,
            "title": recipe.title,
            "description": recipe.description,
            "instructions": recipe.instructions,
            "prep_time_minutes": recipe.prep_time_minutes,
            "cook_time_minutes": recipe.cook_time_minutes,
            "servings": recipe.servings,
            "difficulty": recipe.difficulty,
            "diet_type": recipe.diet_type,
            "user_id": recipe.user_id,
            "ingredients": (
                [
                    {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.unit,
                    }
                    for ing in recipe.ingredients
                ]
                if recipe.ingredients
                else []
            ),
            "tags": recipe.tags or [],
        }

        return {"recipe": recipe_data, "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recipe {recipe_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get recipe: {str(e)}"
        )


@router.post(
    "/",
    response_model=Dict[str, Any],
    summary="Create new recipe",
    description="Create a new recipe in the database",
)
async def create_recipe(recipe_data: RecipeCreate) -> Dict[str, Any]:
    """
    Create a new recipe.

    Accepts recipe data and creates a new recipe in the database.
    """
    try:
        logger.info("Creating new recipe")

        # Create recipe object (id will be assigned by repository)
        recipe = Recipe(
            id=None,  # Will be assigned by repository
            title=recipe_data.title,
            description=recipe_data.description or "",
            instructions=recipe_data.instructions,
            prep_time_minutes=recipe_data.prep_time_minutes,
            cook_time_minutes=recipe_data.cook_time_minutes,
            servings=recipe_data.servings,
            difficulty=recipe_data.difficulty,
            diet_type=recipe_data.diet_type,
            user_id=recipe_data.user_id,
        )

        # Add ingredients if provided
        if recipe_data.ingredients:
            ingredients = []
            for ing_data in recipe_data.ingredients:
                ingredient = Ingredient(
                    name=ing_data.name,
                    quantity=ing_data.quantity,
                    unit=ing_data.unit,
                )
                ingredients.append(ingredient)
            recipe.ingredients = ingredients

        # Save recipe
        created_recipe = recipe_repo.save(recipe)

        # Serialize recipe properly
        recipe_data = {
            "id": created_recipe.id,
            "title": created_recipe.title,
            "description": created_recipe.description,
            "instructions": created_recipe.instructions,
            "prep_time_minutes": created_recipe.prep_time_minutes,
            "cook_time_minutes": created_recipe.cook_time_minutes,
            "servings": created_recipe.servings,
            "difficulty": created_recipe.difficulty,
            "diet_type": created_recipe.diet_type,
            "ingredients": (
                [
                    {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.unit,
                    }
                    for ing in created_recipe.ingredients
                ]
                if created_recipe.ingredients
                else []
            ),
        }

        return {
            "recipe": recipe_data,
            "status": "created",
            "message": "Recipe created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating recipe: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create recipe: {str(e)}"
        )


@router.get(
    "/diet-types/",
    response_model=List[str],
    summary="Get available diet types",
    description="Get list of available diet types for filtering",
)
async def get_diet_types() -> List[str]:
    """
    Get available diet types.

    Returns a list of all available diet types for recipe filtering.
    """
    return [diet_type.value for diet_type in DietType]


@router.get(
    "/difficulty-levels/",
    response_model=List[str],
    summary="Get difficulty levels",
    description="Get list of available difficulty levels",
)
async def get_difficulty_levels() -> List[str]:
    """
    Get available difficulty levels.

    Returns a list of all available difficulty levels for recipe filtering.
    """
    return ["easy", "medium", "hard"]
