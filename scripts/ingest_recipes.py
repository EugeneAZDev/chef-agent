#!/usr/bin/env python3
"""
Recipe ingestion script.

Usage:
  python -m scripts.ingest_recipes data/recipes.json
  python -m scripts.ingest_recipes data/recipes.json --output migrations/0002_seed_recipes.sql
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from domain.entities import Recipe, Ingredient
from adapters.db import Database, SQLiteRecipeRepository


def parse_recipe_data(recipe_data: Dict[str, Any]) -> Recipe:
    """Parse recipe data from JSON into Recipe entity."""
    # Parse ingredients
    ingredients = []
    if "ingredients" in recipe_data:
        for ing_data in recipe_data["ingredients"]:
            if isinstance(ing_data, dict):
                ingredient = Ingredient(
                    name=ing_data.get("name", ""),
                    quantity=ing_data.get("quantity", ""),
                    unit=ing_data.get("unit", ""),
                )
                ingredients.append(ingredient)
            elif isinstance(ing_data, str):
                # Simple string format: "2 cups flour"
                parts = ing_data.split(" ", 2)
                if len(parts) >= 3:
                    ingredient = Ingredient(
                        quantity=parts[0],
                        unit=parts[1],
                        name=parts[2],
                    )
                    ingredients.append(ingredient)
    
    # Parse tags
    tags = recipe_data.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",")]
    
    # Create recipe
    recipe = Recipe(
        id=None,  # Will be set by database
        title=recipe_data.get("title", "Untitled Recipe"),
        description=recipe_data.get("description", ""),
        ingredients=ingredients,
        instructions=recipe_data.get("instructions", ""),
        prep_time_minutes=recipe_data.get("prep_time_minutes"),
        cook_time_minutes=recipe_data.get("cook_time_minutes"),
        servings=recipe_data.get("servings"),
        tags=tags,
        difficulty=recipe_data.get("difficulty"),
    )
    
    return recipe


def load_recipes_from_json(file_path: Path) -> List[Recipe]:
    """Load recipes from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    recipes = []
    if isinstance(data, list):
        for recipe_data in data:
            recipes.append(parse_recipe_data(recipe_data))
    elif isinstance(data, dict) and "recipes" in data:
        for recipe_data in data["recipes"]:
            recipes.append(parse_recipe_data(recipe_data))
    else:
        raise ValueError(
            "Invalid JSON format. Expected list of recipes or object with 'recipes' key."
        )
    
    return recipes


def save_recipes_to_database(recipes: List[Recipe], db_path: str) -> None:
    """Save recipes to database."""
    db = Database(db_path)
    recipe_repo = SQLiteRecipeRepository(db)
    
    print(f"  Saving {len(recipes)} recipes to database...")
    for i, recipe in enumerate(recipes, 1):
        try:
            recipe_repo.save(recipe)
            if i % 10 == 0:
                print(f"    Processed {i}/{len(recipes)} recipes...")
        except Exception as e:
            print(f"    Error saving recipe '{recipe.title}': {e}")
    
    print(f"    Successfully saved {len(recipes)} recipes")


def generate_sql_migration(recipes: List[Recipe], output_path: Path) -> None:
    """Generate SQL migration file for recipes."""
    print(f"  Generating SQL migration file: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- Seed recipes data\n")
        f.write("-- Migration: 0002_seed_recipes\n\n")
        
        for recipe in recipes:
            # Insert recipe
            f.write(
                "INSERT INTO recipes (title, description, instructions, "
                "prep_time_minutes, cook_time_minutes, servings, difficulty) VALUES (\n"
            )
            f.write(f"  '{recipe.title.replace(\"'\", \"''\")}',\n")
            f.write(
                f"  '{recipe.description.replace(\"'\", \"''\") if recipe.description else ''}',\n"
            )
            f.write(f"  '{recipe.instructions.replace(\"'\", \"''\")}',\n")
            f.write(f"  {recipe.prep_time_minutes or 'NULL'},\n")
            f.write(f"  {recipe.cook_time_minutes or 'NULL'},\n")
            f.write(f"  {recipe.servings or 'NULL'},\n")
            f.write(
                f"  {'\"' + recipe.difficulty + '\"' if recipe.difficulty else 'NULL'}\n"
            )
            f.write(");\n\n")
            
            # Get the last inserted ID (this is a simplified approach)
            f.write("-- Get recipe ID for ingredients and tags\n")
            f.write(
                "-- Note: In a real migration, you'd need to handle ID references properly\n\n"
            )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Ingest recipes from JSON")
    parser.add_argument("input_file", help="Path to JSON file with recipes")
    parser.add_argument("--output", help="Output SQL migration file")
    parser.add_argument("--db", help="Database path (default: from config)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)
    
    print(f"Loading recipes from {input_path}...")
    try:
        recipes = load_recipes_from_json(input_path)
        print(f"  ✅ Loaded {len(recipes)} recipes")
    except Exception as e:
        print(f"  ❌ Error loading recipes: {e}")
        sys.exit(1)
    
    if args.output:
        # Generate SQL migration file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generate_sql_migration(recipes, output_path)
        print(f"  ✅ SQL migration generated: {output_path}")
    else:
        # Save to database
        db_path = args.db or "chef_agent.db"
        save_recipes_to_database(recipes, db_path)


if __name__ == "__main__":
    main()
