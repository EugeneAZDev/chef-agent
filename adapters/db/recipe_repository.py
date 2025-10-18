"""
SQLite implementation of RecipeRepository.
"""

import gzip
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

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user_id format and content."""
        if not isinstance(user_id, str):
            raise ValueError("user_id must be a string")

        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        # Check if it's an email address
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(email_pattern, user_id):
            return  # Valid email

        # Check if it's a valid alphanumeric ID with dashes/underscores
        if not user_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "user_id must be a valid email address or alphanumeric "
                "string with dashes/underscores only"
            )

    def get_by_id(
        self, recipe_id: int, include_ingredients: bool = True
    ) -> Optional[Recipe]:
        """Get a recipe by its ID."""
        if include_ingredients:
            query = """
                SELECT r.*, ri.ingredients
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                WHERE r.id = ?
            """
        else:
            query = """
                SELECT r.*, NULL as ingredients
                FROM recipes r
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
            # Escape SQL wildcards to prevent injection
            escaped_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
            conditions.append("(r.title LIKE ? OR r.description LIKE ?)")
            params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])

        where_clause = " OR ".join(conditions)
        query = (
            """
            SELECT r.*, ri.ingredients
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            WHERE """
            + where_clause
            + """
            LIMIT ?
        """
        )
        params.append(limit)

        rows = self.db.execute_query(query, params)
        return [self._row_to_recipe(row) for row in rows]

    def get_all(
        self, limit: int = 100, offset: int = 0, user_id: str = None
    ) -> List[Recipe]:
        """Get all recipes with a limit, optionally filtered by user."""
        if user_id:
            self._validate_user_id(user_id)
            query = """
                SELECT r.*, ri.ingredients
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                WHERE r.user_id = ?
                ORDER BY r.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self.db.execute_query(query, (user_id, limit, offset))
        else:
            query = """
                SELECT r.*, ri.ingredients
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                ORDER BY r.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self.db.execute_query(query, (limit, offset))
        return [self._row_to_recipe(row) for row in rows]

    def get_all_with_tags(
        self, limit: int = 100, offset: int = 0, user_id: str = None
    ) -> List[Recipe]:
        """Get all recipes with a limit, optionally filtered by user,
        with optimized tag loading."""
        if user_id:
            self._validate_user_id(user_id)
            query = """
                SELECT r.*, ri.ingredients, GROUP_CONCAT(t.name) as tags
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                LEFT JOIN recipe_tags rt ON r.id = rt.recipe_id
                LEFT JOIN tags t ON rt.tag_id = t.id
                WHERE r.user_id = ?
                GROUP BY r.id, ri.ingredients
                ORDER BY r.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self.db.execute_query(query, (user_id, limit, offset))
        else:
            query = """
                SELECT r.*, ri.ingredients, GROUP_CONCAT(t.name) as tags
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                LEFT JOIN recipe_tags rt ON r.id = rt.recipe_id
                LEFT JOIN tags t ON rt.tag_id = t.id
                GROUP BY r.id, ri.ingredients
                ORDER BY r.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self.db.execute_query(query, (limit, offset))
        return [self._row_to_recipe_with_tags(row) for row in rows]

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
        with self._lock:  # Ensure thread safety
            try:
                self.db.begin_transaction()

                # Check if recipe exists to prevent race conditions
                lock_query = """
                    SELECT id FROM recipes WHERE id = ?
                """
                locked_rows = self.db.execute_query(lock_query, (recipe_id,))
                if not locked_rows:
                    self.db.rollback_transaction()
                    return False

                # Delete from recipe_tags first (due to foreign key
                # constraints)
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
        servings: int = None,
        limit: int = 10,
        user_id: str = None,
    ) -> List[Recipe]:
        """Search recipes with various filters."""
        conditions = []
        params = []

        # Base query
        base_query = """
            SELECT r.*, ri.ingredients
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
        """

        # Add user filter
        if user_id:
            self._validate_user_id(user_id)
            conditions.append("r.user_id = ?")
            params.append(user_id)

        # Add text search filter
        if query:
            conditions.append(
                "(r.title LIKE ? OR r.description LIKE ? OR "
                "r.instructions LIKE ?)"
            )
            # Escape SQL wildcards to prevent injection
            escaped_query = query.replace("%", "\\%").replace("_", "\\_")
            search_term = f"%{escaped_query}%"
            params.extend([search_term, search_term, search_term])

        # Add diet type filter
        if diet_type:
            conditions.append("r.diet_type = ?")
            # Validate diet_type and convert to string value
            if isinstance(diet_type, str):
                diet_enum = next(
                    (dt for dt in DietType if dt.value == diet_type), None
                )
                if diet_enum is None:
                    # Invalid diet_type - raise error instead of silent failure
                    raise ValueError(
                        f"Invalid diet_type '{diet_type}'. "
                        f"Must be one of: {[dt.value for dt in DietType]}"
                    )
                params.append(diet_enum.value)
            elif isinstance(diet_type, DietType):
                # Already a DietType enum, use its value
                params.append(diet_type.value)
            else:
                # Invalid type
                raise ValueError(
                    f"Invalid diet_type type '{type(diet_type)}'. "
                    f"Must be string or DietType enum."
                )

        # Add difficulty filter
        if difficulty:
            conditions.append("r.difficulty = ?")
            params.append(difficulty)

        # Add prep time filter
        if max_prep_time:
            conditions.append("r.prep_time_minutes <= ?")
            params.append(max_prep_time)

        # Add servings filter - use approximate matching instead of >=
        if servings:
            # Allow recipes with servings within 25% of requested amount
            min_servings = max(1, int(servings * 0.75))
            max_servings = int(servings * 1.25)
            conditions.append("r.servings BETWEEN ? AND ?")
            params.extend([min_servings, max_servings])

        # Build final query safely
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            final_query = (
                base_query
                + where_clause
                + " ORDER BY r.created_at DESC LIMIT ?"
            )
        else:
            final_query = base_query + " ORDER BY r.created_at DESC LIMIT ?"

        params.append(limit)

        rows = self.db.execute_query(final_query, params)
        return [self._row_to_recipe(row) for row in rows]

    def _create_recipe(self, recipe: Recipe) -> Recipe:
        """Create a new recipe atomically with proper locking."""
        # Use INSERT OR IGNORE to handle race conditions atomically
        query = """
            INSERT OR IGNORE INTO recipes (
                title, description, instructions, prep_time_minutes,
                cook_time_minutes, servings, difficulty, diet_type, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            recipe_id = self.db.execute_insert_in_transaction(
                query,
                (
                    recipe.title,
                    recipe.description,
                    recipe.instructions,
                    recipe.prep_time_minutes,
                    recipe.cook_time_minutes,
                    recipe.servings,
                    recipe.difficulty,
                    recipe.diet_type.value if recipe.diet_type else None,
                    recipe.user_id,
                ),
            )

            # If recipe_id is None or 0, it means the insert was ignored due to
            # unique constraint - recipe already exists
            if recipe_id is None or recipe_id == 0:
                raise ValueError(
                    f"Recipe with title '{recipe.title}' already exists "
                    f"for this user"
                )
            # Check for integer overflow (SQLite max is 2^63-1)
            elif recipe_id > 2**63 - 1:
                raise ValueError("Recipe ID overflow - database limit reached")

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(
                    f"Recipe with title '{recipe.title}' already exists "
                    f"for this user"
                )
            else:
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
        # Update recipe atomically - check affected rows to detect if recipe
        # exists
        # CRITICAL: Include user_id in WHERE clause to prevent cross-user
        # updates
        query = """
            UPDATE recipes
            SET title = ?, description = ?, instructions = ?,
                prep_time_minutes = ?, cook_time_minutes = ?,
                servings = ?, difficulty = ?, diet_type = ?, user_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """
        affected_rows = self.db.execute_update_in_transaction(
            query,
            (
                recipe.title,
                recipe.description,
                recipe.instructions,
                recipe.prep_time_minutes,
                recipe.cook_time_minutes,
                recipe.servings,
                recipe.difficulty,
                recipe.diet_type.value if recipe.diet_type else None,
                recipe.user_id,
                recipe.id,
                recipe.user_id,  # Additional user_id check in WHERE clause
            ),
        )

        # If no rows were affected, the recipe doesn't exist
        if affected_rows == 0:
            raise ValueError(f"Recipe with id {recipe.id} not found")

        # Update ingredients
        self.db.execute_update_in_transaction(
            "DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe.id,)
        )
        self._save_ingredients(recipe.id, recipe.ingredients)

        # Update tags
        self.db.execute_update_in_transaction(
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

            # Compress if JSON is larger than 1KB
            if len(ingredients_json) > 1024:
                compressed = gzip.compress(ingredients_json.encode("utf-8"))
                ingredients_json = f"COMPRESSED:{compressed.hex()}"
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize ingredients: {e}")

        self.db.execute_insert_in_transaction(
            "INSERT INTO recipe_ingredients (recipe_id, ingredients) "
            "VALUES (?, ?)",
            (recipe_id, ingredients_json),
        )

    def _save_tags(self, recipe_id: int, tags: List[str]) -> None:
        """Save tags for a recipe."""
        if not tags:
            return

        for tag_name in tags:
            # Use atomic INSERT OR IGNORE with immediate SELECT to get tag_id
            # This prevents race conditions between threads
            self.db.execute_insert_in_transaction(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag_name,),
            )

            # Get tag ID atomically - this will always work since we just
            # inserted the tag or it already existed
            rows = self.db.execute_query(
                "SELECT id FROM tags WHERE name = ?", (tag_name,)
            )
            if rows:
                tag_id = rows[0]["id"]
            else:
                # This should not happen, but handle gracefully
                continue

            # Link recipe to tag
            self.db.execute_insert_in_transaction(
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
                ingredients_json = (
                    row["ingredients"] if row["ingredients"] else "[]"
                )

                # Check if compressed - ensure ingredients_json is not None
                if ingredients_json and ingredients_json.startswith(
                    "COMPRESSED:"
                ):
                    compressed_hex = ingredients_json[
                        11:
                    ]  # Remove "COMPRESSED:" prefix
                    try:
                        compressed_bytes = bytes.fromhex(compressed_hex)
                        ingredients_json = gzip.decompress(
                            compressed_bytes
                        ).decode("utf-8")
                    except (ValueError, gzip.BadGzipFile, UnicodeDecodeError):
                        # If decompression fails, treat as empty ingredients
                        ingredients_json = "[]"

                ingredients_data = json.loads(ingredients_json)
                ingredients = [
                    Ingredient(
                        name=ing["name"],
                        quantity=ing["quantity"],
                        unit=ing["unit"],
                        allergens=ing.get("allergens", []),
                    )
                    for ing in ingredients_data
                ]
            except (
                json.JSONDecodeError,
                KeyError,
                gzip.BadGzipFile,
                ValueError,
                UnicodeDecodeError,
            ):
                ingredients = []

        # Get tags for this recipe
        tags = self._get_recipe_tags(row["id"])

        # Safely parse diet_type - handle invalid values gracefully
        try:
            parsed_diet_type = self._parse_diet_type(row["diet_type"])
        except ValueError:
            # Log warning and use None as default for invalid diet_type
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Invalid diet_type '%s' in database for recipe %s. "
                "Using None as default.",
                row["diet_type"],
                row["id"],
            )
            parsed_diet_type = None

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
            diet_type=parsed_diet_type,
            user_id=row["user_id"],
        )

    def _parse_diet_type(self, diet_type_str: str) -> Optional[DietType]:
        """Parse diet_type string from database to DietType enum.

        Args:
            diet_type_str: String value from database

        Returns:
            DietType enum if valid, None if invalid or empty

        Raises:
            ValueError: If diet_type_str is not None/empty but doesn't match
                any enum value
        """
        if (
            not diet_type_str
            or diet_type_str.strip() == ""
            or diet_type_str == "None"
        ):
            return None

        # Try to find matching enum value
        diet_enum = next(
            (dt for dt in DietType if dt.value == diet_type_str), None
        )

        if diet_enum is None:
            # Invalid diet_type in database - raise ValueError for validation
            diet_values = [dt.value for dt in DietType]
            raise ValueError(
                f"Invalid diet_type '{diet_type_str}' in database. "
                f"Must be one of: {diet_values}"
            )

        return diet_enum

    def _row_to_recipe_with_tags(self, row) -> Recipe:
        """Convert database row to Recipe entity with pre-loaded tags."""
        # Parse ingredients from JSON
        ingredients = []
        if row["ingredients"]:
            try:
                ingredients_json = (
                    row["ingredients"] if row["ingredients"] else "[]"
                )

                # Check if compressed - ensure ingredients_json is not None
                if ingredients_json and ingredients_json.startswith(
                    "COMPRESSED:"
                ):
                    compressed_hex = ingredients_json[
                        11:
                    ]  # Remove "COMPRESSED:" prefix
                    try:
                        compressed_bytes = bytes.fromhex(compressed_hex)
                        ingredients_json = gzip.decompress(
                            compressed_bytes
                        ).decode("utf-8")
                    except (ValueError, gzip.BadGzipFile, UnicodeDecodeError):
                        # If decompression fails, treat as empty ingredients
                        ingredients_json = "[]"

                ingredients_data = json.loads(ingredients_json)
                ingredients = [
                    Ingredient(
                        name=ing["name"],
                        quantity=ing["quantity"],
                        unit=ing["unit"],
                        allergens=ing.get("allergens", []),
                    )
                    for ing in ingredients_data
                ]
            except (
                json.JSONDecodeError,
                KeyError,
                gzip.BadGzipFile,
                ValueError,
                UnicodeDecodeError,
            ):
                ingredients = []

        # Parse tags from GROUP_CONCAT result
        tags = []
        if row.get("tags"):
            tags = [
                tag.strip() for tag in row["tags"].split(",") if tag.strip()
            ]

        # Safely parse diet_type - handle invalid values gracefully
        try:
            parsed_diet_type = self._parse_diet_type(row["diet_type"])
        except ValueError:
            # Log warning and use None as default for invalid diet_type
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Invalid diet_type '%s' in database for recipe %s. "
                "Using None as default.",
                row["diet_type"],
                row["id"],
            )
            parsed_diet_type = None

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
            diet_type=parsed_diet_type,
            user_id=row["user_id"],
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
