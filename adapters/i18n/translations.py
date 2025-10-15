"""
Translation strings for Chef Agent.

This module contains all translatable strings organized by language.
"""

from typing import Dict

# Translation dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # Common messages
        "welcome": (
            "Welcome to Chef Agent! I can help you plan meals and create "
            "shopping lists."
        ),
        "error_occurred": "An error occurred while processing your request.",
        "no_recipes_found": "No recipes found matching your criteria.",
        "meal_plan_generated": "Your meal plan has been generated successfully!",
        "shopping_list_created": "Shopping list created successfully!",
        # Meal planning
        "meal_plan_title": "Meal Plan",
        "breakfast": "Breakfast",
        "lunch": "Lunch",
        "dinner": "Dinner",
        "snack": "Snack",
        "day": "Day",
        "total_calories": "Total Calories",
        # Diet types
        "vegetarian": "Vegetarian",
        "vegan": "Vegan",
        "keto": "Keto",
        "paleo": "Paleo",
        "mediterranean": "Mediterranean",
        "gluten_free": "Gluten-Free",
        "low_carb": "Low-Carb",
        # Difficulty levels
        "easy": "Easy",
        "medium": "Medium",
        "hard": "Hard",
        # Shopping list
        "shopping_list": "Shopping List",
        "ingredients": "Ingredients",
        "quantity": "Quantity",
        "unit": "Unit",
        "category": "Category",
        # Categories
        "proteins": "Proteins",
        "vegetables": "Vegetables",
        "fruits": "Fruits",
        "dairy": "Dairy",
        "grains": "Grains",
        "beverages": "Beverages",
        "spices": "Spices",
        "other": "Other",
        # Allergens
        "contains_allergens": "Contains allergens: {allergens}",
        "gluten": "Gluten",
        "dairy": "Dairy",
        "nuts": "Nuts",
        "eggs": "Eggs",
        "soy": "Soy",
        "fish": "Fish",
        "shellfish": "Shellfish",
    },
    "ru": {
        # Common messages
        "welcome": (
            "Добро пожаловать в Chef Agent! Я помогу вам планировать "
            "питание и создавать списки покупок."
        ),
        "error_occurred": "Произошла ошибка при обработке вашего запроса.",
        "no_recipes_found": "Рецепты по вашим критериям не найдены.",
        "meal_plan_generated": "Ваш план питания успешно создан!",
        "shopping_list_created": "Список покупок успешно создан!",
        # Meal planning
        "meal_plan_title": "План питания",
        "breakfast": "Завтрак",
        "lunch": "Обед",
        "dinner": "Ужин",
        "snack": "Перекус",
        "day": "День",
        "total_calories": "Общие калории",
        # Diet types
        "vegetarian": "Вегетарианская",
        "vegan": "Веганская",
        "keto": "Кето",
        "paleo": "Палео",
        "mediterranean": "Средиземноморская",
        "gluten_free": "Безглютеновая",
        "low_carb": "Низкоуглеводная",
        # Difficulty levels
        "easy": "Легкая",
        "medium": "Средняя",
        "hard": "Сложная",
        # Shopping list
        "shopping_list": "Список покупок",
        "ingredients": "Ингредиенты",
        "quantity": "Количество",
        "unit": "Единица",
        "category": "Категория",
        # Categories
        "proteins": "Белки",
        "vegetables": "Овощи",
        "fruits": "Фрукты",
        "dairy": "Молочные продукты",
        "grains": "Зерновые",
        "beverages": "Напитки",
        "spices": "Специи",
        "other": "Другое",
        # Allergens
        "contains_allergens": "Содержит аллергены: {allergens}",
        "gluten": "Глютен",
        "dairy": "Молочные продукты",
        "nuts": "Орехи",
        "eggs": "Яйца",
        "soy": "Соя",
        "fish": "Рыба",
        "shellfish": "Моллюски",
    },
    "es": {
        # Common messages
        "welcome": (
            "¡Bienvenido a Chef Agent! Puedo ayudarte a planificar comidas "
            "y crear listas de compras."
        ),
        "error_occurred": "Ocurrió un error al procesar tu solicitud.",
        "no_recipes_found": (
            "No se encontraron recetas que coincidan con tus criterios."
        ),
        "meal_plan_generated": "¡Tu plan de comidas ha sido generado exitosamente!",
        "shopping_list_created": "¡Lista de compras creada exitosamente!",
        # Meal planning
        "meal_plan_title": "Plan de Comidas",
        "breakfast": "Desayuno",
        "lunch": "Almuerzo",
        "dinner": "Cena",
        "snack": "Merienda",
        "day": "Día",
        "total_calories": "Calorías Totales",
        # Diet types
        "vegetarian": "Vegetariana",
        "vegan": "Vegana",
        "keto": "Keto",
        "paleo": "Paleo",
        "mediterranean": "Mediterránea",
        "gluten_free": "Sin Gluten",
        "low_carb": "Baja en Carbohidratos",
        # Difficulty levels
        "easy": "Fácil",
        "medium": "Medio",
        "hard": "Difícil",
        # Shopping list
        "shopping_list": "Lista de Compras",
        "ingredients": "Ingredientes",
        "quantity": "Cantidad",
        "unit": "Unidad",
        "category": "Categoría",
        # Categories
        "proteins": "Proteínas",
        "vegetables": "Verduras",
        "fruits": "Frutas",
        "dairy": "Lácteos",
        "grains": "Granos",
        "beverages": "Bebidas",
        "spices": "Especias",
        "other": "Otro",
        # Allergens
        "contains_allergens": "Contiene alérgenos: {allergens}",
        "gluten": "Gluten",
        "dairy": "Lácteos",
        "nuts": "Frutos secos",
        "eggs": "Huevos",
        "soy": "Soja",
        "fish": "Pescado",
        "shellfish": "Mariscos",
    },
    "fr": {
        # Common messages
        "welcome": (
            "Bienvenue chez Chef Agent ! Je peux vous aider à planifier "
            "vos repas et créer des listes de courses."
        ),
        "error_occurred": (
            "Une erreur s'est produite lors du traitement de votre demande."
        ),
        "no_recipes_found": "Aucune recette trouvée correspondant à vos critères.",
        "meal_plan_generated": "Votre plan de repas a été généré avec succès !",
        "shopping_list_created": "Liste de courses créée avec succès !",
        # Meal planning
        "meal_plan_title": "Plan de Repas",
        "breakfast": "Petit-déjeuner",
        "lunch": "Déjeuner",
        "dinner": "Dîner",
        "snack": "Collation",
        "day": "Jour",
        "total_calories": "Calories Totales",
        # Diet types
        "vegetarian": "Végétarienne",
        "vegan": "Végane",
        "keto": "Keto",
        "paleo": "Paléo",
        "mediterranean": "Méditerranéenne",
        "gluten_free": "Sans Gluten",
        "low_carb": "Faible en Glucides",
        # Difficulty levels
        "easy": "Facile",
        "medium": "Moyen",
        "hard": "Difficile",
        # Shopping list
        "shopping_list": "Liste de Courses",
        "ingredients": "Ingrédients",
        "quantity": "Quantité",
        "unit": "Unité",
        "category": "Catégorie",
        # Categories
        "proteins": "Protéines",
        "vegetables": "Légumes",
        "fruits": "Fruits",
        "dairy": "Produits Laitiers",
        "grains": "Céréales",
        "beverages": "Boissons",
        "spices": "Épices",
        "other": "Autre",
        # Allergens
        "contains_allergens": "Contient des allergènes : {allergens}",
        "gluten": "Gluten",
        "dairy": "Produits Laitiers",
        "nuts": "Noix",
        "eggs": "Œufs",
        "soy": "Soja",
        "fish": "Poisson",
        "shellfish": "Crustacés",
    },
    "de": {
        # Common messages
        "welcome": (
            "Willkommen bei Chef Agent! Ich kann Ihnen helfen, Mahlzeiten "
            "zu planen und Einkaufslisten zu erstellen."
        ),
        "error_occurred": "Ein Fehler ist beim Verarbeiten Ihrer Anfrage aufgetreten.",
        "no_recipes_found": "Keine Rezepte gefunden, die Ihren Kriterien entsprechen.",
        "meal_plan_generated": "Ihr Speiseplan wurde erfolgreich erstellt!",
        "shopping_list_created": "Einkaufsliste erfolgreich erstellt!",
        # Meal planning
        "meal_plan_title": "Speiseplan",
        "breakfast": "Frühstück",
        "lunch": "Mittagessen",
        "dinner": "Abendessen",
        "snack": "Snack",
        "day": "Tag",
        "total_calories": "Gesamtkalorien",
        # Diet types
        "vegetarian": "Vegetarisch",
        "vegan": "Vegan",
        "keto": "Keto",
        "paleo": "Paleo",
        "mediterranean": "Mittelmeer",
        "gluten_free": "Glutenfrei",
        "low_carb": "Kohlenhydratarm",
        # Difficulty levels
        "easy": "Einfach",
        "medium": "Mittel",
        "hard": "Schwer",
        # Shopping list
        "shopping_list": "Einkaufsliste",
        "ingredients": "Zutaten",
        "quantity": "Menge",
        "unit": "Einheit",
        "category": "Kategorie",
        # Categories
        "proteins": "Proteine",
        "vegetables": "Gemüse",
        "fruits": "Früchte",
        "dairy": "Milchprodukte",
        "grains": "Getreide",
        "beverages": "Getränke",
        "spices": "Gewürze",
        "other": "Andere",
        # Allergens
        "contains_allergens": "Enthält Allergene: {allergens}",
        "gluten": "Gluten",
        "dairy": "Milchprodukte",
        "nuts": "Nüsse",
        "eggs": "Eier",
        "soy": "Soja",
        "fish": "Fisch",
        "shellfish": "Schalentiere",
    },
}


def get_translation(key: str, language: str = "en", **kwargs) -> str:
    """
    Get a translated string for the given key and language.

    Args:
        key: Translation key
        language: Language code (en, ru, es, fr, de)
        **kwargs: Format parameters for the translation string

    Returns:
        Translated string or the key if translation not found
    """
    if language not in TRANSLATIONS:
        language = "en"  # Fallback to English

    translation = TRANSLATIONS[language].get(key, key)

    # Format the string with provided parameters
    try:
        return translation.format(**kwargs)
    except (KeyError, ValueError):
        return translation


def get_supported_languages() -> list:
    """Get list of supported language codes."""
    return list(TRANSLATIONS.keys())


def is_language_supported(language: str) -> bool:
    """Check if a language is supported."""
    return language in TRANSLATIONS
