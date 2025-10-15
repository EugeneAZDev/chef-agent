"""
Translation utility for Chef Agent.

This module provides a convenient interface for translating strings.
"""

from typing import Optional

from .translations import (
    get_supported_languages,
    get_translation,
    is_language_supported,
)


class Translator:
    """Translation utility class."""

    def __init__(self, default_language: str = "en"):
        """
        Initialize translator with default language.

        Args:
            default_language: Default language code
        """
        if not is_language_supported(default_language):
            default_language = "en"
        self.default_language = default_language

    def translate(
        self, key: str, language: Optional[str] = None, **kwargs
    ) -> str:
        """
        Translate a key to the specified language.

        Args:
            key: Translation key
            language: Target language (uses default if None)
            **kwargs: Format parameters

        Returns:
            Translated string
        """
        target_language = language or self.default_language
        return get_translation(key, target_language, **kwargs)

    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """Short alias for translate method."""
        return self.translate(key, language, **kwargs)

    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return get_supported_languages()

    def is_supported(self, language: str) -> bool:
        """Check if language is supported."""
        return is_language_supported(language)


# Global translator instance
translator = Translator()


def translate(key: str, language: str = "en", **kwargs) -> str:
    """
    Global translation function.

    Args:
        key: Translation key
        language: Target language
        **kwargs: Format parameters

    Returns:
        Translated string
    """
    return translator.translate(key, language, **kwargs)


def t(key: str, language: str = "en", **kwargs) -> str:
    """Short alias for global translate function."""
    return translate(key, language, **kwargs)
