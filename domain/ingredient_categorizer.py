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
            # English
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
            # German
            "tomate",
            "zwiebel",
            "knoblauch",
            "karotte",
            "kartoffel",
            "salat",
            "spinat",
            "gurke",
            "pilz",
            "brokkoli",
            "blumenkohl",
            "kohl",
            "sellerie",
            "zitrone",
            "limette",
            "orange",
            "apfel",
            "banane",
            "erdbeere",
            "blaubeere",
            "avocado",
            "chili",
            "jalapeno",
            "zucchini",
            "aubergine",
            "kürbis",
            "mais",
            "erbsen",
            "bohnen",
            "linsen",
            # French
            "tomate",
            "oignon",
            "ail",
            "carotte",
            "pomme de terre",
            "laitue",
            "épinard",
            "concombre",
            "champignon",
            "brocoli",
            "chou-fleur",
            "chou",
            "céleri",
            "citron",
            "citron vert",
            "orange",
            "pomme",
            "banane",
            "fraise",
            "myrtille",
            "avocat",
            "piment",
            "jalapeno",
            "courgette",
            "aubergine",
            "courge",
            "maïs",
            "petits pois",
            "haricots",
            "lentilles",
        ],
        "dairy": [
            # English
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
            # German
            "käse",
            "butter",
            "sahne",
            "joghurt",
            "saure sahne",
            "quark",
            "mozzarella",
            "cheddar",
            "parmesan",
            "feta",
            "ricotta",
            "mascarpone",
            "schlagsahne",
            "halb und halb",
            "buttermilch",
            "griechischer joghurt",
            "milch",
            # French
            "fromage",
            "beurre",
            "crème",
            "yaourt",
            "crème sure",
            "fromage blanc",
            "mozzarella",
            "cheddar",
            "parmesan",
            "feta",
            "ricotta",
            "mascarpone",
            "crème épaisse",
            "demi-écrémé",
            "babeurre",
            "yaourt grec",
            "lait",
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
            # English
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
            "ginger",
            # German
            "paprika",
            "kümmel",
            "koriander",
            "kurkuma",
            "zimt",
            "muskatnuss",
            "nelken",
            "kardamom",
            "lorbeerblätter",
            "salbei",
            "majoran",
            "estragon",
            "dill",
            "schnittlauch",
            "petersilie",
            "koriander",
            "basilikum",
            "oregano",
            "thymian",
            "rosmarin",
            "ingwer",
            # French
            "paprika",
            "cumin",
            "coriandre",
            "curcuma",
            "cannelle",
            "muscade",
            "clous de girofle",
            "cardamome",
            "feuilles de laurier",
            "sauge",
            "marjolaine",
            "estragon",
            "aneth",
            "ciboulette",
            "persil",
            "coriandre",
            "basilic",
            "origan",
            "thym",
            "romarin",
            "gingembre",
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

        # Find all matching categories and their keyword lengths
        matches = []
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    # Use keyword length as priority (longer = more specific)
                    matches.append((len(keyword), category))
                    break  # Only one match per category

        if not matches:
            return "other"

        # Return category with the longest (most specific) keyword match
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]

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
