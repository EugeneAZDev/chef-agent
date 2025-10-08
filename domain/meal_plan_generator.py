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
    ) -> MealPlan:
        """
        Generate a meal plan based on available recipes and preferences.

        Args:
            recipes: List of available recipes
            diet_goal: Diet goal (e.g., 'low-carb', 'vegetarian')
            days_count: Number of days for the meal plan (3-7)
            preferences: Additional preferences

        Returns:
            Generated meal plan
        """
        if not recipes:
            return MealPlan(days=[], diet_type=None, total_days=0)

        # Filter recipes by diet goal
        filtered_recipes = cls._filter_recipes_by_diet(recipes, diet_goal)

        if not filtered_recipes:
            # If no recipes match diet goal, use all recipes
            filtered_recipes = recipes

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

        return MealPlan(
            days=days,
            diet_type=diet_type,
            total_days=days_count,
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def _filter_recipes_by_diet(
        cls, recipes: List[Recipe], diet_goal: str
    ) -> List[Recipe]:
        """Filter recipes based on diet goal."""
        diet_goal_lower = diet_goal.lower()

        if diet_goal_lower in ["vegetarian", "veggie"]:
            return [
                r
                for r in recipes
                if r.diet_type in ["vegetarian", "vegan"] or not r.diet_type
            ]
        elif diet_goal_lower in ["vegan"]:
            return [r for r in recipes if r.diet_type == "vegan"]
        elif diet_goal_lower in ["low-carb", "keto"]:
            return [
                r
                for r in recipes
                if r.diet_type in ["low-carb", "keto"] or not r.diet_type
            ]
        elif diet_goal_lower in ["gluten-free"]:
            return [
                r
                for r in recipes
                if r.diet_type == "gluten-free" or not r.diet_type
            ]
        else:
            # For other diet goals, return all recipes
            return recipes

    @classmethod
    def _expand_recipe_list(
        cls, recipes: List[Recipe], days_count: int
    ) -> List[Recipe]:
        """Expand recipe list by duplicating recipes if needed."""
        needed_recipes = days_count * len(cls.MEAL_TYPES)
        expanded = recipes.copy()

        while len(expanded) < needed_recipes:
            expanded.extend(recipes)

        return expanded[:needed_recipes]

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

        for meal_type in cls.MEAL_TYPES:
            if recipe_index < len(recipes):
                recipe = recipes[recipe_index]
                meal = Meal(
                    name=meal_type,
                    recipe=recipe,
                    notes=cls._generate_meal_notes(meal_type, recipe),
                )
                meals.append(meal)
                recipe_index += 1

        return MenuDay(
            day_number=day_num,
            meals=meals,
            notes=cls._generate_day_notes(day_num, diet_goal),
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
