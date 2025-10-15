"""
Domain entities for the Chef Agent application.

These classes represent the core business concepts and contain only business
logic. They are independent of external technologies (database, API, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from .ingredient_categorizer import IngredientCategorizer


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format with timezone."""
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime object."""
    if not timestamp_str:
        return None

    try:
        # Try parsing ISO format with timezone
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        # Fallback to parsing without timezone info
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None


class DietType(Enum):
    """Diet types supported by the chef agent."""

    LOW_CARB = "low-carb"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HIGH_PROTEIN = "high-protein"
    KETO = "keto"
    MEDITERRANEAN = "mediterranean"
    GLUTEN_FREE = "gluten-free"
    PALEO = "paleo"


@dataclass
class Ingredient:
    """Represents an ingredient with quantity and unit."""

    name: str
    quantity: str
    unit: str
    allergens: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        allergen_info = (
            f" (allergens: {', '.join(self.allergens)})"
            if self.allergens
            else ""
        )
        return f"{self.quantity} {self.unit} {self.name}{allergen_info}"


@dataclass
class Recipe:
    """Represents a recipe with ingredients, instructions, and metadata."""

    id: Optional[int]
    title: str
    description: Optional[str] = None
    ingredients: List[Ingredient] = field(default_factory=list)
    instructions: str = ""
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    difficulty: Optional[str] = None  # "easy", "medium", "hard"
    diet_type: Optional[DietType] = None
    user_id: Optional[str] = None  # User who created this recipe
    allergens: List[str] = field(
        default_factory=list
    )  # Allergens in this recipe
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.ingredients is None:
            self.ingredients = []
        if self.tags is None:
            self.tags = []

        # Validate time values
        if self.prep_time_minutes is not None and self.prep_time_minutes < 0:
            raise ValueError("prep_time_minutes cannot be negative")
        if self.cook_time_minutes is not None and self.cook_time_minutes < 0:
            raise ValueError("cook_time_minutes cannot be negative")
        if self.servings is not None and self.servings <= 0:
            raise ValueError("servings must be positive")

        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")

        # Validate user_id
        if self.user_id is not None and (
            not self.user_id or not self.user_id.strip()
        ):
            raise ValueError("user_id cannot be empty")

        # Set timestamps if not provided
        if self.created_at is None:
            self.created_at = get_current_timestamp()
        if self.updated_at is None:
            self.updated_at = get_current_timestamp()

    def get_total_time_minutes(self) -> Optional[int]:
        """Calculate total time (prep + cook) in minutes.

        Returns:
            Optional[int]: Total time in minutes, or None if both times are None
        """
        if self.prep_time_minutes is None and self.cook_time_minutes is None:
            return None
        prep = self.prep_time_minutes or 0
        cook = self.cook_time_minutes or 0
        return prep + cook

    def has_tag(self, tag: str) -> bool:
        """Check if recipe has a specific tag."""
        return tag.lower() in [t.lower() for t in self.tags]

    def __str__(self) -> str:
        return f"Recipe: {self.title}"


@dataclass
class ShoppingItem:
    """Represents an item in the shopping list."""

    name: str
    quantity: str
    unit: str
    category: Optional[str] = None  # "produce", "dairy", "meat", etc.
    purchased: bool = False

    def __str__(self) -> str:
        status = "✓" if self.purchased else "○"
        return f"{status} {self.quantity} {self.unit} {self.name}"


class ShoppingList:
    """Represents a shopping list with items."""

    def __init__(
        self,
        items: List[ShoppingItem] = None,
        created_at: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.items = items if items is not None else []
        self.thread_id: Optional[str] = None  # Set by repository when loading
        self.created_at = created_at or get_current_timestamp()
        self.user_id = user_id

    def add_item(self, item: ShoppingItem) -> None:
        """Add an item to the shopping list."""
        self.items.append(item)

    def add_ingredients(
        self, ingredients: List[Ingredient], category: Optional[str] = None
    ) -> None:
        """Add multiple ingredients as shopping items with automatic
        categorization."""
        if not ingredients:
            return

        for ingredient in ingredients:
            # Use provided category or auto-detect if not provided
            detected_category = (
                category
                or IngredientCategorizer.categorize_ingredient(ingredient.name)
            )

            item = ShoppingItem(
                name=ingredient.name,
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                category=detected_category,
            )
            self.add_item(item)

    def get_unpurchased_items(self) -> List[ShoppingItem]:
        """Get all unpurchased items.

        Returns:
            List[ShoppingItem]: List of items that have not been purchased
        """
        return [item for item in self.items if not item.purchased]

    def get_items_by_category(self, category: str) -> List[ShoppingItem]:
        """Get items by category.

        Args:
            category: Category to filter by

        Returns:
            List[ShoppingItem]: List of items in the specified category
        """
        return [item for item in self.items if item.category == category]

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        """Return True if the shopping list exists (is not None)."""
        return True


@dataclass
class Meal:
    """Represents a single meal (breakfast, lunch, dinner)."""

    name: str  # "breakfast", "lunch", "dinner"
    recipe: Recipe
    notes: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.name.title()}: {self.recipe.title}"


@dataclass
class MenuDay:
    """Represents a day's menu with meals."""

    day_number: int
    meals: List[Meal] = None
    notes: Optional[str] = None
    total_calories: Optional[int] = None

    def __post_init__(self):
        if self.meals is None:
            self.meals = []

    def add_meal(self, meal: Meal) -> None:
        """Add a meal to the day's menu."""
        self.meals.append(meal)

    def get_meal_by_name(self, name: str) -> Optional[Meal]:
        """Get a meal by name (breakfast, lunch, dinner).

        Args:
            name: Name of the meal to find

        Returns:
            Optional[Meal]: The meal if found, None otherwise
        """
        for meal in self.meals:
            if meal.name.lower() == name.lower():
                return meal
        return None

    def get_all_ingredients(self) -> List[Ingredient]:
        """Get all ingredients from all meals in this day.

        Returns:
            List[Ingredient]: All ingredients from all meals
        """
        ingredients = []
        for meal in self.meals:
            ingredients.extend(meal.recipe.ingredients)
        return ingredients

    def __str__(self) -> str:
        return f"Day {self.day_number}: {len(self.meals)} meals"


@dataclass
class MealPlan:
    """Represents a complete meal plan for multiple days."""

    days: List[MenuDay] = None
    diet_type: Optional[DietType] = None
    total_days: int = 0
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.days is None:
            self.days = []
        self.total_days = len(self.days)

        # Set timestamp if not provided
        if self.created_at is None:
            self.created_at = get_current_timestamp()

    def add_day(self, day: MenuDay) -> None:
        """Add a day to the meal plan."""
        self.days.append(day)
        self.total_days = len(self.days)

    def get_all_ingredients(self) -> List[Ingredient]:
        """Get all ingredients from all days in the meal plan.

        Returns:
            List[Ingredient]: All ingredients from all meals in the meal plan
        """
        ingredients = []
        for day in self.days:
            ingredients.extend(day.get_all_ingredients())
        return ingredients

    def get_shopping_list(self) -> ShoppingList:
        """Generate a shopping list from all ingredients in the meal plan.

        Returns:
            ShoppingList: A shopping list containing all ingredients
        """
        shopping_list = ShoppingList()
        all_ingredients = self.get_all_ingredients()
        shopping_list.add_ingredients(all_ingredients)
        return shopping_list

    def __str__(self) -> str:
        diet_str = self.diet_type.value if self.diet_type else "any"
        return f"Meal Plan: {self.total_days} days, {diet_str} diet"
