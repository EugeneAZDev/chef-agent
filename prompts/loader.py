"""Prompt loader utility for loading prompts from files."""

import json
from pathlib import Path
from typing import Dict, Optional


class PromptLoader:
    """Utility class for loading prompts from files."""

    def __init__(self, prompts_dir: Optional[str] = None):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Path to the prompts directory.
                        If None, uses the default prompts directory.
        """
        if prompts_dir is None:
            # Get the directory where this file is located
            current_dir = Path(__file__).parent
            self.prompts_dir = current_dir
        else:
            self.prompts_dir = Path(prompts_dir)

        self._cache: Dict[str, Dict[str, str]] = {}

    def load_system_prompts(self) -> Dict[str, str]:
        """Load system prompts from the JSON file.

        Returns:
            Dictionary mapping language codes to prompt texts.
        """
        cache_key = "system_prompts"

        if cache_key not in self._cache:
            prompts_file = self.prompts_dir / "system_prompts.json"

            if not prompts_file.exists():
                raise FileNotFoundError(
                    f"System prompts file not found: {prompts_file}"
                )

            with open(prompts_file, "r", encoding="utf-8") as f:
                self._cache[cache_key] = json.load(f)

        return self._cache[cache_key]

    def get_system_prompt(self, language: str = "en") -> str:
        """Get system prompt for a specific language.

        Args:
            language: Language code (e.g., 'en', 'de', 'fr').

        Returns:
            System prompt text for the specified language.
            Falls back to English if language not found.
        """
        prompts = self.load_system_prompts()
        return prompts.get(language, prompts.get("en", ""))

    def reload_prompts(self) -> None:
        """Reload all prompts from files, clearing the cache."""
        self._cache.clear()

    def get_available_languages(self) -> list[str]:
        """Get list of available languages.

        Returns:
            List of language codes for which prompts are available.
        """
        prompts = self.load_system_prompts()
        return list(prompts.keys())


# Global instance for easy access
prompt_loader = PromptLoader()
