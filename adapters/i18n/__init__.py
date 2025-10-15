"""
Internationalization (i18n) support for Chef Agent.

This module provides translation functionality for multiple languages.
"""

from .translator import (
    get_supported_languages,
    is_language_supported,
    translate,
    translator,
)

__all__ = [
    "translate",
    "translator",
    "get_supported_languages",
    "is_language_supported",
]
