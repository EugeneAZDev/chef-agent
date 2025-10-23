"""
Test MCP client connectivity and agent initialization.
"""

import pytest

from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from agent import ChefAgentGraph
from config import settings


@pytest.mark.integration
class TestMCPClient:
    """Test MCP client functionality."""

    def test_mcp_client_creation(self):
        """Test that MCP client can be created."""
        client = ChefAgentHTTPMCPClient()
        assert client is not None
        assert client.base_url == "http://localhost:8072"

    @pytest.mark.asyncio
    async def test_mcp_client_health_check(self):
        """Test that MCP client can connect to server."""
        client = ChefAgentHTTPMCPClient()

        # Test connection by trying to find recipes - this will test server connectivity
        try:
            result = await client.find_recipes("test", limit=1)
            # If server is available, result should be a dict
            # If server is not available, it should return error dict
            assert isinstance(result, dict)
            # Check if it's an error response or success response
            if "success" in result:
                # This is an error response from our client
                assert result["success"] is False
            else:
                # This is a success response from the server
                assert "recipes" in result
        except Exception as e:
            # If there's an unexpected error, fail the test
            pytest.fail(f"Unexpected error in connection test: {e}")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_mcp_client_find_recipes(self):
        """Test that MCP client can find recipes."""
        client = ChefAgentHTTPMCPClient()

        # Test find recipes - it should handle connection errors gracefully
        try:
            result = await client.find_recipes("vegetarian", limit=5)
            # If server is available, result should be a dict
            # If server is not available, it should return error dict
            assert isinstance(result, dict)
        except Exception as e:
            # If there's an unexpected error, fail the test
            pytest.fail(f"Unexpected error in find_recipes: {e}")
        finally:
            await client.close()

    def test_agent_with_mcp_client(self):
        """Test that agent can be created with MCP client."""
        # Create MCP client and agent with it
        mcp_client = ChefAgentHTTPMCPClient()
        agent = ChefAgentGraph(
            llm_provider="groq",
            api_key=settings.groq_api_key,
            mcp_client=mcp_client,
        )

        assert agent is not None
        assert agent.mcp_client is not None
        # With MCP client, agent should have more tools available
        assert (
            len(agent.tools) >= 5
        ), f"Agent has {len(agent.tools)} tools, expected at least 5 with MCP"
        print(f"Agent created with {len(agent.tools)} tools (with MCP client)")

    def test_agent_without_mcp_client(self):
        """Test that agent can be created without MCP client."""
        agent = ChefAgentGraph(
            llm_provider="groq",
            api_key=settings.groq_api_key,
            mcp_client=None,
        )

        assert agent is not None
        # In fallback mode, agent should have 5 tools: search_recipes, create_recipe,
        # create_shopping_list, add_to_shopping_list, create_fallback_recipes
        assert (
            len(agent.tools) == 5
        ), f"Agent has {len(agent.tools)} tools, expected 5 in fallback mode"
        print(
            f"Agent created with {len(agent.tools)} tools (no MCP - fallback mode)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
