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

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user_id format to prevent SQL injection."""
        if user_id is not None:
            if (
                not isinstance(user_id, str)
                or not user_id.replace("-", "").replace("_", "").isalnum()
            ):
                raise ValueError("Invalid user_id format")

    def _validate_thread_id(self, thread_id: str) -> None:
        """Validate thread_id format to prevent SQL injection."""
        if thread_id is None:
            raise ValueError("thread_id cannot be None")
        if (
            not isinstance(thread_id, str)
            or not thread_id.replace("-", "").replace("_", "").isalnum()
        ):
            raise ValueError("Invalid thread_id format")

    def create(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Create a new shopping list for a thread."""
        return self._create_shopping_list(shopping_list, thread_id, user_id)

    def update(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Update an existing shopping list."""
        return self._update_shopping_list(shopping_list, thread_id, user_id)

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
        self._validate_thread_id(thread_id)
        self._validate_user_id(user_id)
        # If user_id is provided, search with user filter for security
        if user_id:
            query = (
                "SELECT * FROM shopping_lists WHERE thread_id = ? "
                "AND user_id = ?"
            )
            rows = self.db.execute_query(query, (thread_id, user_id))
        else:
            # For anonymous users, only allow access to lists without user_id
            query = (
                "SELECT * FROM shopping_lists WHERE thread_id = ? "
                "AND user_id IS NULL"
            )
            rows = self.db.execute_query(query, (thread_id,))

        if not rows:
            return None

        row = rows[0]
        return self._row_to_shopping_list(row)

    def _get_by_thread_id_with_lock(
        self, thread_id: str, user_id: str = None
    ) -> List[ShoppingList]:
        """Get shopping lists for a specific thread with user filtering."""
        if user_id:
            query = (
                "SELECT * FROM shopping_lists WHERE thread_id = ? "
                "AND user_id = ? ORDER BY created_at DESC"
            )
            rows = self.db.execute_query(query, (thread_id, user_id))
        else:
            query = (
                "SELECT * FROM shopping_lists WHERE thread_id = ? "
                "AND user_id IS NULL ORDER BY created_at DESC"
            )
            rows = self.db.execute_query(query, (thread_id,))

        if not rows:
            return []

        return [self._row_to_shopping_list(row) for row in rows]

    def save(
        self, shopping_list: ShoppingList, thread_id: str, user_id: str = None
    ) -> ShoppingList:
        """Save a shopping list for a specific thread and optionally user."""
        self._validate_thread_id(thread_id)
        self._validate_user_id(user_id)
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()

                items_data = self._items_to_json(shopping_list.items)

                # Use proper UPSERT logic without ON CONFLICT to handle
                # race conditions
                # This is atomic and prevents data loss
                if user_id is not None:
                    # For authenticated users, first try to update existing
                    # record
                    update_query = """
                        UPDATE shopping_lists
                        SET items = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE thread_id = ? AND user_id = ?
                    """
                    rows_affected = self.db.execute_update_in_transaction(
                        update_query, (items_data, thread_id, user_id)
                    )

                    # If no rows were updated, insert new record
                    if rows_affected == 0:
                        insert_query = """
                            INSERT INTO shopping_lists
                            (thread_id, user_id, items, created_at, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """
                        self.db.execute_update_in_transaction(
                            insert_query, (thread_id, user_id, items_data)
                        )
                else:
                    # For anonymous users, first try to update existing record
                    update_query = """
                        UPDATE shopping_lists
                        SET items = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE thread_id = ? AND user_id IS NULL
                    """
                    rows_affected = self.db.execute_update_in_transaction(
                        update_query, (items_data, thread_id)
                    )

                    # If no rows were updated, insert new record
                    if rows_affected == 0:
                        insert_query = """
                            INSERT INTO shopping_lists
                            (thread_id, user_id, items, created_at, updated_at)
                            VALUES (?, NULL, ?, CURRENT_TIMESTAMP,
                                    CURRENT_TIMESTAMP)
                        """
                        self.db.execute_update_in_transaction(
                            insert_query, (thread_id, items_data)
                        )

                # Get the created/updated shopping list
                result = self.get_by_thread_id(thread_id, user_id)
                if not result:
                    raise RuntimeError("Failed to save shopping list")

                self.db.commit_transaction()
                return result

            except Exception as e:
                self.db.rollback_transaction()
                raise e

    def add_items(
        self, thread_id: str, items: List[ShoppingItem], user_id: str = None
    ) -> None:
        """Add items to an existing shopping list."""
        self._validate_thread_id(thread_id)
        self._validate_user_id(user_id)
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()

                # First, ensure shopping list exists, create if not
                if user_id is not None:
                    # For authenticated users, check if list exists first
                    check_query = """
                        SELECT id FROM shopping_lists
                        WHERE thread_id = ? AND user_id = ?
                    """
                    existing = self.db.execute_query(
                        check_query, (thread_id, user_id)
                    )

                    if not existing:
                        # Create new list for authenticated user
                        insert_query = """
                            INSERT INTO shopping_lists
                            (thread_id, user_id, items, created_at, updated_at)
                            VALUES (?, ?, '[]', CURRENT_TIMESTAMP,
                                    CURRENT_TIMESTAMP)
                        """
                        self.db.execute_update_in_transaction(
                            insert_query, (thread_id, user_id)
                        )
                else:
                    # For anonymous users, check if list exists first
                    check_query = """
                        SELECT id FROM shopping_lists
                        WHERE thread_id = ? AND user_id IS NULL
                    """
                    existing = self.db.execute_query(check_query, (thread_id,))

                    if not existing:
                        # Create new list for anonymous user
                        insert_query = """
                            INSERT INTO shopping_lists
                            (thread_id, user_id, items, created_at, updated_at)
                            VALUES (?, NULL, '[]', CURRENT_TIMESTAMP,
                                    CURRENT_TIMESTAMP)
                        """
                        self.db.execute_update_in_transaction(
                            insert_query, (thread_id,)
                        )

                # Now add items atomically using efficient JSON operations
                # For small lists (<100 items), use the simple
                # approach
                # For large lists, we could optimize further with batch operations
                if len(items) <= 100:
                    # Simple approach: get current items, add new ones, update
                    if user_id is not None:
                        # Get current items
                        current_query = """
                            SELECT items FROM shopping_lists
                            WHERE thread_id = ? AND user_id = ?
                        """
                        current_rows = self.db.execute_query(
                            current_query, (thread_id, user_id)
                        )
                    else:
                        # Get current items for anonymous user
                        current_query = """
                            SELECT items FROM shopping_lists
                            WHERE thread_id = ? AND user_id IS NULL
                        """
                        current_rows = self.db.execute_query(
                            current_query, (thread_id,)
                        )

                    current_items = []
                    if current_rows:
                        # Parse existing items
                        try:
                            current_items_data = json.loads(
                                current_rows[0]["items"] or "[]"
                            )
                            current_items = [
                                ShoppingItem(
                                    name=item["name"],
                                    quantity=item["quantity"],
                                    unit=item["unit"],
                                    category=item.get("category"),
                                    purchased=item.get("purchased", False),
                                )
                                for item in current_items_data
                            ]
                        except (json.JSONDecodeError, KeyError, TypeError):
                            current_items = []

                    # Add new items to current items
                    current_items.extend(items)

                    # Serialize combined items
                    combined_items_data = self._items_to_json(current_items)

                    # Update with combined items in one operation
                    if user_id is not None:
                        update_query = """
                            UPDATE shopping_lists
                            SET items = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE thread_id = ? AND user_id = ?
                        """
                        self.db.execute_update_in_transaction(
                            update_query,
                            (combined_items_data, thread_id, user_id),
                        )
                    else:
                        update_query = """
                            UPDATE shopping_lists
                            SET items = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE thread_id = ? AND user_id IS NULL
                        """
                        self.db.execute_update_in_transaction(
                            update_query, (combined_items_data, thread_id)
                        )
                else:
                    # For large lists, use more efficient approach
                    # Create a temporary table with new items
                    temp_table_query = """
                        CREATE TEMP TABLE temp_new_items (
                            name TEXT,
                            quantity TEXT,
                            unit TEXT,
                            category TEXT,
                            purchased BOOLEAN
                        )
                    """
                    self.db.execute_update_in_transaction(temp_table_query)

                    # Insert new items into temp table
                    for item in items:
                        insert_temp_query = """
                            INSERT INTO temp_new_items
                            (name, quantity, unit, category, purchased)
                            VALUES (?, ?, ?, ?, ?)
                        """
                        self.db.execute_update_in_transaction(
                            insert_temp_query,
                            (
                                item.name,
                                item.quantity,
                                item.unit,
                                item.category,
                                item.purchased,
                            ),
                        )

                    # Merge with existing items using JSON functions
                    if user_id is not None:
                        merge_query = """
                            UPDATE shopping_lists
                            SET items = (
                                SELECT json_group_array(
                                    json_object(
                                        'name', name,
                                        'quantity', quantity,
                                        'unit', unit,
                                        'category', category,
                                        'purchased', purchased
                                    )
                                )
                                FROM (
                                    SELECT name, quantity, unit, category,
                                           purchased
                                    FROM json_each(shopping_lists.items)
                                    UNION ALL
                                    SELECT name, quantity, unit, category,
                                           purchased
                                    FROM temp_new_items
                                )
                            ),
                            updated_at = CURRENT_TIMESTAMP
                            WHERE thread_id = ? AND user_id = ?
                        """
                        self.db.execute_update_in_transaction(
                            merge_query, (thread_id, user_id)
                        )
                    else:
                        merge_query = """
                            UPDATE shopping_lists
                            SET items = (
                                SELECT json_group_array(
                                    json_object(
                                        'name', name,
                                        'quantity', quantity,
                                        'unit', unit,
                                        'category', category,
                                        'purchased', purchased
                                    )
                                )
                                FROM (
                                    SELECT name, quantity, unit, category,
                                           purchased
                                    FROM json_each(shopping_lists.items)
                                    UNION ALL
                                    SELECT name, quantity, unit, category,
                                           purchased
                                    FROM temp_new_items
                                )
                            ),
                            updated_at = CURRENT_TIMESTAMP
                            WHERE thread_id = ? AND user_id IS NULL
                        """
                        self.db.execute_update_in_transaction(
                            merge_query, (thread_id,)
                        )

                    # Clean up temp table
                    drop_temp_query = "DROP TABLE temp_new_items"
                    self.db.execute_update_in_transaction(drop_temp_query)

                self.db.commit_transaction()
            except Exception as e:
                self.db.rollback_transaction()
                raise e

    def clear(self, thread_id: str, user_id: str = None) -> None:
        """Clear all items from a shopping list."""
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()
                # Check if shopping list exists to prevent race conditions
                if user_id:
                    lock_query = (
                        "SELECT id FROM shopping_lists WHERE thread_id = ? "
                        "AND user_id = ?"
                    )
                    locked_rows = self.db.execute_query(
                        lock_query, (thread_id, user_id)
                    )
                else:
                    lock_query = (
                        "SELECT id FROM shopping_lists WHERE thread_id = ? "
                        "AND user_id IS NULL"
                    )
                    locked_rows = self.db.execute_query(
                        lock_query, (thread_id,)
                    )
                if not locked_rows:
                    self.db.rollback_transaction()
                    return

                query = (
                    "UPDATE shopping_lists SET items = '[]' "
                    "WHERE thread_id = ?"
                )
                self.db.execute_update(query, (thread_id,))
                self.db.commit_transaction()
            except Exception as e:
                self.db.rollback_transaction()
                raise e

    def delete(self, list_id: int) -> bool:
        """Delete a shopping list by ID."""
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()
                # Check if shopping list exists to prevent race conditions
                lock_query = "SELECT id FROM shopping_lists WHERE id = ?"
                locked_rows = self.db.execute_query(lock_query, (list_id,))
                if not locked_rows:
                    self.db.rollback_transaction()
                    return False

                affected_rows = self.db.execute_update(
                    "DELETE FROM shopping_lists WHERE id = ?", (list_id,)
                )
                self.db.commit_transaction()
                return affected_rows > 0
            except Exception as e:
                self.db.rollback_transaction()
                raise e

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

        # Check for integer overflow (SQLite max is 2^63-1)
        if list_id > 2**63 - 1:
            raise ValueError(
                "Shopping list ID overflow - database limit reached"
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
