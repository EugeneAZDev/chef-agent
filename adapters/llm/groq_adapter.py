"""
Groq LLM adapter.

This module provides the Groq implementation of the BaseLLM interface.
"""

from typing import Any, Dict, List

from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq

from .base import BaseLLM


class GroqAdapter(BaseLLM):
    """Groq LLM adapter implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ):
        """Initialize Groq adapter."""
        if not api_key:
            raise ValueError("API key cannot be empty")
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if max_tokens <= 0:
            raise ValueError("Max tokens must be positive")

        super().__init__(api_key, model, **kwargs)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _create_llm(self) -> ChatGroq:
        """Create Groq LLM instance."""
        return ChatGroq(
            model=self.model,
            groq_api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **self.kwargs,
        )

    def _create_llm_with_tools(self, tools: List[Any]) -> ChatGroq:
        """Create Groq LLM instance with tools bound."""
        llm = self._create_llm()
        return llm.bind_tools(tools)

    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Invoke Groq LLM asynchronously."""
        return await self.llm.ainvoke(messages, **kwargs)

    def invoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Invoke Groq LLM synchronously."""
        if not messages:
            raise ValueError("Messages list cannot be empty")
        if messages is None:
            raise ValueError("Messages cannot be None")
        return self.llm.invoke(messages, **kwargs)

    def bind_tools(self, tools: List[Any]) -> ChatGroq:
        """Bind tools to Groq LLM."""
        return self.llm.bind_tools(tools)

    def get_model_info(self) -> Dict[str, Any]:
        """Get Groq model information."""
        return {
            "provider": "groq",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "supports_tools": True,
            "supports_streaming": True,
        }

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens for Groq models (rough approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for most models
        return len(text) // 4
