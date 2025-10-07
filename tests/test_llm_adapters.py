"""
Tests for LLM adapters.

This module contains unit tests for the LLM adapter functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from adapters.llm import LLMFactory
from adapters.llm.groq_adapter import GroqAdapter
from adapters.llm.openai_adapter import OpenAIAdapter


class TestLLMFactory:
    """Test cases for LLMFactory."""

    def test_create_llm_groq(self):
        """Test creating Groq LLM adapter."""
        result = LLMFactory.create_llm(
            provider="groq", api_key="test-key", model="llama-3.1-8b-instant"
        )

        assert isinstance(result, GroqAdapter)
        assert result.api_key == "test-key"
        assert result.model == "llama-3.1-8b-instant"

    def test_create_llm_openai(self):
        """Test creating OpenAI LLM adapter."""
        result = LLMFactory.create_llm(
            provider="openai", api_key="test-key", model="gpt-3.5-turbo"
        )

        assert isinstance(result, OpenAIAdapter)
        assert result.api_key == "test-key"
        assert result.model == "gpt-3.5-turbo"

    def test_create_llm_with_default_model(self):
        """Test creating LLM with default model."""
        result = LLMFactory.create_llm(provider="groq", api_key="test-key")

        assert isinstance(result, GroqAdapter)
        assert result.api_key == "test-key"
        assert result.model == "llama-3.1-8b-instant"

    def test_create_llm_unsupported_provider(self):
        """Test creating LLM with unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            LLMFactory.create_llm(provider="unsupported", api_key="test-key")

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = LLMFactory.get_supported_providers()

        assert "groq" in providers
        assert "openai" in providers

    def test_get_adapter_info(self):
        """Test getting adapter info."""
        # Test supported provider
        info = LLMFactory.get_adapter_info("groq")
        assert info["provider"] == "groq"
        assert info["available"] is True
        assert info["adapter_class"] == "GroqAdapter"

        # Test unsupported provider
        info = LLMFactory.get_adapter_info("unsupported")
        assert info["provider"] == "unsupported"
        assert info["available"] is False
        assert info["adapter_class"] is None


class TestGroqAdapter:
    """Test cases for GroqAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("adapters.llm.groq_adapter.ChatGroq"):
            self.adapter = GroqAdapter(
                api_key="test-key",
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=2048,
            )

    def test_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.api_key == "test-key"
        assert self.adapter.model == "llama-3.1-8b-instant"
        assert self.adapter.temperature == 0.7
        assert self.adapter.max_tokens == 2048

    def test_get_model_info(self):
        """Test getting model information."""
        info = self.adapter.get_model_info()

        assert info["provider"] == "groq"
        assert info["model"] == "llama-3.1-8b-instant"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 2048
        assert info["supports_tools"] is True
        assert info["supports_streaming"] is True

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test message with some content."
        tokens = self.adapter.estimate_tokens(text)

        # Should be approximately 1/4 of character count
        expected = len(text) // 4
        assert tokens == expected

    @pytest.mark.asyncio
    async def test_ainvoke(self):
        """Test async invoke."""
        mock_messages = [Mock()]
        mock_response = Mock()

        with patch.object(self.adapter, "_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            result = await self.adapter.ainvoke(mock_messages)

            assert result == mock_response
            mock_llm.ainvoke.assert_called_once_with(mock_messages)

    def test_invoke(self):
        """Test sync invoke."""
        mock_messages = [Mock()]
        mock_response = Mock()

        with patch.object(self.adapter, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response

            result = self.adapter.invoke(mock_messages)

            assert result == mock_response
            mock_llm.invoke.assert_called_once_with(mock_messages)

    def test_bind_tools(self):
        """Test binding tools."""
        mock_tools = [Mock()]
        mock_response = Mock()

        with patch.object(self.adapter, "_llm") as mock_llm:
            mock_llm.bind_tools.return_value = mock_response

            result = self.adapter.bind_tools(mock_tools)

            assert result == mock_response
            mock_llm.bind_tools.assert_called_once_with(mock_tools)


class TestOpenAIAdapter:
    """Test cases for OpenAIAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("adapters.llm.openai_adapter.ChatOpenAI"):
            self.adapter = OpenAIAdapter(
                api_key="test-key",
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=2048,
            )

    def test_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.api_key == "test-key"
        assert self.adapter.model == "gpt-3.5-turbo"
        assert self.adapter.temperature == 0.7
        assert self.adapter.max_tokens == 2048

    def test_get_model_info(self):
        """Test getting model information."""
        info = self.adapter.get_model_info()

        assert info["provider"] == "openai"
        assert info["model"] == "gpt-3.5-turbo"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 2048
        assert info["supports_tools"] is True
        assert info["supports_streaming"] is True

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test message with some content."
        tokens = self.adapter.estimate_tokens(text)

        # Should be approximately 1/4 of character count
        expected = len(text) // 4
        assert tokens == expected

    @pytest.mark.asyncio
    async def test_ainvoke(self):
        """Test async invoke."""
        mock_messages = [Mock()]
        mock_response = Mock()

        with patch.object(self.adapter, "_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            result = await self.adapter.ainvoke(mock_messages)

            assert result == mock_response
            mock_llm.ainvoke.assert_called_once_with(mock_messages)

    def test_invoke(self):
        """Test sync invoke."""
        mock_messages = [Mock()]
        mock_response = Mock()

        with patch.object(self.adapter, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response

            result = self.adapter.invoke(mock_messages)

            assert result == mock_response
            mock_llm.invoke.assert_called_once_with(mock_messages)

    def test_bind_tools(self):
        """Test binding tools."""
        mock_tools = [Mock()]
        mock_response = Mock()

        with patch.object(self.adapter, "_llm") as mock_llm:
            mock_llm.bind_tools.return_value = mock_response

            result = self.adapter.bind_tools(mock_tools)

            assert result == mock_response
            mock_llm.bind_tools.assert_called_once_with(mock_tools)
