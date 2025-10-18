"""
HTTP-based MCP client for Chef Agent.

This client provides a simple interface to interact with the HTTP MCP server
and use the available tools.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx


class ChefAgentHTTPMCPClient:
    """HTTP client for Chef Agent MCP server."""

    def __init__(
        self, base_url: str = "http://localhost:8002", timeout: int = 30
    ):
        """Initialize the HTTP MCP client."""
        self.base_url = base_url
        # Cap at 10 seconds for better UX
        self.timeout = min(timeout, 10)
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def find_recipes(
        self,
        query: str = "",
        diet_type: Optional[str] = None,
        max_prep_time: Optional[int] = None,
        servings: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Find recipes based on criteria."""
        try:
            data = {
                "query": query,
                "diet_type": diet_type,
                "max_prep_time": max_prep_time,
                "servings": servings,
                "limit": limit,
            }

            response = await self.client.post(
                f"{self.base_url}/tools/recipe_finder", json=data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recipes": [],
                "total_found": 0,
            }

    async def create_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Create a new shopping list."""
        try:
            data = {
                "action": "create",
                "thread_id": thread_id,
            }

            response = await self.client.post(
                f"{self.base_url}/tools/shopping_list_manager", json=data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def add_to_shopping_list(
        self, thread_id: str, items: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Add items to shopping list."""
        try:
            data = {
                "action": "add",
                "thread_id": thread_id,
                "items": items,
            }

            response = await self.client.post(
                f"{self.base_url}/tools/shopping_list_manager", json=data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def get_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Get shopping list."""
        try:
            data = {
                "action": "get",
                "thread_id": thread_id,
            }

            response = await self.client.post(
                f"{self.base_url}/tools/shopping_list_manager", json=data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def clear_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Clear shopping list."""
        try:
            data = {
                "action": "clear",
                "thread_id": thread_id,
            }

            response = await self.client.post(
                f"{self.base_url}/tools/shopping_list_manager", json=data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def delete_shopping_list(self, thread_id: str) -> Dict[str, Any]:
        """Delete shopping list."""
        try:
            data = {
                "action": "delete",
                "thread_id": thread_id,
            }

            response = await self.client.post(
                f"{self.base_url}/tools/shopping_list_manager", json=data
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Example usage
async def main():
    """Example usage of the HTTP MCP client."""
    client = ChefAgentHTTPMCPClient()

    try:
        # Find recipes
        print("Finding recipes...")
        recipes = await client.find_recipes(
            query="pasta", diet_type="vegetarian", limit=3
        )
        print(f"Found {recipes.get('total_found', 0)} recipes")

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
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
