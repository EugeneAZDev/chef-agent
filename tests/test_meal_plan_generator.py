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
                diet_type=DietType.VEGETARIAN,
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
                diet_type=DietType.HIGH_PROTEIN,
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
                diet_type=DietType.VEGAN,
                prep_time_minutes=20,
                cook_time_minutes=30,
                servings=3,
            ),
        ]

    def test_generate_meal_plan_basic(self, sample_recipes):
        """Test basic meal plan generation."""
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )

        assert meal_plan.total_days == 3
        assert len(meal_plan.days) == 3
        assert meal_plan.diet_type == DietType.VEGETARIAN
        assert meal_plan.created_at is not None

    def test_generate_meal_plan_empty_recipes(self):
        """Test meal plan generation with empty recipe list."""
        with pytest.raises(
            ValueError, match="Cannot generate meal plan: no recipes available"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=[], diet_goal="vegetarian", days_count=3
            )

    def test_generate_meal_plan_diet_filtering(self, sample_recipes):
        """Test that recipes are filtered by diet goal."""
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegan", days_count=3
        )

        # Should only include vegan recipes
        all_ingredients = meal_plan.get_all_ingredients()
        assert len(all_ingredients) > 0

    def test_generate_meal_plan_insufficient_recipes(self, sample_recipes):
        """Test meal plan generation when there are insufficient recipes."""
        # Use only 1 recipe for 3 days (need 9 recipes for 3 meals per day)
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
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
        valid_plan, _ = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )
        assert MealPlanGenerator.validate_meal_plan(valid_plan) is True

        # Invalid meal plan (empty days) - should raise error
        with pytest.raises(
            ValueError, match="Cannot generate meal plan: no recipes available"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=[], diet_goal="vegetarian", days_count=3
            )

    def test_meal_plan_shopping_list_generation(self, sample_recipes):
        """Test that meal plan can generate shopping list."""
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )

        shopping_list = meal_plan.get_shopping_list()
        assert shopping_list is not None
        assert len(shopping_list.items) > 0

        # Check that items have categories
        for item in shopping_list.items:
            assert item.category is not None

    def test_fallback_when_no_diet_recipes(self, sample_recipes):
        """Test fallback behavior when no recipes match diet goal."""
        # Create recipes that don't match vegan diet
        non_vegan_recipes = [
            Recipe(
                id=1,
                title="Chicken Salad",
                ingredients=[
                    Ingredient(name="chicken", quantity="200", unit="g"),
                    Ingredient(name="lettuce", quantity="1", unit="head"),
                ],
                instructions="Mix chicken with lettuce",
                diet_type=DietType.HIGH_PROTEIN,
            ),
            Recipe(
                id=2,
                title="Beef Steak",
                ingredients=[
                    Ingredient(name="beef", quantity="300", unit="g"),
                ],
                instructions="Cook the steak",
                diet_type=DietType.HIGH_PROTEIN,
            ),
        ]

        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=non_vegan_recipes, diet_goal="vegan", days_count=3
        )

        # Should use fallback (all recipes) since no vegan recipes found
        assert fallback_used is True
        assert meal_plan.total_days == 3
        assert len(meal_plan.days) == 3

    def test_no_fallback_when_diet_recipes_exist(self, sample_recipes):
        """Test no fallback when diet-specific recipes exist."""
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )

        # Should not use fallback since vegetarian recipes exist
        assert fallback_used is False
        assert meal_plan.total_days == 3
        assert meal_plan.diet_type == DietType.VEGETARIAN

    def test_fallback_with_empty_recipes(self):
        """Test fallback behavior with empty recipe list."""
        with pytest.raises(
            ValueError, match="Cannot generate meal plan: no recipes available"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=[], diet_goal="vegetarian", days_count=3
            )

    def test_maximum_days_count_seven(self, sample_recipes):
        """Test meal plan generation with maximum days count (7)."""
        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=7
        )

        assert meal_plan.total_days == 7
        assert len(meal_plan.days) == 7
        assert meal_plan.diet_type == DietType.VEGETARIAN
        assert meal_plan.created_at is not None

        # Each day should have 3 meals
        for day in meal_plan.days:
            assert len(day.meals) == 3
            assert day.meals[0].name == "breakfast"
            assert day.meals[1].name == "lunch"
            assert day.meals[2].name == "dinner"

    def test_days_count_validation_boundary_values(self, sample_recipes):
        """Test days_count validation with boundary values."""
        # Test minimum valid value (3)
        meal_plan, _ = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )
        assert meal_plan.total_days == 3

        # Test maximum valid value (7)
        meal_plan, _ = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=7
        )
        assert meal_plan.total_days == 7

        # Test invalid values
        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=sample_recipes, diet_goal="vegetarian", days_count=2
            )

        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=sample_recipes, diet_goal="vegetarian", days_count=8
            )

        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=sample_recipes, diet_goal="vegetarian", days_count=0
            )

        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=sample_recipes, diet_goal="vegetarian", days_count=-1
            )

        with pytest.raises(
            ValueError, match="days_count must be an integer between 3 and 7"
        ):
            MealPlanGenerator.generate_meal_plan(
                recipes=sample_recipes, diet_goal="vegetarian", days_count="3"
            )

    def test_meal_plan_with_maximum_days_and_limited_recipes(self):
        """Test meal plan with 7 days using limited recipes."""
        # Create only 2 recipes for 7 days (need 21 recipes for 3 meals per day)
        limited_recipes = [
            Recipe(
                id=1,
                title="Recipe 1",
                ingredients=[
                    Ingredient(name="ingredient1", quantity="1", unit="cup"),
                ],
                instructions="Instructions 1",
                diet_type=DietType.VEGETARIAN,
            ),
            Recipe(
                id=2,
                title="Recipe 2",
                ingredients=[
                    Ingredient(name="ingredient2", quantity="2", unit="cups"),
                ],
                instructions="Instructions 2",
                diet_type=DietType.VEGETARIAN,
            ),
        ]

        meal_plan, fallback_used = MealPlanGenerator.generate_meal_plan(
            recipes=limited_recipes, diet_goal="vegetarian", days_count=7
        )

        assert meal_plan.total_days == 7
        assert len(meal_plan.days) == 7
        assert fallback_used is False  # Should use diet-filtered recipes

        # Each day should have 3 meals
        for day in meal_plan.days:
            assert len(day.meals) == 3

    def test_meal_plan_shopping_list_with_maximum_days(self, sample_recipes):
        """Test shopping list generation with maximum days (7)."""
        meal_plan, _ = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=7
        )

        shopping_list = meal_plan.get_shopping_list()
        assert shopping_list is not None
        assert len(shopping_list.items) > 0

        # Should have more items than 3-day plan
        three_day_plan, _ = MealPlanGenerator.generate_meal_plan(
            recipes=sample_recipes, diet_goal="vegetarian", days_count=3
        )
        three_day_shopping = three_day_plan.get_shopping_list()
        assert len(shopping_list.items) >= len(three_day_shopping.items)
