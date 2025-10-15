"""
Abstract repository interfaces for the Chef Agent domain.

These interfaces define the contract for data access without specifying
the implementation details (database, file system, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import DietType, Recipe, ShoppingItem, ShoppingList


class RecipeRepository(ABC):
    """Abstract repository for recipe data access."""

    @abstractmethod
    def get_by_id(self, recipe_id: int) -> Optional[Recipe]:
        """Get a recipe by its ID."""
        pass

    @abstractmethod
    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[Recipe]:
        """Search recipes by tags."""
        pass

    @abstractmethod
    def search_by_diet_type(
        self, diet_type: DietType, limit: int = 10
    ) -> List[Recipe]:
        """Search recipes by diet type."""
        pass

    @abstractmethod
    def search_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Recipe]:
        """Search recipes by keywords in title or description."""
        pass

    @abstractmethod
    def get_all(self, limit: int = 100) -> List[Recipe]:
        """Get all recipes with a limit."""
        pass

    @abstractmethod
    def save(self, recipe: Recipe) -> Recipe:
        """Save a recipe (create or update)."""
        pass

    @abstractmethod
    def delete(self, recipe_id: int) -> bool:
        """Delete a recipe by ID."""
        pass


class ShoppingListRepository(ABC):
    """Abstract repository for shopping list data access."""

    @abstractmethod
    def get_by_id(self, list_id: int) -> Optional[ShoppingList]:
        """Get a shopping list by its ID."""
        pass

    @abstractmethod
    def get_by_thread_id(
        self, thread_id: str, user_id: str = None
    ) -> Optional[ShoppingList]:
        """Get a shopping list by conversation thread ID and optionally user
        ID."""
        pass

    @abstractmethod
    def save(
        self, shopping_list: ShoppingList, thread_id: str
    ) -> ShoppingList:
        """Save a shopping list for a specific thread."""
        pass

    @abstractmethod
    def add_items(self, thread_id: str, items: List[ShoppingItem]) -> None:
        """Add items to an existing shopping list."""
        pass

    @abstractmethod
    def clear(self, thread_id: str) -> None:
        """Clear all items from a shopping list."""
        pass

    @abstractmethod
    def delete(self, list_id: int) -> bool:
        """Delete a shopping list by ID."""
        pass
