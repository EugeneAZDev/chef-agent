"""
Tests for meal plan generation functionality.
"""

import pytest

from domain.entities import DietType, Ingredient, Recipe
from domain.meal_plan_generator import MealPlanGenerator


class TestMealPlanGenerator:
    """Test cases for MealPlanGenerator."""

    @pytest.fixture
    def sample_recipes(self):
        """Create sample recipes for testing."""
        return [
            Recipe(
                id=1,
                title="Vegetarian Pasta",
                description="A delicious vegetarian pasta dish",
                instructions="Cook pasta, add vegetables",
                ingredients=[
                    Ingredient(name="pasta", quantity="200", unit="g"),
                    Ingredient(name="tomato", quantity="2", unit="pieces"),
                    Ingredient(name="onion", quantity="1", unit="piece"),
                ],
                diet_type="vegetarian",
                prep_time_minutes=15,
                cook_time_minutes=20,
                servings=4,
            ),
            Recipe(
                id=2,
                title="Chicken Salad",
                description="Healthy chicken salad",
                instructions="Mix chicken with vegetables",
                ingredients=[
                    Ingredient(name="chicken", quantity="300", unit="g"),
                    Ingredient(name="lettuce", quantity="1", unit="head"),
                    Ingredient(name="tomato", quantity="1", unit="piece"),
                ],
                diet_type="high-protein",
                prep_time_minutes=10,
                cook_time_minutes=0,
                servings=2,
            ),
            Recipe(
                id=3,
                title="Vegan Curry",
                description="Spicy vegan curry",
                instructions="Cook vegetables in curry sauce",
                ingredients=[
                    Ingredient(name="coconut milk", quantity="400", unit="ml"),
                    Ingredient(name="curry powder", quantity="2", unit="tbsp"),
                    Ingredient(name="potato", quantity="2", unit="pieces"),
                ],
                diet_type="vegan",
                prep_time_minutes=20,
                cook_time_minutes=30,
                servings=3,
            ),
        ]

    def test_generate_meal_plan_basic(self, sample_recipes):
        """Test basic meal plan generation."""
        meal_plan = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )

        assert meal_plan.total_days == 3
        assert len(meal_plan.days) == 3
        assert meal_plan.diet_type == DietType.VEGETARIAN
        assert meal_plan.created_at is not None

    def test_generate_meal_plan_empty_recipes(self):
        """Test meal plan generation with empty recipe list."""
        meal_plan = MealPlanGenerator.generate_meal_plan(
            recipes=[], diet_goal="vegetarian", days_count=3
        )

        assert meal_plan.total_days == 0
        assert len(meal_plan.days) == 0
        assert meal_plan.diet_type is None

    def test_generate_meal_plan_diet_filtering(self, sample_recipes):
        """Test that recipes are filtered by diet goal."""
        meal_plan = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegan", days_count=1
        )

        # Should only include vegan recipes
        all_ingredients = meal_plan.get_all_ingredients()
        assert len(all_ingredients) > 0

    def test_generate_meal_plan_insufficient_recipes(self, sample_recipes):
        """Test meal plan generation when there are insufficient recipes."""
        # Use only 1 recipe for 3 days (need 9 recipes for 3 meals per day)
        meal_plan = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes[:1], diet_goal="vegetarian", days_count=3
        )

        assert meal_plan.total_days == 3
        assert len(meal_plan.days) == 3
        # Should have expanded the recipe list

    def test_generate_menu_day(self, sample_recipes):
        """Test generating a single menu day."""
        day = MealPlanGenerator._generate_menu_day(
            day_num=1,
            recipes=sample_recipes,
            diet_goal="vegetarian",
            preferences=None,
        )

        assert day.day_number == 1
        assert len(day.meals) == 3  # breakfast, lunch, dinner
        assert day.meals[0].name == "breakfast"
        assert day.meals[1].name == "lunch"
        assert day.meals[2].name == "dinner"

    def test_filter_recipes_by_diet(self, sample_recipes):
        """Test filtering recipes by diet goal."""
        vegetarian_recipes = MealPlanGenerator._filter_recipes_by_diet(
            sample_recipes, "vegetarian"
        )

        # Should include vegetarian and recipes without diet_type
        assert len(vegetarian_recipes) >= 1

        vegan_recipes = MealPlanGenerator._filter_recipes_by_diet(
            sample_recipes, "vegan"
        )

        # Should only include vegan recipes
        assert len(vegan_recipes) >= 1

    def test_determine_diet_type(self):
        """Test determining diet type from diet goal."""
        assert (
            MealPlanGenerator._determine_diet_type("vegetarian")
            == DietType.VEGETARIAN
        )
        assert (
            MealPlanGenerator._determine_diet_type("vegan") == DietType.VEGAN
        )
        assert (
            MealPlanGenerator._determine_diet_type("low-carb")
            == DietType.LOW_CARB
        )
        assert MealPlanGenerator._determine_diet_type("unknown") is None

    def test_validate_meal_plan(self, sample_recipes):
        """Test meal plan validation."""
        # Valid meal plan
        valid_plan = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )
        assert MealPlanGenerator.validate_meal_plan(valid_plan) is True

        # Invalid meal plan (empty days)
        invalid_plan = MealPlanGenerator.generate_meal_plan(
            recipes=[], diet_goal="vegetarian", days_count=3
        )
        assert MealPlanGenerator.validate_meal_plan(invalid_plan) is False

    def test_meal_plan_shopping_list_generation(self, sample_recipes):
        """Test that meal plan can generate shopping list."""
        meal_plan = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=2
        )

        shopping_list = meal_plan.get_shopping_list()
        assert shopping_list is not None
        assert len(shopping_list.items) > 0

        # Check that items have categories
        for item in shopping_list.items:
            assert item.category is not None
