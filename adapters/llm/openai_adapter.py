"""
OpenAI LLM adapter.

This module provides the OpenAI implementation of the BaseLLM interface.
"""

from typing import Any, Dict, List

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .base import BaseLLM


class OpenAIAdapter(BaseLLM):
    """OpenAI LLM adapter implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ):
        """Initialize OpenAI adapter."""
        super().__init__(api_key, model, **kwargs)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _create_llm(self) -> ChatOpenAI:
        """Create OpenAI LLM instance."""
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **self.kwargs,
        )

    def _create_llm_with_tools(self, tools: List[Any]) -> ChatOpenAI:
        """Create OpenAI LLM instance with tools bound."""
        llm = self._create_llm()
        return llm.bind_tools(tools)

    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Invoke OpenAI LLM asynchronously."""
        return await self.llm.ainvoke(messages, **kwargs)

    def invoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Invoke OpenAI LLM synchronously."""
        return self.llm.invoke(messages, **kwargs)

    def bind_tools(self, tools: List[Any]) -> ChatOpenAI:
        """Bind tools to OpenAI LLM."""
        return self.llm.bind_tools(tools)

    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information."""
        return {
            "provider": "openai",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "supports_tools": True,
            "supports_streaming": True,
        }

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens for OpenAI models (rough approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for most models
        return len(text) // 4
