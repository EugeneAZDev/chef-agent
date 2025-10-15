"""
Tests for JSON error handling in recipe repository.

This module tests that empty strings and malformed JSON are properly handled
when parsing ingredients in _row_to_recipe.
"""

import json
from unittest.mock import Mock

from adapters.db.recipe_repository import SQLiteRecipeRepository


class TestJsonErrorHandling:
    """Test JSON error handling in recipe repository."""

    def test_empty_string_ingredients(self, temp_database):
        """Test that empty string ingredients are handled properly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with empty string ingredients
        mock_row = Mock()
        mock_row.__getitem__ = Mock(
            side_effect=lambda key: {
                "id": 1,
                "title": "Test Recipe",
                "description": "Test Description",
                "instructions": "Test Instructions",
                "prep_time_minutes": 30,
                "cook_time_minutes": 45,
                "servings": 4,
                "difficulty": "medium",
                "diet_type": "vegetarian",
                "user_id": "test_user",
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00",
                "ingredients": "",  # Empty string
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []

    def test_none_ingredients(self, temp_database):
        """Test that None ingredients are handled properly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with None ingredients
        mock_row = Mock()
        mock_row.__getitem__ = Mock(
            side_effect=lambda key: {
                "id": 1,
                "title": "Test Recipe",
                "description": "Test Description",
                "instructions": "Test Instructions",
                "prep_time_minutes": 30,
                "cook_time_minutes": 45,
                "servings": 4,
                "difficulty": "medium",
                "diet_type": "vegetarian",
                "user_id": "test_user",
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00",
                "ingredients": None,  # None value
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []

    def test_malformed_json_ingredients(self, temp_database):
        """Test that malformed JSON ingredients are handled properly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with malformed JSON
        mock_row = Mock()
        mock_row.__getitem__ = Mock(
            side_effect=lambda key: {
                "id": 1,
                "title": "Test Recipe",
                "description": "Test Description",
                "instructions": "Test Instructions",
                "prep_time_minutes": 30,
                "cook_time_minutes": 45,
                "servings": 4,
                "difficulty": "medium",
                "diet_type": "vegetarian",
                "user_id": "test_user",
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00",
                "ingredients": '{"invalid": json}',  # Malformed JSON
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []

    def test_valid_json_ingredients(self, temp_database):
        """Test that valid JSON ingredients are parsed correctly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create valid JSON ingredients
        valid_ingredients = [
            {
                "name": "Tomato",
                "quantity": "2",
                "unit": "pieces",
                "allergens": [],
            },
            {
                "name": "Onion",
                "quantity": "1",
                "unit": "piece",
                "allergens": [],
            },
        ]
        ingredients_json = json.dumps(valid_ingredients)

        # Create a mock row with valid JSON ingredients
        mock_row = Mock()
        mock_row.__getitem__ = Mock(
            side_effect=lambda key: {
                "id": 1,
                "title": "Test Recipe",
                "description": "Test Description",
                "instructions": "Test Instructions",
                "prep_time_minutes": 30,
                "cook_time_minutes": 45,
                "servings": 4,
                "difficulty": "medium",
                "diet_type": "vegetarian",
                "user_id": "test_user",
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00",
                "ingredients": ingredients_json,
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with parsed ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert len(recipe.ingredients) == 2
        assert recipe.ingredients[0].name == "Tomato"
        assert recipe.ingredients[0].quantity == "2"
        assert recipe.ingredients[0].unit == "pieces"
        assert recipe.ingredients[1].name == "Onion"
        assert recipe.ingredients[1].quantity == "1"
        assert recipe.ingredients[1].unit == "piece"
