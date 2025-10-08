"""
Base test class with common setup and utilities.
"""

import tempfile
from unittest.mock import patch

from adapters.db import Database
from adapters.db.recipe_repository import SQLiteRecipeRepository
from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from adapters.llm.groq_adapter import GroqAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from domain.entities import Ingredient, Recipe


class BaseDatabaseTest:
    """Base class for database-related tests."""

    def setup_method(self):
        """Set up test database and repositories."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.db = Database(self.temp_db.name)
        self.recipe_repo = SQLiteRecipeRepository(self.db)
        self.shopping_repo = SQLiteShoppingListRepository(self.db)
        self.test_user_id = "test-user-123"

    def teardown_method(self):
        """Clean up test database."""
        self.db.close()
        import os

        os.unlink(self.temp_db.name)

    def create_test_recipe(self, title="Test Recipe", user_id=None):
        """Create a test recipe."""
        return Recipe(
            id=None,
            title=title,
            description="Test description",
            instructions="Test instructions",
            ingredients=[
                Ingredient(name="test ingredient", quantity="1", unit="piece")
            ],
            user_id=user_id or self.test_user_id,
        )


class BaseLLMTest:
    """Base class for LLM-related tests."""

    def setup_method(self):
        """Set up test LLM adapters."""
        self.test_api_key = "test-key"
        self.test_model = "test-model"

    def create_mock_groq_adapter(self):
        """Create a mock Groq adapter."""
        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_chat:
            adapter = GroqAdapter(
                api_key=self.test_api_key,
                model=self.test_model,
                temperature=0.7,
                max_tokens=2048,
            )
            # Set the mock as the _llm attribute
            adapter._llm = mock_chat.return_value
            return adapter

    def create_mock_openai_adapter(self):
        """Create a mock OpenAI adapter."""
        with patch("adapters.llm.openai_adapter.ChatOpenAI") as mock_chat:
            adapter = OpenAIAdapter(
                api_key=self.test_api_key,
                model=self.test_model,
                temperature=0.7,
                max_tokens=2048,
            )
            # Set the mock as the _llm attribute
            adapter._llm = mock_chat.return_value
            return adapter


class BaseAPITest:
    """Base class for API-related tests."""

    def setup_method(self):
        """Set up test API client."""
        from fastapi.testclient import TestClient

        from main import app

        self.client = TestClient(app)
        self.test_user_id = "test-user-123"

    def create_test_recipe_data(self, title="Test Recipe"):
        """Create test recipe data for API calls."""
        return {
            "title": title,
            "description": "Test description",
            "instructions": "Test instructions",
            "ingredients": [
                {"name": "test ingredient", "quantity": "1", "unit": "piece"}
            ],
            "user_id": self.test_user_id,
        }
