"""
Database connection and schema management.
"""

import sqlite3
from typing import Optional

# Import config here to avoid circular imports
try:
    from config import settings
except ImportError:
    # Fallback for when config is not available
    class DefaultSettings:
        sqlite_db = "chef_agent.db"

    settings = DefaultSettings()


class Database:
    """SQLite database connection and schema management."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.sqlite_db
        self._connection: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating it if necessary."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._create_schema()
        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        conn = self.get_connection()

        # Create recipes table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                instructions TEXT NOT NULL DEFAULT '',
                prep_time_minutes INTEGER,
                cook_time_minutes INTEGER,
                servings INTEGER,
                difficulty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create tags table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """
        )

        # Create recipe_tags junction table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_tags (
                recipe_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (recipe_id, tag_id),
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) "
                "ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """
        )

        # Create ingredients table (stored as JSON)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                ingredients JSON NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                ON DELETE CASCADE
            )
        """
        )

        # Create shopping lists table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT UNIQUE NOT NULL,
                items JSON NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_shopping_lists_thread_id "
            "ON shopping_lists(thread_id)"
        )

        conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a SELECT query and return results."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the last row ID."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid

    def begin_transaction(self) -> None:
        """Begin a database transaction."""
        conn = self.get_connection()
        conn.execute("BEGIN TRANSACTION")

    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        conn = self.get_connection()
        conn.commit()

    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        conn = self.get_connection()
        conn.rollback()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
