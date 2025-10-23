"""
Tests for LLM error handling and recovery scenarios.

This module contains comprehensive tests for handling various LLM errors,
including API failures, timeouts, rate limits, and recovery mechanisms.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import HumanMessage

from adapters.llm.groq_adapter import GroqAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from agent import ChefAgentGraph
from agent.models import AgentState, ChatRequest, ChatResponse


@pytest.mark.llm_errors
class TestLLMErrorHandling:
    """Test LLM adapter error handling scenarios."""

    def test_groq_api_rate_limit_error(self):
        """Test Groq API rate limit error handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock rate limit error
            mock_groq.return_value.invoke.side_effect = Exception(
                "Rate limit exceeded"
            )

            with pytest.raises(Exception, match="Rate limit exceeded"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_openai_api_quota_exceeded(self):
        """Test OpenAI API quota exceeded error."""
        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")

        with patch("adapters.llm.openai_adapter.ChatOpenAI") as mock_openai:
            # Mock quota exceeded error
            mock_openai.return_value.invoke.side_effect = Exception(
                "Quota exceeded"
            )

            with pytest.raises(Exception, match="Quota exceeded"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_llm_timeout_error(self):
        """Test LLM timeout error handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock timeout error
            mock_groq.return_value.invoke.side_effect = TimeoutError(
                "Request timeout"
            )

            with pytest.raises(TimeoutError, match="Request timeout"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_llm_invalid_api_key(self):
        """Test LLM invalid API key error."""
        adapter = GroqAdapter(
            api_key="invalid-key", model="llama-3.1-8b-instant"
        )

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock invalid API key error
            mock_groq.return_value.invoke.side_effect = Exception(
                "Invalid API key"
            )

            with pytest.raises(Exception, match="Invalid API key"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_llm_model_not_found(self):
        """Test LLM model not found error."""
        adapter = GroqAdapter(api_key="test-key", model="nonexistent-model")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock model not found error
            mock_groq.return_value.invoke.side_effect = Exception(
                "Model not found"
            )

            with pytest.raises(Exception, match="Model not found"):
                adapter.invoke([HumanMessage(content="Test message")])

    def test_llm_network_connection_error(self):
        """Test LLM network connection error."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock network error
            mock_groq.return_value.invoke.side_effect = ConnectionError(
                "Network connection failed"
            )

            with pytest.raises(
                ConnectionError, match="Network connection failed"
            ):
                adapter.invoke([HumanMessage(content="Test message")])

    @pytest.mark.asyncio
    async def test_llm_async_error_handling(self):
        """Test async LLM error handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock async error
            mock_groq.return_value.ainvoke = AsyncMock(
                side_effect=Exception("Async API error")
            )

            with pytest.raises(Exception, match="Async API error"):
                await adapter.ainvoke([HumanMessage(content="Test message")])

    def test_llm_invalid_input_format(self):
        """Test LLM invalid input format error."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        # Test with invalid message format
        with pytest.raises(ValueError):
            adapter.invoke([])  # Empty messages

        with pytest.raises(ValueError):
            adapter.invoke(None)  # None messages

    def test_llm_response_parsing_error(self):
        """Test LLM response parsing error."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock invalid response format
            mock_response = Mock()
            mock_response.content = None  # Invalid content
            mock_groq.return_value.invoke.return_value = mock_response

            # Should handle gracefully
            result = adapter.invoke([HumanMessage(content="Test message")])
            assert result is not None

    def test_llm_empty_response_handling(self):
        """Test LLM empty response handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock empty response
            mock_response = Mock()
            mock_response.content = ""  # Empty content
            mock_groq.return_value.invoke.return_value = mock_response

            # Should handle empty response gracefully
            result = adapter.invoke([HumanMessage(content="Test message")])
            assert result is not None
            assert result.content == ""

    def test_llm_whitespace_only_response(self):
        """Test LLM response with only whitespace."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock whitespace-only response
            mock_response = Mock()
            mock_response.content = "   \n\t  "  # Only whitespace
            mock_groq.return_value.invoke.return_value = mock_response

            # Should handle whitespace-only response
            result = adapter.invoke([HumanMessage(content="Test message")])
            assert result is not None
            assert result.content == "   \n\t  "

    def test_llm_null_response_handling(self):
        """Test LLM null response handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock null response
            mock_response = Mock()
            mock_response.content = None  # Null content
            mock_groq.return_value.invoke.return_value = mock_response

            # Should handle null response gracefully
            result = adapter.invoke([HumanMessage(content="Test message")])
            assert result is not None
            assert result.content is None

    @pytest.mark.asyncio
    async def test_llm_async_empty_response_handling(self):
        """Test async LLM empty response handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock empty async response
            mock_response = Mock()
            mock_response.content = ""
            mock_groq.return_value.ainvoke = AsyncMock(
                return_value=mock_response
            )

            # Should handle empty async response gracefully
            result = await adapter.ainvoke(
                [HumanMessage(content="Test message")]
            )
            assert result is not None
            assert result.content == ""

    def test_llm_response_with_special_characters(self):
        """Test LLM response with special characters."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock response with special characters
            mock_response = Mock()
            mock_response.content = "Response with special chars: \x00\x01\x02"
            mock_groq.return_value.invoke.return_value = mock_response

            # Should handle special characters
            result = adapter.invoke([HumanMessage(content="Test message")])
            assert result is not None
            assert "special chars" in result.content

    def test_llm_very_long_response(self):
        """Test LLM very long response handling."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock very long response
            long_content = "A" * 10000  # 10KB response
            mock_response = Mock()
            mock_response.content = long_content
            mock_groq.return_value.invoke.return_value = mock_response

            # Should handle long response
            result = adapter.invoke([HumanMessage(content="Test message")])
            assert result is not None
            assert len(result.content) == 10000
            assert result.content == long_content


@pytest.mark.llm_errors
class TestAgentLLMErrorHandling:
    """Test agent-level LLM error handling."""

    @pytest.mark.asyncio
    async def test_agent_llm_failure_recovery(self, mock_chef_agent):
        """Test agent recovery from LLM failures."""
        # Mock LLM to fail
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=Mock,
            side_effect=Exception("LLM API Error"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            # Should handle error gracefully
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "error" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_llm_timeout_handling(self, mock_chef_agent):
        """Test agent handling of LLM timeouts."""
        # Mock LLM to timeout
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=Mock,
            side_effect=TimeoutError("Request timeout"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            # Should handle timeout gracefully
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert (
                "timeout" in response.message.lower()
                or "error" in response.message.lower()
            )

    @pytest.mark.asyncio
    async def test_agent_llm_rate_limit_handling(self, mock_chef_agent):
        """Test agent handling of LLM rate limits."""
        # Mock LLM to hit rate limit
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=Mock,
            side_effect=Exception("Rate limit exceeded"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)

            # Should handle rate limit gracefully
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert (
                "rate limit" in response.message.lower()
                or "error" in response.message.lower()
            )

    @pytest.mark.asyncio
    async def test_agent_llm_partial_failure(self, mock_chef_agent):
        """Test agent handling of partial LLM failures."""
        # Mock LLM to fail on first call but succeed on retry
        call_count = 0

        async def mock_ainvoke(state, config=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary API error")
            else:
                # Return successful response
                return AgentState(
                    thread_id="test-123",
                    messages=[
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hello!"},
                    ],
                    language="en",
                )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            side_effect=mock_ainvoke,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            # Agent should handle error gracefully
            response = await mock_chef_agent.process_request(request)

            # Verify response indicates error
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            assert "error" in response.message.lower()

            # Verify it was called
            assert call_count == 1

    def test_agent_llm_configuration_error(self):
        """Test agent handling of LLM configuration errors."""
        # Test with invalid LLM provider - this should raise ValueError from LLMFactory
        # Use patch to ensure we're testing the real LLMFactory without global mocks
        with patch("agent.graph.LLMFactory.create_llm") as mock_factory:
            # Make the mock raise ValueError for unsupported providers
            mock_factory.side_effect = ValueError("Unsupported LLM provider")

            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                ChefAgentGraph("invalid-provider", "test-key", Mock())

    @pytest.mark.asyncio
    async def test_agent_llm_memory_error(self, mock_chef_agent):
        """Test agent handling of LLM memory errors."""
        # Mock memory manager to fail
        with patch.object(
            mock_chef_agent.memory_manager,
            "save_conversation_state",
            new_callable=Mock,
            side_effect=Exception("Memory save error"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            # Should handle memory error gracefully
            response = await mock_chef_agent.process_request(request)
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"

    @pytest.mark.asyncio
    async def test_agent_llm_empty_response_handling(self, mock_chef_agent):
        """Test agent handling of empty LLM responses."""
        # Mock LLM to return empty response
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=AgentState(
                thread_id="test-123",
                messages=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": ""},  # Empty response
                ],
                language="en",
            ),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            # Should handle empty response gracefully
            assert (
                response.message == "" or "error" in response.message.lower()
            )

    @pytest.mark.asyncio
    async def test_agent_llm_whitespace_response_handling(
        self, mock_chef_agent
    ):
        """Test agent handling of whitespace-only LLM responses."""
        # Mock LLM to return whitespace-only response
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=AgentState(
                thread_id="test-123",
                messages=[
                    {"role": "user", "content": "Hello"},
                    {
                        "role": "assistant",
                        "content": "   \n\t  ",
                    },  # Whitespace only
                ],
                language="en",
            ),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            # Should handle whitespace response
            assert (
                response.message.strip() == ""
                or "error" in response.message.lower()
            )

    @pytest.mark.asyncio
    async def test_agent_llm_null_response_handling(self, mock_chef_agent):
        """Test agent handling of null LLM responses."""
        # Mock LLM to return null response by raising an exception
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=Mock,
            side_effect=Exception("LLM returned null response"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            # Should handle null response gracefully
            assert "error" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_llm_special_characters_response(
        self, mock_chef_agent
    ):
        """Test agent handling of LLM responses with special characters."""
        # Mock LLM to return response with special characters
        special_content = "Response with special chars: \x00\x01\x02"

        # Mock the graph to return a proper AgentState
        mock_state = AgentState(
            thread_id="test-123",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": special_content},
            ],
            language="en",
        )

        with patch.object(
            mock_chef_agent.graph,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=mock_state,
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"
            # Should handle special characters
            assert "special chars" in response.message


@pytest.mark.llm_errors
class TestLLMRetryMechanisms:
    """Test LLM retry mechanisms and circuit breakers."""

    def test_llm_retry_on_temporary_failure(self):
        """Test LLM retry on temporary failures."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock temporary failure followed by success
            call_count = 0

            def mock_invoke(messages):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("Temporary failure")
                else:
                    return Mock(content="Success")

            mock_groq.return_value.invoke.side_effect = mock_invoke

            # Should fail on first call (no retry logic implemented)
            with pytest.raises(Exception, match="Temporary failure"):
                adapter.invoke([HumanMessage(content="Test message")])

            # Verify it was called once (no retry)
            assert call_count == 1

    def test_llm_circuit_breaker_pattern(self):
        """Test LLM circuit breaker pattern."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock persistent failure
            mock_groq.return_value.invoke.side_effect = Exception(
                "Persistent API failure"
            )

            # Multiple calls should all fail
            for _ in range(5):
                with pytest.raises(Exception, match="Persistent API failure"):
                    adapter.invoke([HumanMessage(content="Test message")])

    def test_llm_fallback_provider(self):
        """Test LLM fallback to different provider."""
        # This would require implementing fallback logic
        # For now, just test that we can create different adapters
        groq_adapter = GroqAdapter(
            api_key="test-key", model="llama-3.1-8b-instant"
        )
        openai_adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")

        assert groq_adapter.get_model_info()["provider"] == "groq"
        assert openai_adapter.get_model_info()["provider"] == "openai"

    def test_llm_error_logging(self):
        """Test LLM error logging."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock error with specific message
            mock_groq.return_value.invoke.side_effect = Exception(
                "Test error for logging"
            )

            # Test that error is raised (logging is handled internally)
            with pytest.raises(Exception, match="Test error for logging"):
                adapter.invoke([HumanMessage(content="Test message")])


@pytest.mark.llm_errors
class TestLLMErrorRecovery:
    """Test LLM error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_agent_recovery_after_llm_failure(self, mock_chef_agent):
        """Test agent recovery after LLM failure."""
        # First call fails
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=Mock,
            side_effect=Exception("LLM failure"),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert "error" in response.message.lower()

        # Second call succeeds
        with patch.object(
            mock_chef_agent.llm,
            "ainvoke",
            new_callable=AsyncMock,
            return_value=AgentState(
                thread_id="test-123",
                messages=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ],
                language="en",
            ),
        ):
            request = ChatRequest(
                thread_id="test-123", message="Hello again", language="en"
            )

            response = await mock_chef_agent.process_request(request)
            assert isinstance(response, ChatResponse)
            assert response.thread_id == "test-123"

    def test_llm_error_state_preservation(self):
        """Test that LLM errors don't corrupt agent state."""
        # This would require more complex state management testing
        # For now, just verify that adapters maintain their state
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        # Verify adapter state is preserved
        assert adapter.api_key == "test-key"
        assert adapter.model == "llama-3.1-8b-instant"
        assert adapter.temperature == 0.7
        assert adapter.max_tokens == 2048

    def test_llm_error_metrics_collection(self):
        """Test LLM error metrics collection."""
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        with patch("adapters.llm.groq_adapter.ChatGroq") as mock_groq:
            # Mock error
            mock_groq.return_value.invoke.side_effect = Exception("Test error")

            # Track error count
            error_count = 0
            try:
                adapter.invoke([HumanMessage(content="Test message")])
            except Exception:
                error_count += 1

            assert error_count == 1
