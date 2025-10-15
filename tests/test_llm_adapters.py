"""
Tests for LLM adapters.

This module contains unit tests for the LLM adapter functionality.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from adapters.llm import LLMFactory
from adapters.llm.groq_adapter import GroqAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from tests.base_test import BaseLLMTest


class TestLLMFactory:
    """Test cases for LLMFactory."""

    def test_create_llm_groq(self):
        """Test creating Groq LLM adapter."""
        result = LLMFactory.create_llm(
            provider="groq", api_key="test-key", model="llama-3.1-8b-instant"
        )

        assert isinstance(result, GroqAdapter)

    def test_create_llm_openai(self):
        """Test creating OpenAI LLM adapter."""
        result = LLMFactory.create_llm(
            provider="openai", api_key="test-key", model="gpt-3.5-turbo"
        )

        assert isinstance(result, OpenAIAdapter)

    def test_create_llm_with_default_model(self):
        """Test creating LLM with default model."""
        result = LLMFactory.create_llm(provider="groq", api_key="test-key")

        assert isinstance(result, GroqAdapter)

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


class TestGroqAdapter(BaseLLMTest):
    """Test cases for GroqAdapter."""

    def test_model_info_structure(self):
        """Test model info returns expected structure."""
        adapter = self.create_mock_groq_adapter()
        info = adapter.get_model_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "supports_tools" in info
        assert "supports_streaming" in info
        assert "temperature" in info
        assert "max_tokens" in info
        assert info["provider"] == "groq"
        assert info["supports_tools"] is True
        assert info["supports_streaming"] is True

    def test_estimate_tokens(self):
        """Test token estimation returns reasonable values."""
        adapter = self.create_mock_groq_adapter()

        assert adapter.get_model_info()["provider"] == "groq"
        test_cases = [
            ("", 0),  # Empty string
            ("a", 0),  # Single character (len=1, 1//4=0)
            ("abc", 0),  # 3 chars (3//4=0)
            ("abcd", 1),  # 4 chars (4//4=1)
            ("Hello world", 2),  # 11 chars (11//4=2)
            (
                "This is a longer text with more content to test estimation",
                14,
            ),  # 58 chars (58//4=14)
        ]

        for text, expected in test_cases:
            tokens = adapter.estimate_tokens(text)
            # Test that estimation is reasonable (not negative, not too high)
            assert (
                tokens >= 0
            ), f"Token count should be non-negative for '{text}'"
            assert tokens <= len(
                text
            ), f"Token count should not exceed text length for '{text}'"
            assert (
                tokens == expected
            ), f"Expected {expected} tokens for '{text}', got {tokens}"

    @pytest.mark.asyncio
    async def test_ainvoke(self):
        """Test async invoke."""
        adapter = self.create_mock_groq_adapter()
        mock_messages = [Mock()]
        mock_response = Mock()

        adapter._llm.ainvoke = AsyncMock(return_value=mock_response)
        result = await adapter.ainvoke(mock_messages)

        assert result == mock_response
        adapter._llm.ainvoke.assert_called_once_with(mock_messages)

    def test_invoke(self):
        """Test sync invoke."""
        adapter = self.create_mock_groq_adapter()
        mock_messages = [Mock()]
        mock_response = Mock()

        adapter._llm.invoke.return_value = mock_response
        result = adapter.invoke(mock_messages)

        assert result == mock_response
        adapter._llm.invoke.assert_called_once_with(mock_messages)

    def test_bind_tools(self):
        """Test binding tools."""
        adapter = self.create_mock_groq_adapter()
        mock_tools = [Mock()]
        mock_response = Mock()

        adapter._llm.bind_tools.return_value = mock_response
        result = adapter.bind_tools(mock_tools)

        assert result == mock_response
        adapter._llm.bind_tools.assert_called_once_with(mock_tools)

    @pytest.mark.asyncio
    async def test_ainvoke_failure(self):
        """Test async invoke failure handling."""
        adapter = self.create_mock_groq_adapter()
        mock_messages = [Mock()]

        adapter._llm.ainvoke.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            await adapter.ainvoke(mock_messages)

    def test_invoke_failure(self):
        """Test sync invoke failure handling."""
        adapter = self.create_mock_groq_adapter()
        mock_messages = [Mock()]

        adapter._llm.invoke.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            adapter.invoke(mock_messages)


class TestOpenAIAdapter(BaseLLMTest):
    """Test cases for OpenAIAdapter."""

    def test_model_info_structure(self):
        """Test model info returns expected structure."""
        adapter = self.create_mock_openai_adapter()
        info = adapter.get_model_info()

        assert isinstance(info, dict)
        assert "provider" in info
        assert "supports_tools" in info
        assert "supports_streaming" in info
        assert "temperature" in info
        assert "max_tokens" in info
        assert info["provider"] == "openai"
        assert info["supports_tools"] is True
        assert info["supports_streaming"] is True

    def test_estimate_tokens(self):
        """Test token estimation returns reasonable values."""
        adapter = self.create_mock_openai_adapter()

        assert adapter.get_model_info()["provider"] == "openai"
        test_cases = [
            ("", 0),  # Empty string
            ("a", 0),  # Single character (len=1, 1//4=0)
            ("abc", 0),  # 3 chars (3//4=0)
            ("abcd", 1),  # 4 chars (4//4=1)
            ("Hello world", 2),  # 11 chars (11//4=2)
            (
                "This is a longer text with more content to test estimation",
                14,
            ),  # 58 chars (58//4=14)
        ]

        for text, expected in test_cases:
            tokens = adapter.estimate_tokens(text)
            # Test that estimation is reasonable (not negative, not too high)
            assert (
                tokens >= 0
            ), f"Token count should be non-negative for '{text}'"
            assert tokens <= len(
                text
            ), f"Token count should not exceed text length for '{text}'"
            assert (
                tokens == expected
            ), f"Expected {expected} tokens for '{text}', got {tokens}"

    @pytest.mark.asyncio
    async def test_ainvoke(self):
        """Test async invoke."""
        adapter = self.create_mock_openai_adapter()
        mock_messages = [Mock()]
        mock_response = Mock()

        adapter._llm.ainvoke = AsyncMock(return_value=mock_response)
        result = await adapter.ainvoke(mock_messages)

        assert result == mock_response
        adapter._llm.ainvoke.assert_called_once_with(mock_messages)

    def test_invoke(self):
        """Test sync invoke."""
        adapter = self.create_mock_openai_adapter()
        mock_messages = [Mock()]
        mock_response = Mock()

        adapter._llm.invoke.return_value = mock_response
        result = adapter.invoke(mock_messages)

        assert result == mock_response
        adapter._llm.invoke.assert_called_once_with(mock_messages)

    def test_bind_tools(self):
        """Test binding tools."""
        adapter = self.create_mock_openai_adapter()
        mock_tools = [Mock()]
        mock_response = Mock()

        adapter._llm.bind_tools.return_value = mock_response
        result = adapter.bind_tools(mock_tools)

        assert result == mock_response
        adapter._llm.bind_tools.assert_called_once_with(mock_tools)

    @pytest.mark.asyncio
    async def test_ainvoke_failure(self):
        """Test async invoke failure handling."""
        adapter = self.create_mock_openai_adapter()
        mock_messages = [Mock()]

        adapter._llm.ainvoke.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            await adapter.ainvoke(mock_messages)

    def test_invoke_failure(self):
        """Test sync invoke failure handling."""
        adapter = self.create_mock_openai_adapter()
        mock_messages = [Mock()]

        adapter._llm.invoke.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            adapter.invoke(mock_messages)
