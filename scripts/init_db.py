#!/usr/bin/env python3
"""
Database initialization script.
Creates the database file and schema if it doesn't exist.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.db import Database


def init_database(db_path: str = "chef_agent.db", force_recreate: bool = False):
    """Initialize database with schema."""
    
    print(f"Initializing database at: {os.path.abspath(db_path)}")
    
    # Check if database already exists
    if Path(db_path).exists():
        if force_recreate:
            os.remove(db_path)
            print("Existing database removed (force recreate).")
        else:
            print(f"Database file already exists at: {db_path}")
            print("Schema will be validated/created if needed.")
    
    # Initialize database
    try:
        db = Database(db_path)
        
        # This will create the schema if it doesn't exist
        conn = db.get_connection()
        print("Database schema validated/created successfully!")
        
        # Show tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['name']}")
        
        # Show some basic info
        cursor = conn.execute("SELECT COUNT(*) as count FROM recipes")
        recipe_count = cursor.fetchone()['count']
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM shopping_lists")
        list_count = cursor.fetchone()['count']
        
        print(f"\nDatabase status:")
        print(f"  - Recipes: {recipe_count}")
        print(f"  - Shopping lists: {list_count}")
        
        db.close()
        print(f"\nDatabase ready at: {os.path.abspath(db_path)}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
    
    return True


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "chef_agent.db"
    success = init_database(db_path)
    sys.exit(0 if success else 1)
