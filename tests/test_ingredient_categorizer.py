"""
Tests for ingredient categorization functionality.
"""

from domain.ingredient_categorizer import IngredientCategorizer


class TestIngredientCategorizer:
    """Test cases for IngredientCategorizer."""

    def test_categorize_ingredient_produce(self):
        """Test categorizing produce ingredients."""
        assert (
            IngredientCategorizer.categorize_ingredient("tomato") == "produce"
        )
        assert (
            IngredientCategorizer.categorize_ingredient("onion") == "produce"
        )
        assert (
            IngredientCategorizer.categorize_ingredient("garlic") == "produce"
        )
        assert (
            IngredientCategorizer.categorize_ingredient("bell pepper")
            == "produce"
        )

    def test_categorize_ingredient_dairy(self):
        """Test categorizing dairy ingredients."""
        assert IngredientCategorizer.categorize_ingredient("milk") == "dairy"
        assert IngredientCategorizer.categorize_ingredient("cheese") == "dairy"
        assert IngredientCategorizer.categorize_ingredient("butter") == "dairy"
        assert (
            IngredientCategorizer.categorize_ingredient("heavy cream")
            == "dairy"
        )

    def test_categorize_ingredient_meat(self):
        """Test categorizing meat ingredients."""
        assert IngredientCategorizer.categorize_ingredient("chicken") == "meat"
        assert IngredientCategorizer.categorize_ingredient("beef") == "meat"
        assert (
            IngredientCategorizer.categorize_ingredient("ground beef")
            == "meat"
        )
        assert IngredientCategorizer.categorize_ingredient("bacon") == "meat"

    def test_categorize_ingredient_pantry(self):
        """Test categorizing pantry ingredients."""
        assert IngredientCategorizer.categorize_ingredient("rice") == "pantry"
        assert IngredientCategorizer.categorize_ingredient("pasta") == "pantry"
        assert IngredientCategorizer.categorize_ingredient("salt") == "pantry"
        assert (
            IngredientCategorizer.categorize_ingredient("vinegar") == "pantry"
        )

    def test_categorize_ingredient_spices(self):
        """Test categorizing spice ingredients."""
        assert (
            IngredientCategorizer.categorize_ingredient("paprika") == "spices"
        )
        assert IngredientCategorizer.categorize_ingredient("cumin") == "spices"
        assert (
            IngredientCategorizer.categorize_ingredient("oregano") == "spices"
        )
        assert (
            IngredientCategorizer.categorize_ingredient("bay leaves")
            == "spices"
        )

    def test_categorize_ingredient_baking(self):
        """Test categorizing baking ingredients."""
        assert IngredientCategorizer.categorize_ingredient("flour") == "baking"
        assert IngredientCategorizer.categorize_ingredient("sugar") == "baking"
        assert (
            IngredientCategorizer.categorize_ingredient("baking powder")
            == "baking"
        )
        assert (
            IngredientCategorizer.categorize_ingredient("vanilla") == "baking"
        )

    def test_categorize_ingredient_unknown(self):
        """Test categorizing unknown ingredients."""
        assert (
            IngredientCategorizer.categorize_ingredient("unknown ingredient")
            == "other"
        )
        assert IngredientCategorizer.categorize_ingredient("") == "other"

    def test_categorize_ingredients_list(self):
        """Test categorizing a list of ingredients."""
        ingredients = [
            {"name": "tomato", "quantity": "2", "unit": "pieces"},
            {"name": "milk", "quantity": "1", "unit": "cup"},
            {"name": "chicken", "quantity": "500", "unit": "g"},
            {"name": "flour", "quantity": "2", "unit": "cups"},
        ]

        categorized = IngredientCategorizer.categorize_ingredients(ingredients)

        assert "produce" in categorized
        assert "dairy" in categorized
        assert "meat" in categorized
        assert "baking" in categorized

        assert len(categorized["produce"]) == 1
        assert len(categorized["dairy"]) == 1
        assert len(categorized["meat"]) == 1
        assert len(categorized["baking"]) == 1

    def test_get_category_display_name(self):
        """Test getting display names for categories."""
        assert (
            IngredientCategorizer.get_category_display_name("produce")
            == "Fresh Produce"
        )
        assert (
            IngredientCategorizer.get_category_display_name("dairy")
            == "Dairy & Eggs"
        )
        assert (
            IngredientCategorizer.get_category_display_name("meat")
            == "Meat & Poultry"
        )
        assert (
            IngredientCategorizer.get_category_display_name("other") == "Other"
        )
