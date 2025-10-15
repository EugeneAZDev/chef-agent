"""
Tests for gzip error handling in recipe repository.

This module tests that gzip.BadGzipFile exceptions are properly handled
when decompressing compressed ingredients in _row_to_recipe.
"""

import gzip
import json
from unittest.mock import Mock

from adapters.db.recipe_repository import SQLiteRecipeRepository


class TestGzipErrorHandling:
    """Test gzip error handling in recipe repository."""

    def test_bad_gzip_file_exception_handling(self, temp_database):
        """Test that gzip.BadGzipFile is properly handled."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with corrupted compressed data
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
                "ingredients": (
                    "COMPRESSED:invalid_hex_data_that_will_cause_badgzipfile"
                ),
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []  # Should be empty due to gzip error

    def test_valid_compressed_data_handling(self, temp_database):
        """Test that valid compressed data is handled correctly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create valid compressed data
        ingredients_data = [
            {
                "name": "flour",
                "quantity": "2",
                "unit": "cups",
                "allergens": ["gluten"],
            },
            {"name": "sugar", "quantity": "1", "unit": "cup", "allergens": []},
        ]

        ingredients_json = json.dumps(ingredients_data)
        compressed_data = gzip.compress(ingredients_json.encode("utf-8"))
        compressed_hex = compressed_data.hex()

        # Create a mock row with valid compressed data
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
                "ingredients": f"COMPRESSED:{compressed_hex}",
            }[key]
        )

        # Mock the _get_recipe_tags method
        repo._get_recipe_tags = Mock(return_value=[])

        # This should work correctly
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with proper ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert len(recipe.ingredients) == 2
        assert recipe.ingredients[0].name == "flour"
        assert recipe.ingredients[0].quantity == "2"
        assert recipe.ingredients[0].unit == "cups"
        assert recipe.ingredients[0].allergens == ["gluten"]

    def test_invalid_hex_data_handling(self, temp_database):
        """Test that invalid hex data is handled gracefully."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with invalid hex data
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
                "ingredients": "COMPRESSED:not_valid_hex_data_12345",
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []  # Should be empty due to hex error

    def test_corrupted_gzip_data_handling(self, temp_database):
        """Test that corrupted gzip data is handled gracefully."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create corrupted gzip data
        corrupted_data = b"This is not valid gzip data"
        corrupted_hex = corrupted_data.hex()

        # Create a mock row with corrupted gzip data
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
                "ingredients": f"COMPRESSED:{corrupted_hex}",
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []  # Should be empty due to gzip error

    def test_empty_compressed_data_handling(self, temp_database):
        """Test that empty compressed data is handled gracefully."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create empty compressed data
        empty_data = b""
        empty_hex = empty_data.hex()

        # Create a mock row with empty compressed data
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
                "ingredients": f"COMPRESSED:{empty_hex}",
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []  # Should be empty due to empty data

    def test_non_compressed_data_handling(self, temp_database):
        """Test that non-compressed data is handled correctly."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with regular JSON data (not compressed)
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
                "ingredients": (
                    '[{"name": "flour", "quantity": "2", "unit": "cups", '
                    '"allergens": []}]'
                ),
            }[key]
        )

        # Mock the _get_recipe_tags method
        repo._get_recipe_tags = Mock(return_value=[])

        # This should work correctly
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with proper ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert len(recipe.ingredients) == 1
        assert recipe.ingredients[0].name == "flour"
        assert recipe.ingredients[0].quantity == "2"
        assert recipe.ingredients[0].unit == "cups"

    def test_malformed_json_after_decompression(self, temp_database):
        """Test that malformed JSON after decompression is handled gracefully."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create valid compressed data but with malformed JSON
        # Missing closing brace
        malformed_json = '{"name": "flour", "quantity": "2", "unit": "cups"'
        compressed_data = gzip.compress(malformed_json.encode("utf-8"))
        compressed_hex = compressed_data.hex()

        # Create a mock row with malformed JSON after decompression
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
                "ingredients": f"COMPRESSED:{compressed_hex}",
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []  # Should be empty due to JSON error

    def test_invalid_hex_in_compressed_data(self, temp_database):
        """Test that ValueError from bytes.fromhex() is properly handled."""
        repo = SQLiteRecipeRepository(temp_database)

        # Create a mock row with invalid hex data
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
                "ingredients": "COMPRESSED:INVALID_HEX_DATA",
            }[key]
        )

        # This should not raise an exception
        recipe = repo._row_to_recipe(mock_row)

        # Should return a recipe with empty ingredients
        assert recipe is not None
        assert recipe.title == "Test Recipe"
        assert recipe.ingredients == []
