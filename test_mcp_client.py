#!/usr/bin/env python3
"""Test script for HTTP MCP client."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after path modification
from adapters.mcp.http_client import ChefAgentHTTPMCPClient  # noqa: E402


async def test_mcp_client():
    """Test the HTTP MCP client."""
    print("Testing HTTP MCP client...")

    client = ChefAgentHTTPMCPClient()

    try:
        # Test health check
        print("1. Testing health check...")
        response = await client.client.get("http://localhost:8072/health")
        print(f"Health check: {response.status_code} - {response.json()}")

        # Test recipe finder
        print("\n2. Testing recipe finder...")
        recipes = await client.find_recipes(
            query="pasta", diet_type="vegetarian", limit=3
        )
        print(f"Recipe finder: {recipes}")

        # Test shopping list
        print("\n3. Testing shopping list...")
        thread_id = "test-thread-123"

        # Create shopping list
        result = await client.create_shopping_list(thread_id)
        print(f"Create shopping list: {result}")

        # Add items
        items = [
            {
                "name": "pasta",
                "quantity": "500",
                "unit": "g",
                "category": "pantry",
            }
        ]
        result = await client.add_to_shopping_list(thread_id, items)
        print(f"Add items: {result}")

        # Get shopping list
        result = await client.get_shopping_list(thread_id)
        print(f"Get shopping list: {result}")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
