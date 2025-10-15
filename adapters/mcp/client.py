"""
MCP client for Chef Agent.

This client provides a simple interface to interact with the MCP server
and use the available tools.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


class ChefAgentMCPClient:
    """Client for Chef Agent MCP server."""

    def __init__(self, timeout: int = 30):
        """Initialize the MCP client."""
        self.session: Optional[ClientSession] = None
        self.timeout = min(timeout, 10)  # Cap at 10 seconds for better UX

    async def connect(self):
        """Connect to the MCP server."""
        async with stdio_client() as (read, write):
            self.session = ClientSession(read, write)
            await self.session.initialize()

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.close()

    async def find_recipes(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        diet_type: Optional[str] = None,
        max_prep_time: Optional[int] = None,
        max_cook_time: Optional[int] = None,
        servings: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Find recipes using the recipe_finder tool."""
        if not self.session:
            raise RuntimeError("Client not connected. Call connect() first.")

        arguments = {}
        if query:
            arguments["query"] = query
        if tags:
            arguments["tags"] = tags
        if diet_type:
            arguments["diet_type"] = diet_type
        if max_prep_time is not None:
            arguments["max_prep_time"] = max_prep_time
        if max_cook_time is not None:
            arguments["max_cook_time"] = max_cook_time
        if servings is not None:
            arguments["servings"] = servings

        try:
            result = await asyncio.wait_for(
                self.session.call_tool("recipe_finder", arguments),
                timeout=self.timeout,
            )
            return json.loads(result[0].text)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Recipe search timed out after {self.timeout} seconds"
            )

    async def manage_shopping_list(
        self,
        action: str,
        thread_id: str,
        items: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Manage shopping list using the shopping_list_manager tool."""
        if not self.session:
            raise RuntimeError("Client not connected. Call connect() first.")

        arguments = {"action": action, "thread_id": thread_id}

        if items:
            arguments["items"] = items

        try:
            result = await asyncio.wait_for(
                self.session.call_tool("shopping_list_manager", arguments),
                timeout=self.timeout,
            )
            return json.loads(result[0].text)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Shopping list operation timed out after "
                f"{self.timeout} seconds"
            )

    async def create_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Create a new shopping list."""
        return await self.manage_shopping_list("create", thread_id)

    async def get_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Get existing shopping list."""
        return await self.manage_shopping_list("get", thread_id)

    async def add_to_shopping_list(
        self, thread_id: str, items: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Add items to shopping list."""
        return await self.manage_shopping_list("add_items", thread_id, items)

    async def clear_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Clear shopping list."""
        return await self.manage_shopping_list("clear", thread_id)

    async def delete_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Delete shopping list."""
        return await self.manage_shopping_list("delete", thread_id)


# Example usage
async def main():
    """Example usage of the MCP client."""
    client = ChefAgentMCPClient()

    try:
        await client.connect()

        # Find recipes
        print("Finding recipes...")
        recipes = await client.find_recipes(
            query="pasta", tags=["italian"], max_prep_time=30
        )
        print(f"Found {recipes['total_found']} recipes")

        # Manage shopping list
        print("\nManaging shopping list...")
        thread_id = "test-thread-123"

        # Create shopping list
        result = await client.create_shopping_list(thread_id)
        print(f"Created shopping list: {result}")

        # Add items
        items = [
            {
                "name": "pasta",
                "quantity": "500g",
                "unit": "g",
                "category": "pantry",
            },
            {
                "name": "tomatoes",
                "quantity": "4",
                "unit": "pieces",
                "category": "vegetables",
            },
        ]
        result = await client.add_to_shopping_list(thread_id, items)
        print(f"Added items: {result}")

        # Get shopping list
        result = await client.get_shopping_list(thread_id)
        print(f"Shopping list: {result}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
