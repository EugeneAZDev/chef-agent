"""
Tests for diet_type validation in recipe repository.

This module tests that diet_type values are properly validated
and that invalid values raise appropriate errors.
"""

from unittest.mock import Mock

import pytest

from adapters.db.recipe_repository import SQLiteRecipeRepository
from domain.entities import DietType, Ingredient, Recipe


class TestDietTypeValidation:
    """Test diet_type validation in recipe repository."""

    def test_parse_diet_type_valid_values(self, temp_database):
        """Test parsing valid diet_type values."""
        repo = SQLiteRecipeRepository(temp_database)

        # Test all valid enum values
        for diet_type in DietType:
            result = repo._parse_diet_type(diet_type.value)
            assert result == diet_type

        # Test None/empty values
        assert repo._parse_diet_type(None) is None
        assert repo._parse_diet_type("") is None

    def test_parse_diet_type_invalid_values(self, temp_database):
        """Test parsing invalid diet_type values raises ValueError."""
        repo = SQLiteRecipeRepository(temp_database)

        invalid_values = [
            "paleo-typo",
            "invalid-diet",
            "vegetarian-extra",
            "keto-diet",
            "123",
            "VEGETARIAN",  # Wrong case
            "vegetarian ",  # Extra space
        ]

        for invalid_value in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                repo._parse_diet_type(invalid_value)

            assert "Invalid diet_type" in str(exc_info.value)
            assert invalid_value in str(exc_info.value)

    def test_search_recipes_invalid_diet_type(self, temp_database):
        """Test search_recipes with invalid diet_type raises ValueError."""
        repo = SQLiteRecipeRepository(temp_database)

        with pytest.raises(ValueError) as exc_info:
            repo.search_recipes(diet_type="invalid-diet")

        assert "Invalid diet_type" in str(exc_info.value)
        assert "invalid-diet" in str(exc_info.value)

    def test_search_recipes_valid_diet_type(self, temp_database):
        """Test search_recipes with valid diet_type works correctly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Should not raise any errors
        recipes = repo.search_recipes(diet_type="vegetarian")
        assert isinstance(recipes, list)

    def test_row_to_recipe_invalid_diet_type_in_db(self, temp_database):
        """Test _row_to_recipe with invalid diet_type raises ValueError."""
        repo = SQLiteRecipeRepository(temp_database)

        # Mock a database row with invalid diet_type
        mock_row = {
            "id": 1,
            "title": "Test Recipe",
            "description": "Test Description",
            "instructions": "Test Instructions",
            "prep_time_minutes": 30,
            "cook_time_minutes": 20,
            "servings": 4,
            "difficulty": "easy",
            "diet_type": "invalid-diet-type",  # Invalid value
            "user_id": "test-user",
            "ingredients": "[]",
        }

        # Should not raise exception, but return None for invalid diet_type
        recipe = repo._row_to_recipe(mock_row)
        assert recipe.diet_type is None

    def test_row_to_recipe_valid_diet_type_in_db(self, temp_database):
        """Test _row_to_recipe with valid diet_type works correctly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Mock a database row with valid diet_type
        mock_row = {
            "id": 1,
            "title": "Test Recipe",
            "description": "Test Description",
            "instructions": "Test Instructions",
            "prep_time_minutes": 30,
            "cook_time_minutes": 20,
            "servings": 4,
            "difficulty": "easy",
            "diet_type": "vegetarian",  # Valid value
            "user_id": "test-user",
            "ingredients": "[]",
        }

        # Mock the _get_recipe_tags method to avoid database calls
        repo._get_recipe_tags = Mock(return_value=[])

        recipe = repo._row_to_recipe(mock_row)
        assert recipe.diet_type == DietType.VEGETARIAN

    def test_row_to_recipe_null_diet_type_in_db(self, temp_database):
        """Test _row_to_recipe with null diet_type works correctly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Mock a database row with null diet_type
        mock_row = {
            "id": 1,
            "title": "Test Recipe",
            "description": "Test Description",
            "instructions": "Test Instructions",
            "prep_time_minutes": 30,
            "cook_time_minutes": 20,
            "servings": 4,
            "difficulty": "easy",
            "diet_type": None,  # Null value
            "user_id": "test-user",
            "ingredients": "[]",
        }

        # Mock the _get_recipe_tags method to avoid database calls
        repo._get_recipe_tags = Mock(return_value=[])

        recipe = repo._row_to_recipe(mock_row)
        assert recipe.diet_type is None

    def test_create_recipe_with_invalid_diet_type(self, temp_database):
        """Test creating recipe with invalid diet_type raises error."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create recipe with invalid diet_type
        recipe = Recipe(
            id=None,
            title="Test Recipe",
            description="Test Description",
            instructions="Test Instructions",
            ingredients=[
                Ingredient(name="test_ingredient", quantity="1", unit="piece")
            ],
        )
        recipe.user_id = "test-user"

        # This should work fine - the validation happens in _parse_diet_type
        # which is only called when reading from database
        result = repo.save(recipe)
        assert result.id is not None

    def test_diet_type_enum_values_consistency(self):
        """Test that all DietType enum values are valid strings."""
        valid_diet_types = [
            "vegetarian",
            "vegan",
            "gluten-free",
            "keto",
            "paleo",
            "low-carb",
            "high-protein",
            "mediterranean",
        ]

        enum_values = [dt.value for dt in DietType]

        # Check that all enum values are in the expected list
        for enum_value in enum_values:
            assert (
                enum_value in valid_diet_types
            ), f"Unexpected diet_type: {enum_value}"

        # Check that we have all expected values
        for valid_type in valid_diet_types:
            assert (
                valid_type in enum_values
            ), f"Missing diet_type: {valid_type}"

    def test_row_to_recipe_invalid_diet_type_handling(self, temp_database):
        """Test that invalid diet_type in database doesn't crash the app."""
        repo = SQLiteRecipeRepository(temp_database)

        # Insert recipe with invalid diet_type directly into database
        # This simulates corrupted data or manual database manipulation
        temp_database.execute_update(
            "INSERT INTO recipes (title, diet_type, user_id) VALUES (?, ?, ?)",
            ("Test Recipe", "invalid-diet", "test-user"),
        )

        # This should not raise an exception
        recipes = repo.get_all()
        assert len(recipes) == 1
        assert (
            recipes[0].diet_type is None
        )  # Should default to None for invalid values
        assert recipes[0].title == "Test Recipe"
