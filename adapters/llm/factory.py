"""
LLM Factory for creating LLM adapters.

This module provides a factory pattern for creating LLM adapters
based on the provider type.
"""

from typing import Any, Dict, Optional

from .base import BaseLLM, LLMProvider
from .groq_adapter import GroqAdapter
from .openai_adapter import OpenAIAdapter


class LLMFactory:
    """Factory for creating LLM adapters."""

    _adapters: Dict[LLMProvider, type] = {
        LLMProvider.GROQ: GroqAdapter,
        LLMProvider.OPENAI: OpenAIAdapter,
    }

    @classmethod
    def create_llm(
        cls, provider: str, api_key: str, model: Optional[str] = None, **kwargs
    ) -> BaseLLM:
        """
        Create an LLM adapter instance.

        Args:
            provider: LLM provider name (groq, openai, etc.)
            api_key: API key for the provider
            model: Model name (optional, uses default if not provided)
            **kwargs: Additional arguments for the adapter

        Returns:
            LLM adapter instance

        Raises:
            ValueError: If provider is not supported
        """
        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        if provider_enum not in cls._adapters:
            raise ValueError(f"No adapter available for provider: {provider}")

        adapter_class = cls._adapters[provider_enum]

        # Set default model if not provided
        if model is None:
            model = cls._get_default_model(provider_enum)

        return adapter_class(api_key=api_key, model=model, **kwargs)

    @classmethod
    def create_llm_from_config(cls, provider: str, **kwargs) -> BaseLLM:
        """
        Create an LLM adapter instance using configuration settings.

        Args:
            provider: LLM provider name (groq, openai, etc.)
            **kwargs: Additional arguments for the adapter

        Returns:
            LLM adapter instance

        Raises:
            ValueError: If provider is not supported
        """
        try:
            from config import settings
        except ImportError:
            raise ImportError("Could not import settings from config")

        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        if provider_enum not in cls._adapters:
            raise ValueError(f"No adapter available for provider: {provider}")

        adapter_class = cls._adapters[provider_enum]

        # Get API key and model from settings based on provider
        if provider_enum == LLMProvider.GROQ:
            api_key = settings.groq_api_key
            model = settings.groq_model_name
        elif provider_enum == LLMProvider.OPENAI:
            api_key = getattr(settings, "openai_api_key", "")
            model = getattr(settings, "openai_model_name", "gpt-3.5-turbo")
        else:
            api_key = getattr(settings, f"{provider}_api_key", "")
            model = getattr(
                settings,
                f"{provider}_model_name",
                cls._get_default_model(provider_enum),
            )

        if not api_key:
            raise ValueError(f"API key not found for provider: {provider}")

        return adapter_class(api_key=api_key, model=model, **kwargs)

    @classmethod
    def _get_default_model(cls, provider: LLMProvider) -> str:
        """Get default model for provider."""
        defaults = {
            LLMProvider.GROQ: "llama-3.1-8b-instant",
            LLMProvider.OPENAI: "gpt-3.5-turbo",
        }
        return defaults.get(provider, "gpt-3.5-turbo")

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported providers."""
        return [provider.value for provider in cls._adapters.keys()]

    @classmethod
    def register_adapter(
        cls, provider: LLMProvider, adapter_class: type
    ) -> None:
        """Register a new adapter for a provider."""
        cls._adapters[provider] = adapter_class

    @classmethod
    def get_adapter_info(cls, provider: str) -> Dict[str, Any]:
        """Get information about an adapter."""
        try:
            provider_enum = LLMProvider(provider.lower())
            adapter_class = cls._adapters.get(provider_enum)

            if adapter_class:
                return {
                    "provider": provider,
                    "adapter_class": adapter_class.__name__,
                    "available": True,
                }
            else:
                return {
                    "provider": provider,
                    "adapter_class": None,
                    "available": False,
                }
        except ValueError:
            return {
                "provider": provider,
                "adapter_class": None,
                "available": False,
            }
