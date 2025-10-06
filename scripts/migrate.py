#!/usr/bin/env python3
"""
Database migration script.

Usage:
  python -m scripts.migrate                    # Apply all pending migrations
  python -m scripts.migrate --undo 0002       # Rollback migration 0002
  python -m scripts.migrate --status          # Show migration status
"""

import sqlite3
import sys
import argparse
from pathlib import Path
from typing import Set

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self):
        self.db_path = settings.sqlite_db
        self.migrations_dir = project_root / settings.migrations_dir
        self.version_table = "migrations"
    
    def ensure_meta_table(self) -> None:
        """Create migrations metadata table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.version_table} (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def get_applied_migrations(self) -> Set[str]:
        """Get set of applied migration versions."""
        self.ensure_meta_table()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"SELECT version FROM {self.version_table}")
            return {row[0] for row in cursor.fetchall()}
    
    def apply_migration(self, version: str, sql_content: str) -> None:
        """Apply a single migration."""
        print(f"  Applying migration {version}...")
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.executescript(sql_content)
                conn.execute(
                    f"INSERT INTO {self.version_table}(version) VALUES (?)",
                    (version,)
                )
                print(f"  ✅ Migration {version} applied successfully")
            except Exception as e:
                print(f"  ❌ Error applying migration {version}: {e}")
                raise
    
    def rollback_migration(self, version: str) -> None:
        """Rollback a specific migration."""
        undo_file = self.migrations_dir / f"{version}_undo.sql"
        if not undo_file.exists():
            print(f"  ❌ Rollback file {undo_file} not found")
            return
        
        print(f"  Rolling back migration {version}...")
        with sqlite3.connect(self.db_path) as conn:
            try:
                undo_sql = undo_file.read_text(encoding="utf-8")
                conn.executescript(undo_sql)
                conn.execute(
                    f"DELETE FROM {self.version_table} WHERE version = ?",
                    (version,)
                )
                print(f"  ✅ Migration {version} rolled back successfully")
            except Exception as e:
                print(f"  ❌ Error rolling back migration {version}: {e}")
                raise
    
    def get_pending_migrations(self) -> list:
        """Get list of pending migrations."""
        applied = self.get_applied_migrations()
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        
        pending = []
        for file_path in migration_files:
            version = file_path.stem
            if not version.endswith("_undo") and version not in applied:
                pending.append((version, file_path))
        
        return pending
    
    def apply_all_pending(self) -> None:
        """Apply all pending migrations."""
        pending = self.get_pending_migrations()
        
        if not pending:
            print("  ✅ No pending migrations")
            return
        
        print(f"  Found {len(pending)} pending migrations:")
        for version, file_path in pending:
            print(f"    - {version}")
        
        for version, file_path in pending:
            sql_content = file_path.read_text(encoding="utf-8")
            self.apply_migration(version, sql_content)
        
        print("  ✅ All migrations applied successfully")
    
    def show_status(self) -> None:
        """Show migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print(f"  Database: {self.db_path}")
        print(f"  Applied migrations: {len(applied)}")
        for version in sorted(applied):
            print(f"    ✅ {version}")
        
        print(f"  Pending migrations: {len(pending)}")
        for version, _ in pending:
            print(f"    ⏳ {version}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument("--undo", help="Rollback specific migration")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    
    args = parser.parse_args()
    
    manager = MigrationManager()
    
    if args.status:
        manager.show_status()
    elif args.undo:
        manager.rollback_migration(args.undo)
    else:
        manager.apply_all_pending()


if __name__ == "__main__":
    main()
