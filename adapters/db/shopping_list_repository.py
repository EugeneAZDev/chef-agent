"""
SQLite implementation of ShoppingListRepository.
"""

import json
from typing import List, Optional

from domain.entities import ShoppingItem, ShoppingList
from domain.repo_abc import ShoppingListRepository

from .database import Database


class SQLiteShoppingListRepository(ShoppingListRepository):
    """SQLite implementation of ShoppingListRepository."""

    def __init__(self, db: Database):
        self.db = db

    def create(
        self, shopping_list: ShoppingList, thread_id: str
    ) -> ShoppingList:
        """Create a new shopping list for a thread."""
        return self._create_shopping_list(shopping_list, thread_id)

    def update(
        self, shopping_list: ShoppingList, thread_id: str
    ) -> ShoppingList:
        """Update an existing shopping list."""
        return self._create_shopping_list(shopping_list, thread_id)

    def get_by_id(self, list_id: int) -> Optional[ShoppingList]:
        """Get a shopping list by its ID."""
        query = "SELECT * FROM shopping_lists WHERE id = ?"
        rows = self.db.execute_query(query, (list_id,))

        if not rows:
            return None

        row = rows[0]
        return self._row_to_shopping_list(row)

    def get_by_thread_id(self, thread_id: str) -> Optional[ShoppingList]:
        """Get a shopping list by conversation thread ID."""
        query = "SELECT * FROM shopping_lists WHERE thread_id = ?"
        rows = self.db.execute_query(query, (thread_id,))

        if not rows:
            return None

        row = rows[0]
        return self._row_to_shopping_list(row)

    def save(
        self, shopping_list: ShoppingList, thread_id: str
    ) -> ShoppingList:
        """Save a shopping list for a specific thread."""
        # Check if shopping list already exists for this thread
        existing = self.get_by_thread_id(thread_id)

        if existing:
            return self._update_shopping_list(shopping_list, thread_id)
        else:
            return self._create_shopping_list(shopping_list, thread_id)

    def add_items(self, thread_id: str, items: List[ShoppingItem]) -> None:
        """Add items to an existing shopping list."""
        existing = self.get_by_thread_id(thread_id)

        if existing:
            # Add new items to existing list
            existing.items.extend(items)
            self._update_shopping_list(existing, thread_id)
        else:
            # Create new shopping list with items
            new_list = ShoppingList(items=items)
            self._create_shopping_list(new_list, thread_id)

    def clear(self, thread_id: str) -> None:
        """Clear all items from a shopping list."""
        query = (
            "UPDATE shopping_lists SET items = '[]', updated_at = CURRENT_TIMESTAMP "
            "WHERE thread_id = ?"
        )
        self.db.execute_update(query, (thread_id,))

    def delete(self, list_id: int) -> bool:
        """Delete a shopping list by ID."""
        affected_rows = self.db.execute_update(
            "DELETE FROM shopping_lists WHERE id = ?", (list_id,)
        )
        return affected_rows > 0

    def _create_shopping_list(
        self, shopping_list: ShoppingList, thread_id: str
    ) -> ShoppingList:
        """Create a new shopping list."""
        items_data = self._items_to_json(shopping_list.items)

        query = """
            INSERT INTO shopping_lists (thread_id, items)
            VALUES (?, ?)
        """
        list_id = self.db.execute_insert(query, (thread_id, items_data))

        # Update the shopping list with the ID
        shopping_list.id = list_id
        return shopping_list

    def _update_shopping_list(
        self, shopping_list: ShoppingList, thread_id: str
    ) -> ShoppingList:
        """Update an existing shopping list."""
        items_data = self._items_to_json(shopping_list.items)

        query = """
            UPDATE shopping_lists
            SET items = ?, updated_at = CURRENT_TIMESTAMP
            WHERE thread_id = ?
        """
        self.db.execute_update(query, (items_data, thread_id))

        return shopping_list

    def _row_to_shopping_list(self, row) -> ShoppingList:
        """Convert database row to ShoppingList entity."""
        items = []
        if row["items"]:
            try:
                items_data = json.loads(row["items"])
                items = [
                    ShoppingItem(
                        name=item["name"],
                        quantity=item["quantity"],
                        unit=item["unit"],
                        category=item.get("category"),
                        purchased=item.get("purchased", False),
                    )
                    for item in items_data
                ]
            except (json.JSONDecodeError, KeyError):
                items = []

        shopping_list = ShoppingList(items=items)
        shopping_list.id = row["id"]
        shopping_list.created_at = row["created_at"]
        return shopping_list

    def _items_to_json(self, items: List[ShoppingItem]) -> str:
        """Convert shopping items to JSON string."""
        items_data = [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "purchased": item.purchased,
            }
            for item in items
        ]
        return json.dumps(items_data)
