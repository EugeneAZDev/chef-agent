"""
Tests for domain entities.
"""

from domain.entities import (
    DietType,
    Ingredient,
    Meal,
    MealPlan,
    MenuDay,
    Recipe,
    ShoppingItem,
    ShoppingList,
)


def test_ingredient_creation():
    """Test ingredient creation and string representation."""
    ingredient = Ingredient(name="flour", quantity="2", unit="cups")
    assert ingredient.name == "flour"
    assert ingredient.quantity == "2"
    assert ingredient.unit == "cups"
    assert str(ingredient) == "2 cups flour"


def test_recipe_creation():
    """Test recipe creation and methods."""
    ingredients = [
        Ingredient(name="flour", quantity="2", unit="cups"),
        Ingredient(name="eggs", quantity="2", unit="pieces"),
    ]

    recipe = Recipe(
        id=1,
        title="Pancakes",
        ingredients=ingredients,
        instructions="Mix and cook",
        prep_time_minutes=10,
        cook_time_minutes=15,
        tags=["breakfast", "easy"],
    )

    assert recipe.title == "Pancakes"
    assert len(recipe.ingredients) == 2
    assert recipe.get_total_time_minutes() == 25
    assert recipe.has_tag("breakfast")
    assert not recipe.has_tag("dinner")


def test_shopping_list_operations():
    """Test shopping list operations."""
    shopping_list = ShoppingList()

    item1 = ShoppingItem(name="milk", quantity="1", unit="liter")
    item2 = ShoppingItem(name="bread", quantity="2", unit="loaves")

    shopping_list.add_item(item1)
    shopping_list.add_item(item2)

    assert len(shopping_list) == 2
    assert len(shopping_list.get_unpurchased_items()) == 2

    item1.purchased = True
    assert len(shopping_list.get_unpurchased_items()) == 1


def test_meal_plan_creation():
    """Test meal plan creation and shopping list generation."""
    # Create a simple recipe
    ingredients = [
        Ingredient(name="flour", quantity="2", unit="cups"),
        Ingredient(name="eggs", quantity="2", unit="pieces"),
    ]

    recipe = Recipe(
        id=1, title="Pancakes", ingredients=ingredients, instructions="Mix and cook"
    )

    # Create a meal
    meal = Meal(name="breakfast", recipe=recipe)

    # Create a menu day
    menu_day = MenuDay(day_number=1)
    menu_day.add_meal(meal)

    # Create a meal plan
    meal_plan = MealPlan(diet_type=DietType.LOW_CARB)
    meal_plan.add_day(menu_day)

    assert meal_plan.total_days == 1
    assert len(meal_plan.get_all_ingredients()) == 2

    # Test shopping list generation
    shopping_list = meal_plan.get_shopping_list()
    assert len(shopping_list.items) == 2
    assert shopping_list.items[0].name == "flour"
    assert shopping_list.items[1].name == "eggs"


def test_diet_type_enum():
    """Test diet type enum values."""
    assert DietType.LOW_CARB.value == "low-carb"
    assert DietType.VEGETARIAN.value == "vegetarian"
    assert DietType.VEGAN.value == "vegan"
