"""
Tests for failure scenarios and error handling.
"""

from unittest.mock import patch

import pytest

from adapters.db.recipe_repository import SQLiteRecipeRepository
from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from adapters.llm.groq_adapter import GroqAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from domain.entities import Ingredient, Recipe, ShoppingItem, ShoppingList

# Mark all failure tests
pytestmark = pytest.mark.failure


class TestLLMFailureHandling:
    """Test LLM adapter failure scenarios."""

    def test_groq_api_failure(self):
        """Test Groq API failure handling."""
        from langchain_core.messages import HumanMessage

        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock API failure
            mock_groq.return_value.invoke.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_openai_api_failure(self):
        """Test OpenAI API failure handling."""
        from langchain_core.messages import HumanMessage

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")

        with patch("adapters.llm.openai_adapter.ChatOpenAI") as mock_openai:
            # Mock API failure
            mock_openai.return_value.invoke.side_effect = Exception(
                "API Error"
            )

            with pytest.raises(Exception, match="API Error"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        # Test empty messages list
        with pytest.raises(ValueError):
            adapter.invoke([])

        # Test None messages
        with pytest.raises(ValueError):
            adapter.invoke(None)

    def test_network_timeout_handling(self):
        """Test network timeout handling."""
        from langchain_core.messages import HumanMessage

        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock timeout
            mock_groq.return_value.invoke.side_effect = TimeoutError(
                "Request timeout"
            )

            with pytest.raises(TimeoutError, match="Request timeout"):
                adapter.invoke([HumanMessage(content="Test message")])


class TestDatabaseFailureHandling:
    """Test database failure scenarios."""

    def test_recipe_repository_connection_failure(self, temp_database):
        """Test recipe repository connection failure."""
        repo = SQLiteRecipeRepository(temp_database)

        recipe = Recipe(
            id=None,
            title="Test Recipe",
            description="Test description",
            instructions="Test instructions",
        )
        recipe.user_id = "test-user"

        # Mock database to simulate connection failure
        with patch.object(repo.db, "execute_insert") as mock_insert:
            mock_insert.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                repo.save(recipe)

    def test_shopping_repository_connection_failure(self, temp_database):
        """Test shopping repository connection failure."""
        repo = SQLiteShoppingListRepository(temp_database)

        # Mock database to simulate connection failure
        with patch.object(repo.db, "execute_insert") as mock_insert:
            mock_insert.side_effect = Exception("Database connection failed")

            shopping_list = ShoppingList(
                items=[
                    ShoppingItem(name="Test Item", quantity="1", unit="piece")
                ],
            )
            shopping_list.user_id = "test-user"

            with pytest.raises(Exception, match="Database connection failed"):
                repo.save(shopping_list, "test-thread", user_id="test-user")

    def test_database_constraint_violation(self, recipe_repo):
        """Test database constraint violation handling."""
        # Create first recipe
        recipe1 = Recipe(
            id=None,
            title="Test Recipe",
            description="Test description",
            instructions="Test instructions",
        )
        recipe1.user_id = "test-user"
        recipe_repo.save(recipe1)

        # Try to create duplicate recipe
        recipe2 = Recipe(
            id=None,
            title="Test Recipe",  # Same title
            description="Different description",
            instructions="Different instructions",
        )
        recipe2.user_id = "test-user"  # Same user

        with pytest.raises(ValueError, match="already exists for this user"):
            recipe_repo.save(recipe2)

    def test_json_serialization_failure(self, recipe_repo):
        """Test JSON serialization failure handling."""
        # Create recipe with invalid ingredient data
        recipe = Recipe(
            id=None,
            title="Test Recipe",
            description="Test description",
            instructions="Test instructions",
            ingredients=[Ingredient(name="Test", quantity="1", unit="piece")],
        )
        recipe.user_id = "test-user"

        # Mock json.dumps to fail
        with patch("json.dumps") as mock_dumps:
            mock_dumps.side_effect = TypeError("Object not serializable")

            with pytest.raises(
                ValueError, match="Failed to serialize ingredients"
            ):
                recipe_repo.save(recipe)


class TestAPIFailureHandling:
    """Test API failure scenarios."""

    def test_recipe_search_database_error(self, client):
        """Test recipe search with database error."""
        with patch("api.recipes.recipe_repo") as mock_repo:
            mock_repo.search_recipes.side_effect = Exception("Database error")

            response = client.get("/api/v1/recipes/?query=pasta")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_shopping_list_creation_database_error(self, client):
        """Test shopping list creation with database error."""
        with patch("api.shopping.shopping_repo") as mock_repo:
            mock_repo.get_by_thread_id.side_effect = Exception(
                "Database error"
            )

            response = client.get(
                "/api/v1/shopping/lists?thread_id=test-thread"
            )

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON requests."""
        response = client.post(
            "/api/v1/shopping/lists",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422  # Validation error

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/api/v1/shopping/lists",
            json={"thread_id": "test-thread"},  # Missing items
        )

        assert response.status_code == 422  # Validation error


class TestConcurrentAccess:
    """Test concurrent access scenarios."""

    def test_concurrent_recipe_creation(self, recipe_repo):
        """Test concurrent recipe creation with same title."""
        import threading

        results = []
        errors = []

        def create_recipe(recipe_id):
            try:
                recipe = Recipe(
                    id=None,
                    title="Concurrent Recipe",
                    description=f"Recipe {recipe_id}",
                    instructions="Test instructions",
                )
                recipe.user_id = "test-user"
                result = recipe_repo.save(recipe)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_recipe, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # At least one should succeed
        assert len(results) >= 1
        # Total attempts should equal results + errors
        assert len(results) + len(errors) == 5
