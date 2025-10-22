"""
Shared test fixtures and utilities.
"""

import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from adapters.db import Database
from adapters.db.recipe_repository import SQLiteRecipeRepository
from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from adapters.llm.groq_adapter import GroqAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.mcp.client import ChefAgentMCPClient
from agent import ChefAgentGraph


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    db = Database(temp_db.name)
    yield db

    db.close()
    import os

    os.unlink(temp_db.name)


@pytest.fixture
def recipe_repo(temp_database):
    """Create recipe repository with temp database."""
    return SQLiteRecipeRepository(temp_database)


@pytest.fixture
def shopping_repo(temp_database):
    """Create shopping repository with temp database."""
    return SQLiteShoppingListRepository(temp_database)


@pytest.fixture
def test_user_id():
    """Standard test user ID."""
    return "test-user-123"


@pytest.fixture
def test_thread_id():
    """Standard test thread ID."""
    return "test-thread-456"


@pytest.fixture
def client():
    """Test client for API testing."""
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)


@pytest.fixture
def mock_groq_adapter():
    """Mock Groq adapter for testing."""
    with patch("adapters.llm.groq_adapter.ChatGroq"):
        adapter = GroqAdapter(
            api_key="test-key",
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=2048,
        )
        # Pre-configure common mocks
        adapter._llm = Mock()
        return adapter


@pytest.fixture
def mock_openai_adapter():
    """Mock OpenAI adapter for testing."""
    with patch("adapters.llm.openai_adapter.ChatOpenAI"):
        adapter = OpenAIAdapter(
            api_key="test-key",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=2048,
        )
        # Pre-configure common mocks
        adapter._llm = Mock()
        return adapter


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = Mock(spec=ChefAgentMCPClient)
    # Make MCP client methods async for testing
    client.find_recipes = AsyncMock()
    client.create_shopping_list = AsyncMock()
    client.add_to_shopping_list = AsyncMock()
    client.get_shopping_list = AsyncMock()
    client.clear_shopping_list = AsyncMock()
    client.manage_shopping_list = AsyncMock()
    return client


@pytest.fixture
def mock_chef_agent(mock_mcp_client):
    """Mock ChefAgentGraph for testing."""
    with patch("agent.graph.LLMFactory") as mock_factory:
        # Create a simple mock LLM without AsyncMock
        mock_llm = Mock()
        mock_factory.create_llm.return_value = mock_llm

        # Create real ChefAgentGraph instance
        agent = ChefAgentGraph("groq", "test-api-key", mock_mcp_client)

        # Mock the graph.ainvoke method as a simple Mock
        agent.graph = Mock()

        # Mock memory manager as simple Mock
        agent.memory_manager = Mock()

        # Ensure the agent has access to the mock_llm
        agent.llm = mock_llm

        return agent


@pytest.fixture
def test_recipe_data():
    """Standard test recipe data."""
    return {
        "title": "Test Pasta",
        "description": "A delicious test pasta recipe",
        "instructions": "1. Boil water\n2. Add pasta\n3. Cook for 8 minutes",
        "ingredients": [
            {"name": "Pasta", "quantity": "200", "unit": "g"},
            {"name": "Water", "quantity": "1", "unit": "L"},
            {"name": "Salt", "quantity": "1", "unit": "tsp"},
        ],
        "user_id": "test-user-123",
    }


@pytest.fixture
def test_shopping_data():
    """Standard test shopping list data."""
    return {
        "thread_id": "test-thread-123",
        "items": [
            {"name": "Milk", "quantity": "1", "unit": "L"},
            {"name": "Bread", "quantity": "2", "unit": "loaves"},
        ],
        "user_id": "test-user-123",
    }


@pytest.fixture
def test_recipe_api_data():
    """Test recipe data for API tests."""
    return {
        "title": "Test Pasta",
        "description": "A delicious test pasta recipe",
        "instructions": "1. Boil water\n2. Add pasta\n3. Cook for 8 minutes",
        "prep_time_minutes": 5,
        "cook_time_minutes": 8,
        "servings": 4,
        "difficulty": "easy",
        "diet_type": "vegetarian",
        "ingredients": [
            {"name": "pasta", "quantity": "500", "unit": "g"},
            {"name": "tomato sauce", "quantity": "400", "unit": "ml"},
        ],
    }


@pytest.fixture
def test_shopping_api_data():
    """Test shopping list data for API tests."""
    return {
        "thread_id": "test-thread-123",
        "item_data": {
            "name": "Milk",
            "quantity": "1",
            "unit": "liter",
            "category": "dairy",
            "purchased": False,
        },
    }


@pytest.fixture
def test_api_client():
    """Test client for API testing with common setup."""
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)


@pytest.fixture
def memory_saver():
    """Memory saver for testing."""
    from agent.memory import SQLiteMemorySaver

    return SQLiteMemorySaver(":memory:")


@pytest.fixture
def memory_manager():
    """Memory manager for testing."""
    from agent.memory import MemoryManager

    return MemoryManager(":memory:")


@pytest.fixture
def chef_tools(mock_mcp_client):
    """Chef tools for testing."""
    from agent.tools import create_chef_tools

    return create_chef_tools(mock_mcp_client)


@pytest.fixture
def test_db_setup():
    """Common database setup for tests that need to clear data."""
    from adapters.db import Database

    db = Database("chef_agent.db")
    try:
        # Clear test data
        db.execute_update("DELETE FROM shopping_lists")
        db.execute_update("DELETE FROM recipes")
        # Note: We don't clear agent_memory.db as it's used by the agent
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to clear test database: {e}")
    finally:
        db.close()


@pytest.fixture
def temp_db_with_cleanup():
    """Create a temporary database with automatic cleanup."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    db = Database(temp_db.name)
    yield db

    db.close()
    import os

    os.unlink(temp_db.name)
