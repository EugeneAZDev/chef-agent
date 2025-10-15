"""
Tests for internationalization (i18n) functionality.

This module tests the translation system and multi-language support.
"""

from adapters.i18n import (
    get_supported_languages,
    is_language_supported,
    translate,
    translator,
)


class TestTranslator:
    """Test cases for the translation system."""

    def test_get_supported_languages(self):
        """Test getting supported languages."""
        languages = get_supported_languages()
        assert isinstance(languages, list)
        assert "en" in languages
        assert "ru" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "de" in languages

    def test_is_language_supported(self):
        """Test language support checking."""
        assert is_language_supported("en") is True
        assert is_language_supported("ru") is True
        assert is_language_supported("es") is True
        assert is_language_supported("fr") is True
        assert is_language_supported("de") is True
        assert is_language_supported("invalid") is False
        assert is_language_supported("") is False

    def test_translate_english(self):
        """Test English translations."""
        expected = (
            "Welcome to Chef Agent! I can help you plan meals and create "
            "shopping lists."
        )
        assert translate("welcome", "en") == expected
        assert translate("error_occurred", "en") == (
            "An error occurred while processing your request."
        )
        assert translate("meal_plan_generated", "en") == (
            "Your meal plan has been generated successfully!"
        )

    def test_translate_russian(self):
        """Test Russian translations."""
        expected = (
            "Добро пожаловать в Chef Agent! Я помогу вам планировать "
            "питание и создавать списки покупок."
        )
        assert translate("welcome", "ru") == expected
        assert translate("error_occurred", "ru") == (
            "Произошла ошибка при обработке вашего запроса."
        )
        assert translate("meal_plan_generated", "ru") == (
            "Ваш план питания успешно создан!"
        )

    def test_translate_spanish(self):
        """Test Spanish translations."""
        expected = (
            "¡Bienvenido a Chef Agent! Puedo ayudarte a planificar comidas "
            "y crear listas de compras."
        )
        assert translate("welcome", "es") == expected
        assert translate("error_occurred", "es") == (
            "Ocurrió un error al procesar tu solicitud."
        )
        assert translate("meal_plan_generated", "es") == (
            "¡Tu plan de comidas ha sido generado exitosamente!"
        )

    def test_translate_french(self):
        """Test French translations."""
        expected = (
            "Bienvenue chez Chef Agent ! Je peux vous aider à planifier "
            "vos repas et créer des listes de courses."
        )
        assert translate("welcome", "fr") == expected
        assert translate("error_occurred", "fr") == (
            "Une erreur s'est produite lors du traitement de votre demande."
        )
        assert translate("meal_plan_generated", "fr") == (
            "Votre plan de repas a été généré avec succès !"
        )

    def test_translate_german(self):
        """Test German translations."""
        expected = (
            "Willkommen bei Chef Agent! Ich kann Ihnen helfen, Mahlzeiten "
            "zu planen und Einkaufslisten zu erstellen."
        )
        assert translate("welcome", "de") == expected
        assert translate("error_occurred", "de") == (
            "Ein Fehler ist beim Verarbeiten Ihrer Anfrage aufgetreten."
        )
        assert translate("meal_plan_generated", "de") == (
            "Ihr Speiseplan wurde erfolgreich erstellt!"
        )

    def test_translate_with_parameters(self):
        """Test translations with parameters."""
        result = translate(
            "contains_allergens", "en", allergens="gluten, dairy"
        )
        assert result == "Contains allergens: gluten, dairy"

        result = translate(
            "contains_allergens", "ru", allergens="глютен, молочные продукты"
        )
        assert result == "Содержит аллергены: глютен, молочные продукты"

    def test_translate_fallback_to_english(self):
        """Test fallback to English for unsupported languages."""
        expected = (
            "Welcome to Chef Agent! I can help you plan meals and create "
            "shopping lists."
        )
        result = translate("welcome", "invalid_lang")
        assert result == expected

    def test_translate_unknown_key(self):
        """Test translation of unknown key."""
        result = translate("unknown_key", "en")
        assert result == "unknown_key"

    def test_translator_instance(self):
        """Test translator instance."""
        assert translator.default_language == "en"
        assert translator.is_supported("en") is True
        assert translator.is_supported("invalid") is False

        # Test translation
        result = translator.translate("welcome", "ru")
        assert "Добро пожаловать" in result

    def test_translator_short_alias(self):
        """Test translator short alias method."""
        result = translator.t("welcome", "es")
        assert "Bienvenido" in result

    def test_meal_plan_translations(self):
        """Test meal plan specific translations."""
        # Test meal types
        assert translate("breakfast", "en") == "Breakfast"
        assert translate("lunch", "en") == "Lunch"
        assert translate("dinner", "en") == "Dinner"
        assert translate("snack", "en") == "Snack"

        # Test Russian meal types
        assert translate("breakfast", "ru") == "Завтрак"
        assert translate("lunch", "ru") == "Обед"
        assert translate("dinner", "ru") == "Ужин"
        assert translate("snack", "ru") == "Перекус"

    def test_diet_type_translations(self):
        """Test diet type translations."""
        # Test English diet types
        assert translate("vegetarian", "en") == "Vegetarian"
        assert translate("vegan", "en") == "Vegan"
        assert translate("keto", "en") == "Keto"
        assert translate("paleo", "en") == "Paleo"

        # Test Russian diet types
        assert translate("vegetarian", "ru") == "Вегетарианская"
        assert translate("vegan", "ru") == "Веганская"
        assert translate("keto", "ru") == "Кето"
        assert translate("paleo", "ru") == "Палео"

    def test_difficulty_translations(self):
        """Test difficulty level translations."""
        # Test English difficulty levels
        assert translate("easy", "en") == "Easy"
        assert translate("medium", "en") == "Medium"
        assert translate("hard", "en") == "Hard"

        # Test Russian difficulty levels
        assert translate("easy", "ru") == "Легкая"
        assert translate("medium", "ru") == "Средняя"
        assert translate("hard", "ru") == "Сложная"

    def test_shopping_list_translations(self):
        """Test shopping list translations."""
        # Test English shopping list terms
        assert translate("shopping_list", "en") == "Shopping List"
        assert translate("ingredients", "en") == "Ingredients"
        assert translate("quantity", "en") == "Quantity"
        assert translate("unit", "en") == "Unit"
        assert translate("category", "en") == "Category"

        # Test Russian shopping list terms
        assert translate("shopping_list", "ru") == "Список покупок"
        assert translate("ingredients", "ru") == "Ингредиенты"
        assert translate("quantity", "ru") == "Количество"
        assert translate("unit", "ru") == "Единица"
        assert translate("category", "ru") == "Категория"

    def test_category_translations(self):
        """Test ingredient category translations."""
        # Test English categories
        assert translate("proteins", "en") == "Proteins"
        assert translate("vegetables", "en") == "Vegetables"
        assert translate("fruits", "en") == "Fruits"
        assert translate("dairy", "en") == "Dairy"
        assert translate("grains", "en") == "Grains"
        assert translate("beverages", "en") == "Beverages"
        assert translate("spices", "en") == "Spices"
        assert translate("other", "en") == "Other"

        # Test Russian categories
        assert translate("proteins", "ru") == "Белки"
        assert translate("vegetables", "ru") == "Овощи"
        assert translate("fruits", "ru") == "Фрукты"
        assert translate("dairy", "ru") == "Молочные продукты"
        assert translate("grains", "ru") == "Зерновые"
        assert translate("beverages", "ru") == "Напитки"
        assert translate("spices", "ru") == "Специи"
        assert translate("other", "ru") == "Другое"

    def test_allergen_translations(self):
        """Test allergen translations."""
        # Test English allergens
        assert translate("gluten", "en") == "Gluten"
        assert translate("dairy", "en") == "Dairy"
        assert translate("nuts", "en") == "Nuts"
        assert translate("eggs", "en") == "Eggs"
        assert translate("soy", "en") == "Soy"
        assert translate("fish", "en") == "Fish"
        assert translate("shellfish", "en") == "Shellfish"

        # Test Russian allergens
        assert translate("gluten", "ru") == "Глютен"
        assert translate("dairy", "ru") == "Молочные продукты"
        assert translate("nuts", "ru") == "Орехи"
        assert translate("eggs", "ru") == "Яйца"
        assert translate("soy", "ru") == "Соя"
        assert translate("fish", "ru") == "Рыба"
        assert translate("shellfish", "ru") == "Моллюски"

    def test_translation_consistency(self):
        """Test that all languages have the same keys."""
        languages = get_supported_languages()
        english_keys = (
            set(translator.translate("", "en").keys())
            if hasattr(translator.translate("", "en"), "keys")
            else set()
        )

        # Get all keys from English translations
        from adapters.i18n.translations import TRANSLATIONS

        english_keys = set(TRANSLATIONS["en"].keys())

        for language in languages:
            if language != "en":
                language_keys = set(TRANSLATIONS[language].keys())
                # Check that all English keys exist in other languages
                missing_keys = english_keys - language_keys
                assert (
                    len(missing_keys) == 0
                ), f"Missing keys in {language}: {missing_keys}"
