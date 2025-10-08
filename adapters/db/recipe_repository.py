"""
SQLite implementation of RecipeRepository.
"""

import json
import sqlite3
import threading
from typing import List, Optional

from domain.entities import DietType, Ingredient, Recipe
from domain.repo_abc import RecipeRepository

from .database import Database


class SQLiteRecipeRepository(RecipeRepository):
    """SQLite implementation of RecipeRepository."""

    def __init__(self, db: Database):
        self.db = db
        self._lock = threading.RLock()  # Reentrant lock for thread safety

    def get_by_id(self, recipe_id: int) -> Optional[Recipe]:
        """Get a recipe by its ID."""
        query = """
            SELECT r.*, ri.ingredients
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            WHERE r.id = ?
        """
        rows = self.db.execute_query(query, (recipe_id,))

        if not rows:
            return None

        row = rows[0]
        return self._row_to_recipe(row)

    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Recipe]:
        """Search recipes by tags."""
        if not tags:
            return []

        placeholders = ",".join("?" * len(tags))
        query = f"""
            SELECT DISTINCT r.*, ri.ingredients
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            INNER JOIN recipe_tags rt ON r.id = rt.recipe_id
            INNER JOIN tags t ON rt.tag_id = t.id
            WHERE t.name IN ({placeholders})
            LIMIT ?
        """
        params = tags + [limit]
        rows = self.db.execute_query(query, params)

        return [self._row_to_recipe(row) for row in rows]

    def search_by_diet_type(
        self, diet_type: DietType, limit: int = 10
    ) -> List[Recipe]:
        """Search recipes by diet type."""
        return self.search_by_tags([diet_type.value], limit)

    def search_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Recipe]:
        """Search recipes by keywords in title or description."""
        if not keywords:
            return []

        # Create search conditions for each keyword
        conditions = []
        params = []

        for keyword in keywords:
            conditions.append("(r.title LIKE ? OR r.description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " OR ".join(conditions)
        query = f"""
            SELECT r.*, ri.ingredients
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            WHERE {where_clause}
            LIMIT ?
        """
        params.append(limit)

        rows = self.db.execute_query(query, params)
        return [self._row_to_recipe(row) for row in rows]

    def get_all(self, limit: int = 100, user_id: str = None) -> List[Recipe]:
        """Get all recipes with a limit, optionally filtered by user."""
        if user_id:
            query = """
                SELECT r.*, ri.ingredients
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                WHERE r.user_id = ?
                ORDER BY r.created_at DESC
                LIMIT ?
            """
            rows = self.db.execute_query(query, (user_id, limit))
        else:
            query = """
                SELECT r.*, ri.ingredients
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                ORDER BY r.created_at DESC
                LIMIT ?
            """
            rows = self.db.execute_query(query, (limit,))
        return [self._row_to_recipe(row) for row in rows]

    def save(self, recipe: Recipe) -> Recipe:
        """Save a recipe (create or update) with thread safety."""
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()
                if recipe.id is None:
                    result = self._create_recipe(recipe)
                else:
                    result = self._update_recipe(recipe)
                self.db.commit_transaction()
                return result
            except sqlite3.IntegrityError as e:
                self.db.rollback_transaction()
                if "UNIQUE constraint failed" in str(e):
                    raise ValueError(
                        f"Recipe with title '{recipe.title}' already exists "
                        f"for this user"
                    )
                raise
            except Exception as e:
                self.db.rollback_transaction()
                raise e

    def delete(self, recipe_id: int) -> bool:
        """Delete a recipe by ID."""
        try:
            self.db.begin_transaction()
            # Delete from recipe_tags first (due to foreign key constraints)
            self.db.execute_update(
                "DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe_id,)
            )

            # Delete ingredients
            self.db.execute_update(
                "DELETE FROM recipe_ingredients WHERE recipe_id = ?",
                (recipe_id,),
            )

            # Delete recipe
            affected_rows = self.db.execute_update(
                "DELETE FROM recipes WHERE id = ?", (recipe_id,)
            )
            self.db.commit_transaction()
            return affected_rows > 0
        except Exception as e:
            self.db.rollback_transaction()
            raise e

    def search_recipes(
        self,
        query: str = None,
        diet_type: str = None,
        difficulty: str = None,
        max_prep_time: int = None,
        limit: int = 10,
        user_id: str = None,
    ) -> List[Recipe]:
        """Search recipes with various filters."""
        # For now, implement a simple search that returns all recipes
        # This can be enhanced later with proper search logic
        return self.get_all(limit, user_id)

    def _create_recipe(self, recipe: Recipe) -> Recipe:
        """Create a new recipe atomically with proper locking."""
        # Check for existing recipe to prevent race conditions
        existing_query = """
            SELECT id FROM recipes
            WHERE title = ? AND user_id = ?
        """
        existing = self.db.execute_query(
            existing_query, (recipe.title, recipe.user_id)
        )
        if existing:
            raise ValueError(
                f"Recipe with title '{recipe.title}' already exists "
                f"for this user"
            )

        # Insert new recipe
        query = """
            INSERT INTO recipes (
                title, description, instructions, prep_time_minutes,
                cook_time_minutes, servings, difficulty, diet_type, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            recipe_id = self.db.execute_insert(
                query,
                (
                    recipe.title,
                    recipe.description,
                    recipe.instructions,
                    recipe.prep_time_minutes,
                    recipe.cook_time_minutes,
                    recipe.servings,
                    recipe.difficulty,
                    recipe.diet_type,
                    recipe.user_id,
                ),
            )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(
                    f"Recipe with title '{recipe.title}' already exists "
                    f"for this user"
                )
            raise

        # Insert ingredients
        self._save_ingredients(recipe_id, recipe.ingredients)

        # Insert tags
        self._save_tags(recipe_id, recipe.tags)

        # Return updated recipe with ID
        recipe.id = recipe_id
        return recipe

    def _update_recipe(self, recipe: Recipe) -> Recipe:
        """Update an existing recipe."""
        # Update recipe
        query = """
            UPDATE recipes
            SET title = ?, description = ?, instructions = ?,
                prep_time_minutes = ?, cook_time_minutes = ?,
                servings = ?, difficulty = ?, diet_type = ?, user_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        self.db.execute_update(
            query,
            (
                recipe.title,
                recipe.description,
                recipe.instructions,
                recipe.prep_time_minutes,
                recipe.cook_time_minutes,
                recipe.servings,
                recipe.difficulty,
                recipe.diet_type,
                recipe.user_id,
                recipe.id,
            ),
        )

        # Update ingredients
        self.db.execute_update(
            "DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe.id,)
        )
        self._save_ingredients(recipe.id, recipe.ingredients)

        # Update tags
        self.db.execute_update(
            "DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe.id,)
        )
        self._save_tags(recipe.id, recipe.tags)

        return recipe

    def _save_ingredients(
        self, recipe_id: int, ingredients: List[Ingredient]
    ) -> None:
        """Save ingredients for a recipe."""
        if not ingredients:
            return

        ingredients_data = [
            {
                "name": ing.name,
                "quantity": ing.quantity,
                "unit": ing.unit,
            }
            for ing in ingredients
        ]

        try:
            ingredients_json = json.dumps(ingredients_data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize ingredients: {e}")

        self.db.execute_insert(
            "INSERT INTO recipe_ingredients (recipe_id, ingredients) "
            "VALUES (?, ?)",
            (recipe_id, ingredients_json),
        )

    def _save_tags(self, recipe_id: int, tags: List[str]) -> None:
        """Save tags for a recipe."""
        if not tags:
            return

        for tag_name in tags:
            # Insert tag if it doesn't exist
            tag_id = self.db.execute_insert(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag_name,),
            )

            # Get tag ID
            if tag_id == 0:
                rows = self.db.execute_query(
                    "SELECT id FROM tags WHERE name = ?", (tag_name,)
                )
                tag_id = rows[0]["id"]

            # Link recipe to tag
            self.db.execute_insert(
                "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) "
                "VALUES (?, ?)",
                (recipe_id, tag_id),
            )

    def _row_to_recipe(self, row) -> Recipe:
        """Convert database row to Recipe entity."""
        # Parse ingredients from JSON
        ingredients = []
        if row["ingredients"]:
            try:
                ingredients_data = json.loads(row["ingredients"] or "[]")
                ingredients = [
                    Ingredient(
                        name=ing["name"],
                        quantity=ing["quantity"],
                        unit=ing["unit"],
                    )
                    for ing in ingredients_data
                ]
            except (json.JSONDecodeError, KeyError):
                ingredients = []

        # Get tags for this recipe
        tags = self._get_recipe_tags(row["id"])

        return Recipe(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            ingredients=ingredients,
            instructions=row["instructions"],
            prep_time_minutes=row["prep_time_minutes"],
            cook_time_minutes=row["cook_time_minutes"],
            servings=row["servings"],
            tags=tags,
            difficulty=row["difficulty"],
            diet_type=row["diet_type"] if "diet_type" in row else None,
            user_id=row["user_id"] if "user_id" in row else None,
        )

    def _get_recipe_tags(self, recipe_id: int) -> List[str]:
        """Get tags for a recipe."""
        query = """
            SELECT t.name
            FROM tags t
            INNER JOIN recipe_tags rt ON t.id = rt.tag_id
            WHERE rt.recipe_id = ?
        """
        rows = self.db.execute_query(query, (recipe_id,))
        return [row["name"] for row in rows]
