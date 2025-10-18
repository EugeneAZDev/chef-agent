#!/usr/bin/env python3
"""Test script for agent creation."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after path modification
from adapters.mcp.http_client import ChefAgentHTTPMCPClient  # noqa: E402
from agent import ChefAgentGraph  # noqa: E402
from agent.models import ChatRequest  # noqa: E402


async def test_agent_creation():
    """Test agent creation."""
    print("Testing agent creation...")

    try:
        # Test 1: Create MCP client
        print("1. Creating MCP client...")
        mcp_client = ChefAgentHTTPMCPClient()
        print("✅ MCP client created successfully")

        # Test 2: Create agent without MCP client
        print("\n2. Creating agent without MCP client...")
        agent_no_mcp = ChefAgentGraph(
            llm_provider="groq", api_key="test-key", mcp_client=None
        )
        print("✅ Agent without MCP created successfully")

        # Test 3: Create agent with MCP client
        print("\n3. Creating agent with MCP client...")
        agent_with_mcp = ChefAgentGraph(
            llm_provider="groq", api_key="test-key", mcp_client=mcp_client
        )
        print("✅ Agent with MCP created successfully")

        # Test 4: Test simple chat request
        print("\n4. Testing simple chat request...")
        request = ChatRequest(
            thread_id="test-thread", message="Hello!", language="en"
        )

        # This might fail, but let's see what happens
        try:
            response = await agent_with_mcp.process_request(request)
            print(f"✅ Chat request successful: {response.message[:100]}...")
        except Exception as e:
            print(f"❌ Chat request failed: {e}")
            import traceback

            traceback.print_exc()

        print("\n✅ All tests completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if "mcp_client" in locals():
            await mcp_client.close()


if __name__ == "__main__":
    asyncio.run(test_agent_creation())
