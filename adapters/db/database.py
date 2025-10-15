"""
Database connection and schema management.
"""

# Default database path - can be overridden by config
import os
import sqlite3
import threading
from typing import Optional

DEFAULT_DB_PATH = os.getenv("CHEF_AGENT_DB_PATH", "chef_agent.db")


class Database:
    """SQLite database connection and schema management."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._connection: Optional[sqlite3.Connection] = None
        self._local = threading.local()
        self._run_migrations()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating it if necessary."""
        # Use thread-local storage for thread safety
        if (
            not hasattr(self._local, "connection")
            or self._local.connection is None
        ):
            self._local.connection = sqlite3.connect(
                self.db_path, check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            # Set busy timeout for better handling of concurrent access
            self._local.connection.execute("PRAGMA busy_timeout = 10000")
            # Enable foreign key constraints
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            try:
                self._local.connection.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._local.connection = None

    def cleanup_connections(self) -> None:
        """Clean up all thread-local connections."""
        # This is a best-effort cleanup
        try:
            if hasattr(self._local, "connection") and self._local.connection:
                self._local.connection.close()
                self._local.connection = None
        except Exception:
            pass

    def _run_migrations(self) -> None:
        """Run database migrations."""
        try:
            # Import here to avoid circular import
            from .migrations import MigrationRunner

            migration_runner = MigrationRunner(self)
            migration_runner.run_migrations()
        except Exception as e:
            print(f"Error running migrations: {e}")
            raise e

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

    def execute_update_in_transaction(
        self, query: str, params: tuple = ()
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE query within a transaction."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        return cursor.rowcount

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the last row ID."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid

    def execute_insert_in_transaction(
        self, query: str, params: tuple = ()
    ) -> int:
        """Execute an INSERT query in transaction and return last row ID."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        # For INSERT OR IGNORE, check rowcount to see if insert actually
        # happened
        if cursor.rowcount == 0:
            return 0  # Insert was ignored
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
