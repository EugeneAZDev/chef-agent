"""
Ingredient categorization utility.

This module provides functionality to automatically categorize ingredients
based on their names for better shopping list organization.
"""

from typing import Dict


class IngredientCategorizer:
    """Categorizes ingredients based on their names."""

    # Category mappings based on ingredient names
    CATEGORY_KEYWORDS = {
        "produce": [
            "tomato",
            "onion",
            "garlic",
            "carrot",
            "potato",
            "lettuce",
            "spinach",
            "cucumber",
            "mushroom",
            "broccoli",
            "cauliflower",
            "cabbage",
            "celery",
            "lemon",
            "lime",
            "orange",
            "apple",
            "banana",
            "strawberry",
            "blueberry",
            "avocado",
            "ginger",
            "chili",
            "jalapeno",
            "bell pepper",
            "zucchini",
            "eggplant",
            "squash",
            "pumpkin",
            "corn",
            "peas",
            "beans",
            "lentils",
        ],
        "dairy": [
            "cheese",
            "butter",
            "cream",
            "yogurt",
            "sour cream",
            "cottage cheese",
            "mozzarella",
            "cheddar",
            "parmesan",
            "feta",
            "ricotta",
            "mascarpone",
            "heavy cream",
            "half and half",
            "buttermilk",
            "greek yogurt",
            "milk",
        ],
        "meat": [
            "chicken",
            "beef",
            "pork",
            "lamb",
            "turkey",
            "bacon",
            "ham",
            "sausage",
            "ground beef",
            "ground turkey",
            "ground pork",
            "steak",
            "chops",
            "roast",
            "breast",
            "thigh",
            "drumstick",
            "wing",
            "ribs",
            "tenderloin",
        ],
        "seafood": [
            "salmon",
            "tuna",
            "shrimp",
            "crab",
            "lobster",
            "cod",
            "halibut",
            "tilapia",
            "mahi mahi",
            "scallops",
            "mussels",
            "clams",
            "oysters",
            "fish",
            "seafood",
        ],
        "pantry": [
            "salt",
            "pepper",
            "oil",
            "vinegar",
            "rice",
            "pasta",
            "bread",
            "crackers",
            "cereal",
            "oats",
            "quinoa",
            "barley",
            "bulgur",
            "couscous",
            "noodles",
            "spaghetti",
            "macaroni",
            "penne",
            "fettuccine",
        ],
        "spices": [
            "paprika",
            "cumin",
            "coriander",
            "turmeric",
            "cinnamon",
            "nutmeg",
            "cloves",
            "cardamom",
            "bay leaves",
            "sage",
            "marjoram",
            "tarragon",
            "dill",
            "chives",
            "parsley",
            "cilantro",
            "basil",
            "oregano",
            "thyme",
            "rosemary",
        ],
        "baking": [
            "baking powder",
            "baking soda",
            "yeast",
            "vanilla",
            "cocoa",
            "chocolate",
            "nuts",
            "almonds",
            "walnuts",
            "pecans",
            "hazelnuts",
            "pistachios",
            "raisins",
            "dates",
            "coconut",
            "flour",
            "sugar",
            "brown sugar",
        ],
        "frozen": [
            "frozen",
            "ice cream",
            "frozen vegetables",
            "frozen fruit",
            "frozen berries",
        ],
        "beverages": [
            "juice",
            "wine",
            "beer",
            "soda",
            "water",
            "tea",
            "coffee",
            "coconut milk",
            "almond milk",
            "soy milk",
            "broth",
            "stock",
        ],
    }

    @classmethod
    def categorize_ingredient(cls, ingredient_name: str) -> str:
        """
        Categorize an ingredient based on its name.

        Args:
            ingredient_name: Name of the ingredient to categorize

        Returns:
            Category name or 'other' if no match found
        """
        name_lower = ingredient_name.lower().strip()

        # Check each category for keyword matches
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category

        # Default category for unmatched ingredients
        return "other"

    @classmethod
    def categorize_ingredients(cls, ingredients: list) -> Dict[str, list]:
        """
        Categorize a list of ingredients.

        Args:
            ingredients: List of ingredient dictionaries with 'name' key

        Returns:
            Dictionary mapping categories to lists of ingredients
        """
        categorized = {}

        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                name = ingredient.get("name", "")
            else:
                name = str(ingredient)

            category = cls.categorize_ingredient(name)

            if category not in categorized:
                categorized[category] = []
            categorized[category].append(ingredient)

        return categorized

    @classmethod
    def get_category_display_name(cls, category: str) -> str:
        """
        Get a display-friendly name for a category.

        Args:
            category: Category key

        Returns:
            Display name for the category
        """
        display_names = {
            "produce": "Fresh Produce",
            "dairy": "Dairy & Eggs",
            "meat": "Meat & Poultry",
            "seafood": "Seafood",
            "pantry": "Pantry Staples",
            "spices": "Spices & Herbs",
            "baking": "Baking Supplies",
            "frozen": "Frozen Foods",
            "beverages": "Beverages",
            "other": "Other",
        }
        return display_names.get(category, category.title())
