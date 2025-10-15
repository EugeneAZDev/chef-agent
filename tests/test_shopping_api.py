"""
Tests for Shopping List API endpoints.

This module contains comprehensive tests for the shopping list management API,
including creation, item management, and list operations.
"""

import logging
from unittest.mock import patch

from domain.entities import ShoppingItem, ShoppingList
from tests.base_test import BaseAPITest

logger = logging.getLogger(__name__)


class TestShoppingListEndpoints(BaseAPITest):
    """Test cases for shopping list API endpoints."""

    @patch("api.shopping.shopping_repo")
    def test_get_shopping_lists_success(
        self, mock_repo, test_shopping_api_data
    ):
        """Test getting shopping lists for a thread successfully."""
        # Mock repository response - create real ShoppingList object
        mock_list = ShoppingList(
            items=[], created_at="2024-01-01T00:00:00", user_id="test-user-123"
        )
        # Add id and thread_id as attributes for the mock
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_thread_id.return_value = mock_list

        # Test request
        response = self.client.get(
            "/api/v1/shopping/lists?thread_id=test-thread-123&"
            "user_id=test-user"
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "lists" in data
        assert "total" in data
        assert data["thread_id"] == test_shopping_api_data["thread_id"]
        # Verify mock was called with correct parameters
        mock_repo.get_by_thread_id.assert_called_once_with(
            "test-thread-123", "test-user"
        )

    @patch("api.shopping.shopping_repo")
    def test_get_shopping_lists_empty(self, mock_repo, test_shopping_api_data):
        """Test getting shopping lists when none exist."""
        # Mock empty repository response
        mock_repo.get_by_thread_id.return_value = None

        # Test request
        response = self.client.get(
            "/api/v1/shopping/lists?thread_id=test-thread-123&"
            "user_id=test-user"
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["lists"]) == 0

        # Verify mock was called with correct parameters
        mock_repo.get_by_thread_id.assert_called_once_with(
            "test-thread-123", "test-user"
        )

    @patch("api.shopping.shopping_repo")
    def test_create_shopping_list_success(
        self, mock_repo, test_shopping_api_data
    ):
        """Test creating a shopping list successfully."""
        # Mock repository response
        mock_created_list = ShoppingList(items=[])
        mock_created_list.id = 1
        mock_created_list.thread_id = test_shopping_api_data["thread_id"]
        mock_created_list.name = "Test List"
        mock_repo.create.return_value = mock_created_list

        # Test request
        response = self.client.post(
            "/api/v1/shopping/lists?thread_id=test-thread-123&"
            "user_id=test-user",
            json=test_shopping_api_data,
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "Shopping list created successfully" in data["message"]
        assert "list" in data

        # Verify mock was called with correct parameters
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args
        assert call_args[0][1] == "test-thread-123"  # thread_id
        assert call_args[0][2] == "test-user"  # user_id

    @patch("api.shopping.shopping_repo")
    def test_create_shopping_list_repository_error(
        self, mock_repo, test_shopping_api_data
    ):
        """Test creating a shopping list when repository fails."""
        # Mock repository error
        mock_repo.create.side_effect = Exception("Database error")

        # Test request
        response = self.client.post(
            "/api/v1/shopping/lists?thread_id=test-thread-123&"
            "user_id=test-user",
            json=test_shopping_api_data,
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to create shopping list" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_get_shopping_list_by_id_success(
        self, mock_repo, test_shopping_api_data
    ):
        """Test getting a shopping list by ID successfully."""
        # Mock repository response - create real ShoppingList object
        mock_list = ShoppingList(items=[], created_at="2024-01-01T00:00:00")
        # Add id and thread_id as attributes for the mock
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list

        # Test request
        response = self.client.get("/api/v1/shopping/lists/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "list" in data
        assert data["list"]["id"] == 1

    @patch("api.shopping.shopping_repo")
    def test_get_shopping_list_by_id_not_found(
        self, mock_repo, test_shopping_api_data
    ):
        """Test getting a shopping list by ID when not found."""
        # Mock repository response
        mock_repo.get_by_id.return_value = None

        # Test request
        response = self.client.get("/api/v1/shopping/lists/999")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_add_item_to_list_success(self, mock_repo, test_shopping_api_data):
        """Test adding an item to a shopping list successfully."""
        # Mock repository response - create real ShoppingList object
        mock_list = ShoppingList(items=[], created_at="2024-01-01T00:00:00")
        # Add id and thread_id as attributes for the mock
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list
        mock_repo.update.return_value = mock_list

        # Test request
        response = self.client.post(
            "/api/v1/shopping/lists/1/items",
            json=test_shopping_api_data["item_data"],
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert "Item added successfully" in data["message"]

    def test_add_item_to_list_missing_name(self):
        """Test adding an item without required name field."""
        # Test request without name
        incomplete_data = {"amount": 1, "unit": "liter"}

        response = self.client.post(
            "/api/v1/shopping/lists/1/items", json=incomplete_data
        )

        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Missing required field: name" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_add_item_to_list_not_found(
        self, mock_repo, test_shopping_api_data
    ):
        """Test adding an item to a non-existent list."""
        # Mock repository response
        mock_repo.get_by_id.return_value = None

        # Test request
        response = self.client.post(
            "/api/v1/shopping/lists/999/items",
            json=test_shopping_api_data["item_data"],
        )

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_update_list_item_success(self, mock_repo, test_shopping_api_data):
        """Test updating a shopping list item successfully."""
        # Mock repository response
        mock_item = ShoppingItem(
            name="Milk",
            quantity="1",
            unit="liter",
            purchased=False,
        )
        mock_list = ShoppingList(items=[mock_item])
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list
        mock_repo.update.return_value = mock_list

        # Test request
        update_data = {"name": "Organic Milk", "purchased": True}
        response = self.client.put(
            "/api/v1/shopping/lists/1/items/0", json=update_data
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert "Item updated successfully" in data["message"]

    @patch("api.shopping.shopping_repo")
    def test_update_list_item_index_out_of_range(
        self, mock_repo, test_shopping_api_data
    ):
        """Test updating an item with invalid index."""
        # Mock repository response
        mock_list = ShoppingList(items=[])  # Empty list
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list

        # Test request
        update_data = {"name": "Updated Item"}
        response = self.client.put(
            "/api/v1/shopping/lists/1/items/0", json=update_data
        )

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_remove_list_item_success(self, mock_repo, test_shopping_api_data):
        """Test removing a shopping list item successfully."""
        # Mock repository response
        mock_item = ShoppingItem(
            name="Milk",
            quantity="1",
            unit="liter",
        )
        mock_list = ShoppingList(items=[mock_item])
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list
        mock_repo.update.return_value = mock_list

        # Test request
        response = self.client.delete("/api/v1/shopping/lists/1/items/0")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert "Item removed successfully" in data["message"]
        assert "removed_item" in data

    @patch("api.shopping.shopping_repo")
    def test_remove_list_item_index_out_of_range(
        self, mock_repo, test_shopping_api_data
    ):
        """Test removing an item with invalid index."""
        # Mock repository response
        mock_list = ShoppingList(items=[])  # Empty list
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list

        # Test request
        response = self.client.delete("/api/v1/shopping/lists/1/items/0")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_delete_shopping_list_success(
        self, mock_repo, test_shopping_api_data
    ):
        """Test deleting a shopping list successfully."""
        # Mock repository response
        mock_list = ShoppingList(items=[])
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list

        # Test request
        response = self.client.delete("/api/v1/shopping/lists/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert "deleted successfully" in data["message"]

    @patch("api.shopping.shopping_repo")
    def test_delete_shopping_list_not_found(
        self, mock_repo, test_shopping_api_data
    ):
        """Test deleting a non-existent shopping list."""
        # Mock repository response
        mock_repo.get_by_id.return_value = None

        # Test request
        response = self.client.delete("/api/v1/shopping/lists/999")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_get_shopping_lists_repository_error(
        self, mock_repo, test_shopping_api_data
    ):
        """Test getting shopping lists when repository fails."""
        # Mock repository error
        mock_repo.get_by_thread_id.side_effect = Exception("Database error")

        # Test request
        response = self.client.get(
            "/api/v1/shopping/lists?thread_id=test-thread-123&"
            "user_id=test-user"
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get shopping lists" in data["detail"]

    @patch("api.shopping.shopping_repo")
    def test_add_item_repository_error(
        self, mock_repo, test_shopping_api_data
    ):
        """Test adding item when repository fails."""
        # Mock repository response
        mock_list = ShoppingList(items=[])
        mock_list.id = 1
        mock_list.thread_id = test_shopping_api_data["thread_id"]
        mock_repo.get_by_id.return_value = mock_list
        mock_repo.update.side_effect = Exception("Database error")

        # Test request
        response = self.client.post(
            "/api/v1/shopping/lists/1/items",
            json=test_shopping_api_data["item_data"],
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to add item" in data["detail"]
