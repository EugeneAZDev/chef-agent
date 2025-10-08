"""Database migration system."""

import os
import sqlite3
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from adapters.db.database import Database

__all__ = ["MigrationRunner"]


class MigrationRunner:
    """Handles database migrations."""

    def __init__(self, db: "Database"):
        self.db = db

    def run_migrations(self) -> None:
        """Run all pending migrations."""
        # Create migrations table if it doesn't exist
        self._create_migrations_table()

        # Get list of migration files
        migration_files = self._get_migration_files()

        # Run each migration
        for migration_file in migration_files:
            if not self._is_migration_applied(migration_file):
                self._run_migration(migration_file)

    def _create_migrations_table(self) -> None:
        """Create migrations tracking table."""
        self.db.execute_update(
            """
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    def _get_migration_files(self) -> List[str]:
        """Get list of migration files in order."""
        migrations_dir = "migrations"
        if not os.path.exists(migrations_dir):
            return []

        files = [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
        # Sort by filename (which should include timestamp/version)
        files.sort()
        return files

    def _is_migration_applied(self, filename: str) -> bool:
        """Check if migration has been applied."""
        try:
            # Try new schema first (version column)
            result = self.db.execute_query(
                "SELECT version FROM migrations WHERE version = ?", (filename,)
            )
            return len(result) > 0
        except sqlite3.OperationalError:
            try:
                # Fall back to old schema (id, filename columns)
                result = self.db.execute_query(
                    "SELECT id FROM migrations WHERE filename = ?", (filename,)
                )
                return len(result) > 0
            except sqlite3.OperationalError:
                # Table doesn't exist yet, migration not applied
                return False

    def _run_migration(self, filename: str) -> None:
        """Run a single migration file."""
        migration_path = os.path.join("migrations", filename)

        with open(migration_path, "r") as f:
            migration_sql = f.read()

        # Split by semicolon and execute each statement
        statements = self._split_sql_statements(migration_sql)

        try:
            self.db.begin_transaction()

            for stmt in statements:
                if stmt.strip():
                    self.db.execute_update(stmt)

            # Mark migration as applied - check table schema first
            try:
                # Try new schema first (version column)
                self.db.execute_update(
                    "INSERT INTO migrations (version) VALUES (?)", (filename,)
                )
            except sqlite3.OperationalError:
                # Fall back to old schema (id, filename columns)
                self.db.execute_update(
                    "INSERT INTO migrations (filename) VALUES (?)", (filename,)
                )

            self.db.commit_transaction()
            print(f"Applied migration: {filename}")

        except Exception as e:
            self.db.rollback_transaction()
            print(f"Error applying migration {filename}: {e}")
            raise e

    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements."""
        # Remove comments and split by semicolon
        lines = sql.split("\n")
        clean_lines = []

        for line in lines:
            # Remove SQL comments
            if line.strip().startswith("--"):
                continue
            clean_lines.append(line)

        sql_clean = "\n".join(clean_lines)

        # Split by semicolon, but be careful with semicolons in strings
        statements = []
        current_statement = ""
        in_string = False
        string_char = None

        for char in sql_clean:
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif char == ";" and not in_string:
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
                continue

            current_statement += char

        # Add final statement if exists
        if current_statement.strip():
            statements.append(current_statement.strip())

        return statements
