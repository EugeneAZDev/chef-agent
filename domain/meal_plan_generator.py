"""
Meal plan generation utility.

This module provides functionality to generate meal plans based on
diet goals, preferences, and available recipes.
"""

from datetime import datetime
from typing import List, Optional

from .entities import DietType, Meal, MealPlan, MenuDay, Recipe


class MealPlanGenerator:
    """Generates meal plans based on diet goals and preferences."""

    MEAL_TYPES = ["breakfast", "lunch", "dinner"]
    MEAL_TIMES = {"breakfast": "08:00", "lunch": "13:00", "dinner": "19:00"}

    @classmethod
    def generate_meal_plan(
        cls,
        recipes: List[Recipe],
        diet_goal: str,
        days_count: int,
        preferences: Optional[List[str]] = None,
    ) -> tuple[MealPlan, bool]:
        """
        Generate a meal plan based on available recipes and preferences.

        Args:
            recipes: List of available recipes
            diet_goal: Diet goal (e.g., 'low-carb', 'vegetarian')
            days_count: Number of days for the meal plan (3-7)
            preferences: Additional preferences

        Returns:
            tuple: (Generated meal plan, fallback_used) where fallback_used
                   indicates if all recipes were used instead of
                   diet-filtered ones
        """
        # Validate days_count
        if not isinstance(days_count, int) or days_count < 3 or days_count > 7:
            raise ValueError(
                f"days_count must be an integer between 3 and 7, "
                f"got {days_count}"
            )

        if not recipes:
            raise ValueError("Cannot generate meal plan: no recipes available")

        # Filter recipes by diet goal
        filtered_recipes = cls._filter_recipes_by_diet(recipes, diet_goal)
        fallback_used = False

        if not filtered_recipes:
            # If no recipes match diet goal, use all recipes
            filtered_recipes = recipes
            fallback_used = True

        # Ensure we have enough recipes for the meal plan
        if len(filtered_recipes) < days_count * len(cls.MEAL_TYPES):
            # Duplicate recipes if needed
            filtered_recipes = cls._expand_recipe_list(
                filtered_recipes, days_count
            )

        # Generate days
        days = []
        for day_num in range(1, days_count + 1):
            day = cls._generate_menu_day(
                day_num, filtered_recipes, diet_goal, preferences
            )
            days.append(day)

        # Determine diet type
        diet_type = cls._determine_diet_type(diet_goal)

        return (
            MealPlan(
                days=days,
                diet_type=diet_type,
                total_days=days_count,
                created_at=datetime.now().isoformat(),
            ),
            fallback_used,
        )

    @classmethod
    def _filter_recipes_by_diet(
        cls, recipes: List[Recipe], diet_goal: str
    ) -> List[Recipe]:
        """Filter recipes based on diet goal."""
        diet_goal_lower = diet_goal.lower()

        if diet_goal_lower in ["vegetarian", "veggie"]:
            filtered = [
                r
                for r in recipes
                if r.diet_type in [DietType.VEGETARIAN, DietType.VEGAN]
            ]
            if not filtered:
                print(
                    "Warning: No vegetarian recipes found. "
                    "Consider adding recipes with diet_type "
                    "VEGETARIAN or VEGAN."
                )
            return filtered
        elif diet_goal_lower in ["vegan"]:
            filtered = [r for r in recipes if r.diet_type == DietType.VEGAN]
            if not filtered:
                print(
                    "Warning: No vegan recipes found. "
                    "Consider adding recipes with diet_type VEGAN."
                )
            return filtered
        elif diet_goal_lower in ["low-carb", "keto"]:
            filtered = [
                r
                for r in recipes
                if r.diet_type in [DietType.LOW_CARB, DietType.KETO]
            ]
            if not filtered:
                print(
                    "Warning: No low-carb/keto recipes found. "
                    "Consider adding recipes with diet_type LOW_CARB or KETO."
                )
            return filtered
        elif diet_goal_lower in ["gluten-free"]:
            filtered = [
                r for r in recipes if r.diet_type == DietType.GLUTEN_FREE
            ]
            if not filtered:
                print(
                    "Warning: No gluten-free recipes found. "
                    "Consider adding recipes with diet_type GLUTEN_FREE."
                )
            return filtered
        else:
            # For other diet goals, return all recipes
            return recipes

    @classmethod
    def _expand_recipe_list(
        cls, recipes: List[Recipe], days_count: int
    ) -> List[Recipe]:
        """Expand recipe list by duplicating recipes if needed."""
        import random

        needed_recipes = days_count * len(cls.MEAL_TYPES)
        expanded = recipes.copy()

        # Shuffle recipes to avoid monotonous repetition
        random.shuffle(expanded)

        while len(expanded) < needed_recipes:
            # Add shuffled copies to maintain variety
            shuffled_copy = recipes.copy()
            random.shuffle(shuffled_copy)
            expanded.extend(shuffled_copy)

        # Shuffle final result
        random.shuffle(expanded)
        return expanded

    @classmethod
    def _generate_menu_day(
        cls,
        day_num: int,
        recipes: List[Recipe],
        diet_goal: str,
        preferences: Optional[List[str]] = None,
    ) -> MenuDay:
        """Generate a single day's menu."""
        meals = []
        recipe_index = (day_num - 1) * len(cls.MEAL_TYPES)
        total_calories = 0

        for meal_type in cls.MEAL_TYPES:
            if recipe_index < len(recipes):
                recipe = recipes[recipe_index]
                meal = Meal(
                    name=meal_type,
                    recipe=recipe,
                    notes=cls._generate_meal_notes(meal_type, recipe),
                )
                meals.append(meal)

                # Estimate calories for this meal
                meal_calories = cls._estimate_recipe_calories(recipe)
                total_calories += meal_calories

                recipe_index += 1

        return MenuDay(
            day_number=day_num,
            meals=meals,
            notes=cls._generate_day_notes(day_num, diet_goal),
            total_calories=total_calories if total_calories > 0 else None,
        )

    @classmethod
    def _generate_meal_notes(cls, meal_type: str, recipe: Recipe) -> str:
        """Generate notes for a meal."""
        notes = []

        if recipe.prep_time_minutes:
            notes.append(f"Prep time: {recipe.prep_time_minutes} minutes")

        if recipe.cook_time_minutes:
            notes.append(f"Cook time: {recipe.cook_time_minutes} minutes")

        if recipe.servings:
            notes.append(f"Serves: {recipe.servings}")

        if recipe.difficulty:
            notes.append(f"Difficulty: {recipe.difficulty}")

        return "; ".join(notes) if notes else None

    @classmethod
    def _generate_day_notes(cls, day_num: int, diet_goal: str) -> str:
        """Generate notes for a day."""
        notes = [f"Day {day_num} of {diet_goal} meal plan"]

        if day_num == 1:
            notes.append("Start of your meal plan journey!")
        elif day_num == 7:
            notes.append("Final day - great job sticking to your plan!")

        return " | ".join(notes)

    @classmethod
    def _estimate_recipe_calories(cls, recipe: Recipe) -> int:
        """Estimate calories for a recipe based on ingredients."""
        if not recipe.ingredients:
            return 0

        # Simple calorie estimation based on common ingredients
        calorie_map = {
            # Proteins (per 100g)
            "chicken": 165,
            "beef": 250,
            "pork": 242,
            "fish": 206,
            "salmon": 208,
            "eggs": 155,
            "tofu": 76,
            "beans": 347,
            "lentils": 353,
            # Carbs (per 100g)
            "rice": 130,
            "pasta": 131,
            "bread": 265,
            "potato": 77,
            "quinoa": 368,
            "oats": 389,
            "flour": 364,
            "sugar": 387,
            # Fats (per 100g)
            "oil": 884,
            "butter": 717,
            "olive": 884,
            "avocado": 160,
            # Vegetables (per 100g)
            "tomato": 18,
            "onion": 40,
            "carrot": 41,
            "broccoli": 34,
            "spinach": 23,
            "lettuce": 15,
            "cucumber": 16,
            "pepper": 31,
            "mushroom": 22,
            # Fruits (per 100g)
            "apple": 52,
            "banana": 89,
            "orange": 47,
            "strawberry": 32,
            # Dairy (per 100g)
            "milk": 42,
            "cheese": 113,
            "yogurt": 59,
            "cream": 345,
        }

        total_calories = 0
        for ingredient in recipe.ingredients:
            ingredient_name = ingredient.name.lower()
            # Find matching ingredient in calorie map
            for key, calories in calorie_map.items():
                if key in ingredient_name:
                    # Estimate quantity in grams (simplified)
                    try:
                        quantity = (
                            float(ingredient.quantity)
                            if ingredient.quantity
                            else 100
                        )
                        # Convert common units to grams
                        if ingredient.unit.lower() in ["kg", "kilogram"]:
                            quantity *= 1000
                        elif ingredient.unit.lower() in ["lb", "pound"]:
                            quantity *= 453.592
                        elif ingredient.unit.lower() in ["oz", "ounce"]:
                            quantity *= 28.3495
                        elif ingredient.unit.lower() in ["cup", "cups"]:
                            quantity *= 240  # Approximate
                        elif ingredient.unit.lower() in ["tbsp", "tablespoon"]:
                            quantity *= 15
                        elif ingredient.unit.lower() in ["tsp", "teaspoon"]:
                            quantity *= 5

                        total_calories += calories * quantity / 100
                        break
                    except (ValueError, TypeError):
                        # If quantity can't be parsed, use default estimate
                        total_calories += calories * 0.5  # Assume 50g
                        break

        return int(total_calories)

    @classmethod
    def _determine_diet_type(cls, diet_goal: str) -> Optional[DietType]:
        """Determine DietType enum from diet goal string."""
        diet_goal_lower = diet_goal.lower()

        diet_mapping = {
            "low-carb": DietType.LOW_CARB,
            "vegetarian": DietType.VEGETARIAN,
            "vegan": DietType.VEGAN,
            "high-protein": DietType.HIGH_PROTEIN,
            "keto": DietType.KETO,
            "mediterranean": DietType.MEDITERRANEAN,
            "gluten-free": DietType.GLUTEN_FREE,
            "paleo": DietType.PALEO,
        }

        return diet_mapping.get(diet_goal_lower)

    @classmethod
    def validate_meal_plan(cls, meal_plan: MealPlan) -> bool:
        """Validate that a meal plan meets basic requirements."""
        if not meal_plan.days:
            return False

        if meal_plan.total_days < 3 or meal_plan.total_days > 7:
            return False

        # Check that each day has at least one meal
        for day in meal_plan.days:
            if not day.meals:
                return False

        return True
