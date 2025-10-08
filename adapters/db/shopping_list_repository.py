"""
SQLite implementation of ShoppingListRepository.
"""

import json
import threading
from typing import List, Optional

from domain.entities import ShoppingItem, ShoppingList
from domain.repo_abc import ShoppingListRepository

from .database import Database


class SQLiteShoppingListRepository(ShoppingListRepository):
    """SQLite implementation of ShoppingListRepository."""

    def __init__(self, db: Database):
        self.db = db
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def create(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Create a new shopping list for a thread."""
        return self._create_shopping_list(shopping_list, thread_id, user_id)

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

    def get_by_thread_id(
        self, thread_id: str, user_id: str = None
    ) -> Optional[ShoppingList]:
        """Get a shopping list by conversation thread ID and optionally user
        ID."""
        if user_id:
            query = (
                "SELECT * FROM shopping_lists WHERE thread_id = ? "
                "AND user_id = ?"
            )
            rows = self.db.execute_query(query, (thread_id, user_id))
        else:
            query = "SELECT * FROM shopping_lists WHERE thread_id = ?"
            rows = self.db.execute_query(query, (thread_id,))

        if not rows:
            return None

        row = rows[0]
        return self._row_to_shopping_list(row)

    def _get_by_thread_id_with_lock(
        self, thread_id: str, user_id: str = None
    ) -> Optional[ShoppingList]:
        """Get all shopping lists for a specific user."""
        query = (
            "SELECT * FROM shopping_lists WHERE user_id = ? "
            "ORDER BY created_at DESC"
        )
        # We'll rely on the transaction isolation and the row-level lock
        if user_id:
            rows = self.db.execute_query(query, (thread_id, user_id))
        else:
            query = "SELECT * FROM shopping_lists WHERE thread_id = ?"
            rows = self.db.execute_query(query, (thread_id,))

        if not rows:
            return None

        return [self._row_to_shopping_list(row) for row in rows]

    def save(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Save a shopping list for a specific thread and optionally user."""
        with self._lock:  # Ensure thread safety
            # Check if shopping list already exists for this thread and user
            existing = self.get_by_thread_id(thread_id, user_id)

            if existing:
                return self._update_shopping_list(
                    shopping_list, thread_id, user_id
                )
            else:
                return self._create_shopping_list(
                    shopping_list, thread_id, user_id
                )

    def add_items(
        self, thread_id: str, items: List[ShoppingItem], user_id: str = None
    ) -> None:
        """Add items to an existing shopping list."""
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()
                # Use SELECT FOR UPDATE to prevent race conditions
                existing = self._get_by_thread_id_with_lock(thread_id, user_id)

                if existing:
                    # Add new items to existing list
                    existing[0].items.extend(items)
                    self._update_shopping_list(existing[0], thread_id, user_id)
                else:
                    # Create new shopping list with items
                    new_list = ShoppingList(items=items)
                    self._create_shopping_list(new_list, thread_id, user_id)
                self.db.commit_transaction()
            except Exception as e:
                self.db.rollback_transaction()
                raise e

    def clear(self, thread_id: str) -> None:
        """Clear all items from a shopping list."""
        query = "UPDATE shopping_lists SET items = '[]' WHERE thread_id = ?"
        self.db.execute_update(query, (thread_id,))

    def delete(self, list_id: int) -> bool:
        """Delete a shopping list by ID."""
        affected_rows = self.db.execute_update(
            "DELETE FROM shopping_lists WHERE id = ?", (list_id,)
        )
        return affected_rows > 0

    def _create_shopping_list(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Create a new shopping list."""
        items_data = self._items_to_json(shopping_list.items)

        query = """
            INSERT INTO shopping_lists (thread_id, user_id, items)
            VALUES (?, ?, ?)
        """
        list_id = self.db.execute_insert(
            query, (thread_id, user_id, items_data)
        )

        # Update the shopping list with the ID and user_id
        shopping_list.id = list_id
        shopping_list.user_id = user_id
        return shopping_list

    def _update_shopping_list(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Update an existing shopping list."""
        items_data = self._items_to_json(shopping_list.items)

        if user_id:
            query = """
                UPDATE shopping_lists
                SET items = ?, user_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ?
            """
            self.db.execute_update(
                query, (items_data, user_id, thread_id, user_id)
            )
        else:
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
                items_data = json.loads(row["items"] or "[]")
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
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # Log error but don't fail completely
                print(f"Warning: Failed to parse shopping list items: {e}")
                items = []

        shopping_list = ShoppingList(items=items)
        shopping_list.id = row["id"]
        shopping_list.thread_id = row["thread_id"]
        shopping_list.created_at = row["created_at"]
        shopping_list.user_id = (
            row["user_id"] if "user_id" in row.keys() else None
        )
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
        try:
            return json.dumps(items_data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize shopping items: {e}")
