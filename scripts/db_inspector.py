#!/usr/bin/env python3
"""
Database inspector script for viewing database structure and data.
"""

import sys
import sqlite3
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.db.database import Database


def inspect_database(db_path: str = "chef_agent.db"):
    """Inspect database structure and show sample data."""
    
    if not Path(db_path).exists():
        print(f"Database file {db_path} not found!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("DATABASE STRUCTURE INSPECTION")
    print("=" * 60)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        print(f"  - {table['name']}")
    
    print("\n" + "=" * 60)
    print("TABLE STRUCTURES")
    print("=" * 60)
    
    # Get structure for each table
    for table in tables:
        table_name = table['name']
        print(f"\nTable: {table_name}")
        print("-" * 40)
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  {col['name']:<20} {col['type']:<15} {'NOT NULL' if col['notnull'] else 'NULL'}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()['count']
        print(f"  Rows: {count}")
        
        # Show sample data (first 3 rows)
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()
            print(f"  Sample data:")
            for i, row in enumerate(sample_data, 1):
                print(f"    Row {i}: {dict(row)}")
    
    print("\n" + "=" * 60)
    print("INDEXES")
    print("=" * 60)
    
    # Get indexes
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
    indexes = cursor.fetchall()
    
    for idx in indexes:
        print(f"  {idx['name']}: {idx['sql']}")
    
    conn.close()
    print("\nInspection complete!")


def run_sample_queries(db_path: str = "chef_agent.db"):
    """Run some sample queries to demonstrate database usage."""
    
    if not Path(db_path).exists():
        print(f"Database file {db_path} not found!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("SAMPLE QUERIES")
    print("=" * 60)
    
    # Query 1: All recipes
    print("\n1. All recipes:")
    cursor.execute("SELECT id, title, prep_time_minutes, cook_time_minutes, servings FROM recipes")
    recipes = cursor.fetchall()
    for recipe in recipes:
        print(f"  ID: {recipe['id']}, Title: {recipe['title']}, Prep: {recipe['prep_time_minutes']}min, Cook: {recipe['cook_time_minutes']}min, Servings: {recipe['servings']}")
    
    # Query 2: All tags
    print("\n2. All tags:")
    cursor.execute("SELECT * FROM tags")
    tags = cursor.fetchall()
    for tag in tags:
        print(f"  ID: {tag['id']}, Name: {tag['name']}")
    
    # Query 3: Shopping lists
    print("\n3. Shopping lists:")
    cursor.execute("SELECT thread_id, items, created_at FROM shopping_lists")
    lists = cursor.fetchall()
    for list_item in lists:
        items = json.loads(list_item['items'])
        print(f"  Thread: {list_item['thread_id']}, Items: {len(items)}, Created: {list_item['created_at']}")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "chef_agent.db"
    
    inspect_database(db_path)
    run_sample_queries(db_path)
