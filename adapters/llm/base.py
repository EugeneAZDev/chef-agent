"""
Base LLM interface and provider enum.

This module defines the abstract base class for LLM adapters
and the supported provider types.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class BaseLLM(ABC):
    """Abstract base class for LLM adapters."""

    def __init__(self, api_key: str, model: str, **kwargs):
        """Initialize the LLM adapter."""
        if not api_key:
            raise ValueError("API key cannot be empty")
        if not model:
            raise ValueError("Model cannot be empty")

        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs
        self._llm = None
        self._llm_with_tools = None

    @abstractmethod
    def _create_llm(self) -> Any:
        """Create the underlying LLM instance."""
        pass

    @abstractmethod
    def _create_llm_with_tools(self, tools: List[Any]) -> Any:
        """Create LLM instance with tools bound."""
        pass

    @property
    def llm(self) -> Any:
        """Get the LLM instance."""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def get_llm_with_tools(self, tools: List[Any]) -> Any:
        """Get LLM instance with tools bound."""
        if self._llm_with_tools is None:
            self._llm_with_tools = self._create_llm_with_tools(tools)
        return self._llm_with_tools

    @abstractmethod
    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Invoke the LLM asynchronously."""
        pass

    @abstractmethod
    def invoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Invoke the LLM synchronously."""
        pass

    @abstractmethod
    def bind_tools(self, tools: List[Any]) -> Any:
        """Bind tools to the LLM."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in text."""
        pass

    def close(self) -> None:
        """Close the LLM and clean up resources."""
        self._llm = None
        self._llm_with_tools = None
