"""
Tests for Recipe API endpoints.

This module contains comprehensive tests for the recipe management API,
including search, creation, and retrieval functionality.
"""

from unittest.mock import patch

from domain.entities import DietType, Recipe
from tests.base_test import BaseAPITest


class TestRecipeEndpoints(BaseAPITest):
    """Test cases for recipe API endpoints."""

    @patch("api.recipes.recipe_repo")
    def test_search_recipes_basic(self, mock_repo):
        """Test basic recipe search without filters."""
        # Create real Recipe object for testing
        test_recipe = Recipe(
            id=1,
            title="Test Recipe",
            description="Test description",
            instructions="Test instructions",
            prep_time_minutes=10,
            cook_time_minutes=20,
            servings=2,
            difficulty="easy",
            diet_type=DietType.VEGETARIAN,
            ingredients=[],
            tags=[],
        )
        test_recipe.user_id = self.test_user_id
        mock_repo.search_recipes.return_value = [test_recipe]

        # Test request
        response = self.client.get("/api/v1/recipes/?query=pasta")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        assert "total" in data
        assert "filters" in data
        assert len(data["recipes"]) == 1
        assert data["recipes"][0]["title"] == "Test Recipe"

    @patch("api.recipes.recipe_repo")
    def test_search_recipes_with_filters(self, mock_repo):
        """Test recipe search with multiple filters."""
        # Create real Recipe object for testing
        test_recipe = Recipe(
            id=1,
            title="Vegetarian Pasta",
            description="A healthy pasta dish",
            instructions="Cook pasta and add sauce",
            prep_time_minutes=15,
            cook_time_minutes=20,
            servings=4,
            difficulty="easy",
            diet_type=DietType.VEGETARIAN,
            ingredients=[],
            tags=[],
        )
        test_recipe.user_id = self.test_user_id
        mock_repo.search_recipes.return_value = [test_recipe]

        # Test request with filters
        response = self.client.get(
            "/api/v1/recipes/",
            params={
                "query": "pasta",
                "diet_type": "vegetarian",
                "difficulty": "easy",
                "max_prep_time": 30,
                "limit": 5,
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["query"] == "pasta"
        assert data["filters"]["diet_type"] == "vegetarian"
        assert data["filters"]["difficulty"] == "easy"
        assert data["filters"]["max_prep_time"] == 30

    @patch("api.recipes.recipe_repo")
    def test_search_recipes_empty_result(self, mock_repo):
        """Test recipe search with no results."""
        # Mock empty repository response
        mock_repo.search_recipes.return_value = []

        # Test request
        response = self.client.get("/api/v1/recipes/?query=nonexistent")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["recipes"]) == 0

    @patch("api.recipes.recipe_repo")
    def test_get_recipe_by_id_success(self, mock_repo):
        """Test getting a recipe by ID successfully."""
        # Mock repository response - create real Recipe object
        mock_recipe = Recipe(
            id=1,
            title="Test Recipe",
            description="Test description",
            instructions="Test instructions",
        )
        mock_repo.get_by_id.return_value = mock_recipe

        # Test request
        response = self.client.get("/api/v1/recipes/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "recipe" in data
        assert data["recipe"]["id"] == 1
        assert data["recipe"]["title"] == "Test Recipe"

    @patch("api.recipes.recipe_repo")
    def test_get_recipe_by_id_not_found(self, mock_repo):
        """Test getting a recipe by ID when not found."""
        # Mock repository response
        mock_repo.get_by_id.return_value = None

        # Test request
        response = self.client.get("/api/v1/recipes/999")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @patch("api.recipes.recipe_repo")
    def test_create_recipe_success(self, mock_repo, test_recipe_api_data):
        """Test creating a recipe successfully."""

        # Mock repository save method to simulate real behavior
        def mock_save(recipe):
            # Simulate the real save() behavior: return same object with id set
            recipe.id = 1
            return recipe

        mock_repo.save.side_effect = mock_save

        # Test request
        response = self.client.post(
            "/api/v1/recipes/", json=test_recipe_api_data
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "Recipe created successfully" in data["message"]
        assert "recipe" in data

    def test_create_recipe_missing_required_fields(self):
        """Test creating a recipe with missing required fields."""
        # Test request with missing title
        incomplete_data = {
            "description": "Test description",
            "instructions": "Test instructions",
        }

        response = self.client.post("/api/v1/recipes/", json=incomplete_data)

        # Assertions
        assert response.status_code == 422
        data = response.json()
        assert "title" in str(data["detail"])

    @patch("api.recipes.recipe_repo")
    def test_create_recipe_repository_error(
        self, mock_repo, test_recipe_api_data
    ):
        """Test creating a recipe when repository fails."""
        # Mock repository error
        mock_repo.save.side_effect = Exception("Database error")

        # Test request
        response = self.client.post(
            "/api/v1/recipes/", json=test_recipe_api_data
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to create recipe" in data["detail"]

    def test_get_diet_types(self):
        """Test getting available diet types."""
        response = self.client.get("/api/v1/recipes/diet-types/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "vegetarian" in data
        assert "vegan" in data
        assert "gluten-free" in data

    def test_get_difficulty_levels(self):
        """Test getting available difficulty levels."""
        response = self.client.get("/api/v1/recipes/difficulty-levels/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "easy" in data
        assert "medium" in data
        assert "hard" in data

    @patch("api.recipes.recipe_repo")
    def test_search_recipes_repository_error(self, mock_repo):
        """Test recipe search when repository fails."""
        # Mock repository error
        mock_repo.search_recipes.side_effect = Exception("Database error")

        # Test request
        response = self.client.get("/api/v1/recipes/?query=pasta")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to search recipes" in data["detail"]

    @patch("api.recipes.recipe_repo")
    def test_get_recipe_repository_error(self, mock_repo):
        """Test getting recipe when repository fails."""
        # Mock repository error
        mock_repo.get_by_id.side_effect = Exception("Database error")

        # Test request
        response = self.client.get("/api/v1/recipes/1")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get recipe" in data["detail"]
