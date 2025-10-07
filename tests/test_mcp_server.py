"""
Tests for MCP server functionality.
"""

from unittest.mock import patch

import pytest
from mcp.types import TextContent

from adapters.db import SQLiteRecipeRepository, SQLiteShoppingListRepository
from adapters.mcp.client import ChefAgentMCPClient
from adapters.mcp.server import ChefAgentMCPServer
from domain.entities import Ingredient, Recipe, ShoppingItem, ShoppingList


class TestChefAgentMCPServer:
    """Test cases for ChefAgentMCPServer."""

    @classmethod
    def setup_class(cls):
        """Set up test fixtures for the entire class."""
        # Use in-memory database for tests
        from adapters.db import Database

        cls.test_db = Database(":memory:")

        # Create MCP server with test database
        cls.server = ChefAgentMCPServer()
        # Replace the database and repositories
        cls.server.db = cls.test_db
        cls.server.recipe_repo = SQLiteRecipeRepository(cls.test_db)
        cls.server.shopping_repo = SQLiteShoppingListRepository(cls.test_db)

        # Also update the db reference in repositories
        cls.server.recipe_repo.db = cls.test_db
        cls.server.shopping_repo.db = cls.test_db

    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Clear the database before each test
        self.test_db.execute_update("DELETE FROM shopping_lists")
        self.test_db.execute_update("DELETE FROM recipes")
        self.test_db.execute_update("DELETE FROM tags")
        self.test_db.execute_update("DELETE FROM recipe_tags")
        self.test_db.execute_update("DELETE FROM recipe_ingredients")

    @pytest.mark.asyncio
    async def test_recipe_finder_basic_search(self):
        """Test basic recipe search functionality."""
        # Mock the recipe repository
        mock_recipe = Recipe(
            id=1,
            title="Test Pasta",
            description="A simple pasta dish",
            instructions="Cook pasta, add sauce",
            prep_time_minutes=10,
            cook_time_minutes=15,
            servings=4,
            difficulty="easy",
            tags=["italian", "pasta"],
            diet_type="vegetarian",
            ingredients=[
                Ingredient(name="pasta", quantity="500g", unit="g"),
                Ingredient(name="tomato sauce", quantity="400ml", unit="ml"),
            ],
        )

        with patch.object(
            self.server.recipe_repo,
            "search_by_keywords",
            return_value=[mock_recipe],
        ):
            result = await self.server._handle_recipe_finder(
                {"query": "pasta"}
            )

            assert "recipes" in result
            assert result["total_found"] == 1
            assert result["recipes"][0]["title"] == "Test Pasta"
            assert result["recipes"][0]["tags"] == ["italian", "pasta"]

    @pytest.mark.asyncio
    async def test_recipe_finder_with_filters(self):
        """Test recipe search with filters."""
        mock_recipe = Recipe(
            id=1,
            title="Quick Pasta",
            description="Fast pasta dish",
            instructions="Cook quickly",
            prep_time_minutes=5,
            cook_time_minutes=10,
            servings=2,
            difficulty="easy",
            tags=["quick", "pasta"],
            diet_type="vegetarian",
            ingredients=[],
        )

        with patch.object(
            self.server.recipe_repo,
            "search_by_keywords",
            return_value=[mock_recipe],
        ):
            result = await self.server._handle_recipe_finder(
                {
                    "query": "pasta",
                    "tags": ["quick"],
                    "max_prep_time": 10,
                    "servings": 2,
                }
            )

            assert result["total_found"] == 1
            assert result["recipes"][0]["title"] == "Quick Pasta"

    @pytest.mark.asyncio
    async def test_shopping_list_create(self):
        """Test shopping list creation."""
        with patch.object(self.server.shopping_repo, "create") as mock_create:
            mock_list = ShoppingList(items=[])
            mock_list.id = 1
            mock_create.return_value = mock_list

            result = await self.server._handle_shopping_list_manager(
                {"action": "create", "thread_id": "test-123"}
            )

            assert result["action"] == "created"
            assert result["thread_id"] == "test-123"
            assert result["items"] == []

    @pytest.mark.asyncio
    async def test_shopping_list_add_items(self):
        """Test adding items to shopping list."""
        # Mock existing shopping list
        mock_list = ShoppingList(items=[])
        mock_list.id = 1

        with (
            patch.object(
                self.server.shopping_repo,
                "get_by_thread_id",
                return_value=mock_list,
            ),
            patch.object(self.server.shopping_repo, "update") as mock_update,
        ):

            mock_update.return_value = mock_list

            result = await self.server._handle_shopping_list_manager(
                {
                    "action": "add_items",
                    "thread_id": "test-123",
                    "items": [
                        {
                            "name": "pasta",
                            "quantity": "500g",
                            "unit": "g",
                            "category": "pantry",
                        }
                    ],
                }
            )

            assert result["action"] == "items_added"
            assert result["thread_id"] == "test-123"
            assert result["added_items"] == 1

    @pytest.mark.asyncio
    async def test_shopping_list_get(self):
        """Test getting shopping list."""
        mock_list = ShoppingList(
            items=[
                ShoppingItem(
                    name="pasta",
                    quantity="500g",
                    unit="g",
                    category="pantry",
                )
            ]
        )
        mock_list.id = 1

        with patch.object(
            self.server.shopping_repo,
            "get_by_thread_id",
            return_value=mock_list,
        ):
            result = await self.server._handle_shopping_list_manager(
                {"action": "get", "thread_id": "test-123"}
            )

            assert result["action"] == "retrieved"
            assert result["thread_id"] == "test-123"
            assert len(result["items"]) == 1
            assert result["items"][0]["name"] == "pasta"

    @pytest.mark.asyncio
    async def test_shopping_list_clear(self):
        """Test clearing shopping list."""
        with patch.object(self.server.shopping_repo, "clear") as mock_clear:
            result = await self.server._handle_shopping_list_manager(
                {"action": "clear", "thread_id": "test-123"}
            )

            assert result["action"] == "cleared"
            assert result["thread_id"] == "test-123"
            mock_clear.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_shopping_list_delete(self):
        """Test deleting shopping list (real DB, no mocks)."""
        # 1. Create shopping list
        create_result = await self.server._handle_shopping_list_manager(
            {"action": "create", "thread_id": "test-del"}
        )
        assert create_result["action"] == "created"
        list_id = create_result["list_id"]

        # 2. Delete shopping list
        result = await self.server._handle_shopping_list_manager(
            {"action": "delete", "thread_id": "test-del"}
        )

        # 3. Check response
        assert result["action"] == "deleted"
        assert result["list_id"] == list_id

        # 4. Verify it's no longer in the database
        assert self.server.shopping_repo.get_by_id(list_id) is None

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test handling of unknown tool."""
        # This would be called through the call_tool method
        # We'll test the error handling
        with patch.object(
            self.server,
            "_handle_recipe_finder",
            side_effect=Exception("Test error"),
        ):
            # Simulate the call_tool method behavior
            try:
                await self.server._handle_recipe_finder({"query": "test"})
            except Exception as e:
                assert str(e) == "Test error"


class TestChefAgentMCPClient:
    """Test cases for ChefAgentMCPClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = ChefAgentMCPClient()

    @pytest.mark.asyncio
    async def test_find_recipes(self):
        """Test recipe finding through client."""
        with patch.object(self.client, "session") as mock_session:

            async def mock_call_tool(tool_name, arguments):
                return [
                    TextContent(
                        type="text",
                        text=(
                            '{"recipes": [{"title": "Test Recipe", "id": 1}], '
                            '"total_found": 1}'
                        ),
                    )
                ]

            mock_session.call_tool = mock_call_tool

            result = await self.client.find_recipes(query="test")

            assert result["total_found"] == 1
            assert result["recipes"][0]["title"] == "Test Recipe"

    @pytest.mark.asyncio
    async def test_manage_shopping_list(self):
        """Test shopping list management through client."""
        with patch.object(self.client, "session") as mock_session:

            async def mock_call_tool(tool_name, arguments):
                return [
                    TextContent(
                        type="text",
                        text='{"action": "created", "thread_id": "test-123"}',
                    )
                ]

            mock_session.call_tool = mock_call_tool

            result = await self.client.manage_shopping_list(
                "create", "test-123"
            )

            assert result["action"] == "created"
            assert result["thread_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_client_not_connected_error(self):
        """Test error when client is not connected."""
        with pytest.raises(RuntimeError, match="Client not connected"):
            await self.client.find_recipes(query="test")
