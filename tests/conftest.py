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
    # Make MCP client methods async for testing and return proper values
    client.find_recipes = AsyncMock(
        return_value={"success": True, "recipes": [], "total_found": 0}
    )
    client.create_shopping_list = AsyncMock(
        return_value={"success": True, "message": "Shopping list created"}
    )
    client.add_to_shopping_list = AsyncMock(
        return_value={"success": True, "message": "Items added"}
    )
    client.get_shopping_list = AsyncMock(
        return_value={"success": True, "items": []}
    )
    client.clear_shopping_list = AsyncMock(
        return_value={"success": True, "message": "Shopping list cleared"}
    )
    client.manage_shopping_list = AsyncMock(
        return_value={"success": True, "message": "Shopping list managed"}
    )
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
def mock_llm_factory():
    """Mock LLM factory for tests that need it."""
    with patch("adapters.llm.factory.LLMFactory.create_llm") as mock_factory:
        # Create a mock LLM that returns a simple response
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(
            return_value=Mock(content="Test response")
        )

        # Simple mock that returns mock_llm for all providers
        mock_factory.return_value = mock_llm

        yield mock_factory


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


@pytest.fixture(scope="session")
def test_server():
    """Start test server for integration tests."""
    import os

    from fastapi.testclient import TestClient

    # Set test environment
    os.environ["GROQ_API_KEY"] = "test-key"
    os.environ["API_PORT"] = "8070"
    os.environ["SQLITE_DB"] = "test_chef_agent.db"
    os.environ["DATABASE_URL"] = "sqlite:///./test_chef_agent.db"

    # Also set the database path for the Database class
    import adapters.db.database

    adapters.db.database.DEFAULT_DB_PATH = "test_chef_agent.db"

    # Load test recipes into database
    try:
        from adapters.db import Database
        from adapters.db.recipe_repository import SQLiteRecipeRepository
        from domain.entities import DietType, Ingredient, Recipe

        # Create test database with sample recipes
        db = Database("test_chef_agent.db")
        recipe_repo = SQLiteRecipeRepository(db)

        # Load sample recipes
        sample_recipes = [
            Recipe(
                id=None,
                title="Vegetarian Buddha Bowl",
                description="Nutritious and colorful vegetarian meal",
                ingredients=[
                    Ingredient(name="quinoa", quantity="1", unit="cup"),
                    Ingredient(
                        name="sweet potato", quantity="2", unit="pieces"
                    ),
                    Ingredient(name="chickpeas", quantity="1", unit="can"),
                    Ingredient(name="avocado", quantity="1", unit="piece"),
                    Ingredient(name="spinach", quantity="2", unit="cups"),
                    Ingredient(name="tahini", quantity="3", unit="tbsp"),
                ],
                instructions=(
                    "Cook quinoa. Roast sweet potato cubes. Mix all ingredients "
                    "in a bowl. Drizzle with tahini dressing."
                ),
                prep_time_minutes=15,
                cook_time_minutes=30,
                servings=2,
                difficulty="medium",
                tags=["healthy", "lunch"],
                diet_type=DietType.VEGETARIAN,
                user_id="test-user",  # Add user_id for test recipes
            ),
            Recipe(
                id=None,
                title="Vegetarian Pasta",
                description="Simple vegetarian pasta dish",
                ingredients=[
                    Ingredient(name="pasta", quantity="500", unit="g"),
                    Ingredient(name="tomatoes", quantity="4", unit="pieces"),
                    Ingredient(name="onion", quantity="1", unit="piece"),
                    Ingredient(name="garlic", quantity="2", unit="cloves"),
                    Ingredient(name="olive oil", quantity="3", unit="tbsp"),
                ],
                instructions=(
                    "Cook pasta. Saute onions and garlic. Add tomatoes. "
                    "Mix with pasta."
                ),
                prep_time_minutes=10,
                cook_time_minutes=20,
                servings=4,
                difficulty="easy",
                tags=["pasta", "dinner"],
                diet_type=DietType.VEGETARIAN,
                user_id="test-user",  # Add user_id for test recipes
            ),
        ]

        # Save recipes to database
        for recipe in sample_recipes:
            recipe_repo.save(recipe)

        db.close()

    except Exception as e:
        print(f"Warning: Could not load test recipes: {e}")

    # Mock the agent creation to use fallback mode (no MCP client)
    with patch("api.chat.get_agent") as mock_get_agent:
        # Set the MCP client to None in the tools module to force fallback
        import agent.tools
        from agent import ChefAgentGraph

        agent.tools._mcp_client = None

        # Set the global agent to None to force recreation
        import api.chat

        api.chat._agent = None

        # Create agent without MCP client to use fallback mode
        test_agent = ChefAgentGraph(
            llm_provider="groq",
            api_key="test-key",
            mcp_client=None,  # No MCP client = fallback mode
        )

        # Ensure the agent uses fallback tools
        from langgraph.prebuilt import ToolNode

        from agent.tools import create_chef_tools

        test_agent.tools = create_chef_tools(None)
        test_agent.llm_with_tools = test_agent.llm.bind_tools(test_agent.tools)
        test_agent.tool_node = ToolNode(test_agent.tools)

        # Also patch the global agent variable
        api.chat._agent = test_agent
        mock_get_agent.return_value = test_agent

        # Import and create test client
        from main import app

        client = TestClient(app)

        yield client


@pytest.fixture(scope="session")
def test_mcp_server():
    """Mock MCP server for integration tests."""
    # For now, we'll skip the real MCP server and use mocks
    # This avoids the complexity of starting a real server
    yield None
