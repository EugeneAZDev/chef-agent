"""
Pydantic models for API validation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class IngredientCreate(BaseModel):
    """Model for creating an ingredient."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Ingredient name"
    )
    quantity: str = Field(
        ..., min_length=1, max_length=50, description="Quantity"
    )
    unit: str = Field(
        default="", max_length=20, description="Unit of measurement"
    )


class RecipeCreate(BaseModel):
    """Model for creating a recipe."""

    title: str = Field(
        ..., min_length=1, max_length=200, description="Recipe title"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Recipe description"
    )
    instructions: str = Field(
        ..., min_length=1, description="Cooking instructions"
    )
    prep_time_minutes: Optional[int] = Field(
        None, ge=0, le=1440, description="Prep time in minutes"
    )
    cook_time_minutes: Optional[int] = Field(
        None, ge=0, le=1440, description="Cook time in minutes"
    )
    servings: Optional[int] = Field(
        None, ge=1, le=50, description="Number of servings"
    )
    difficulty: Optional[str] = Field(
        None, pattern="^(easy|medium|hard)$", description="Difficulty level"
    )
    diet_type: Optional[str] = Field(
        None, max_length=50, description="Diet type"
    )
    user_id: Optional[str] = Field(None, max_length=100, description="User ID")
    ingredients: Optional[List[IngredientCreate]] = Field(
        default_factory=list, description="Recipe ingredients"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list, description="Recipe tags"
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(cls, v):
        """Validate ingredients list."""
        if v is None:
            return []
        if len(v) > 50:
            raise ValueError("Too many ingredients (max 50)")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tags list."""
        if v is None:
            return []
        if len(v) > 20:
            raise ValueError("Too many tags (max 20)")
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Tag too long (max 50 characters)")
        return v


class RecipeUpdate(BaseModel):
    """Model for updating a recipe."""

    title: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Recipe title"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Recipe description"
    )
    instructions: Optional[str] = Field(
        None, min_length=1, description="Cooking instructions"
    )
    prep_time_minutes: Optional[int] = Field(
        None, ge=0, le=1440, description="Prep time in minutes"
    )
    cook_time_minutes: Optional[int] = Field(
        None, ge=0, le=1440, description="Cook time in minutes"
    )
    servings: Optional[int] = Field(
        None, ge=1, le=50, description="Number of servings"
    )
    difficulty: Optional[str] = Field(
        None, pattern="^(easy|medium|hard)$", description="Difficulty level"
    )
    diet_type: Optional[str] = Field(
        None, max_length=50, description="Diet type"
    )
    ingredients: Optional[List[IngredientCreate]] = Field(
        None, description="Recipe ingredients"
    )
    tags: Optional[List[str]] = Field(None, description="Recipe tags")

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(cls, v):
        """Validate ingredients list."""
        if v is not None and len(v) > 50:
            raise ValueError("Too many ingredients (max 50)")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tags list."""
        if v is not None:
            if len(v) > 20:
                raise ValueError("Too many tags (max 20)")
            for tag in v:
                if len(tag) > 50:
                    raise ValueError("Tag too long (max 50 characters)")
        return v


class ShoppingItemCreate(BaseModel):
    """Model for creating a shopping list item."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Item name"
    )
    quantity: str = Field(
        ..., min_length=1, max_length=50, description="Quantity"
    )
    unit: str = Field(
        default="", max_length=20, description="Unit of measurement"
    )
    category: Optional[str] = Field(
        None, max_length=50, description="Item category"
    )


class ShoppingListCreate(BaseModel):
    """Model for creating a shopping list."""

    name: Optional[str] = Field(
        None, max_length=100, description="Shopping list name"
    )
    items: Optional[List[ShoppingItemCreate]] = Field(
        default_factory=list, description="Shopping list items"
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        """Validate items list."""
        if v is None:
            return []
        if len(v) > 200:
            raise ValueError("Too many items (max 200)")
        return v
