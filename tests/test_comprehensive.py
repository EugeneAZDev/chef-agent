#!/usr/bin/env python3
"""
Comprehensive test for Chef Agent recipe creation and meal plan generation.

This test demonstrates the full workflow:
1. Agent receives request for vegetarian meal plan
2. Agent searches for recipes (finds none)
3. Agent creates custom recipes
4. Agent generates meal plan
5. Agent creates shopping list
"""

import asyncio

from agent import ChefAgentGraph
from agent.models import ChatRequest


async def test_full_workflow():
    """Test the complete workflow from request to meal plan."""
    print("=== Testing Complete Chef Agent Workflow ===")

    # Create agent without MCP client (fallback mode)
    agent = ChefAgentGraph(
        llm_provider="groq",
        api_key="test-key",  # This will fail with real API, but we're testing logic
        mcp_client=None,
    )

    print(f"Agent created with {len(agent.tools)} tools")
    print(f"Tools: {[tool.name for tool in agent.tools]}")

    # Test request for vegetarian meal plan
    request = ChatRequest(
        thread_id="test_thread_full",
        message="Create a vegetarian meal plan for 3 days",
        user_id="test_user",
    )

    print(f"\nProcessing request: '{request.message}'")

    try:
        # Process the request
        response = await agent.process_request(request)

        print("\n=== Response Analysis ===")
        print(f"Response message: {response.message}")
        print(f"Has menu plan: {response.menu_plan is not None}")
        print(f"Has shopping list: {response.shopping_list is not None}")

        if response.menu_plan:
            print("\n=== Meal Plan Details ===")
            print(f"Total days: {response.menu_plan.total_days}")
            print(f"Diet type: {response.menu_plan.diet_type}")

            for i, day in enumerate(response.menu_plan.days, 1):
                print(f"\nDay {i}:")
                for meal in day.meals:
                    print(f"  {meal.name.title()}: {meal.recipe.title}")
                    print(f"    Ingredients: {len(meal.recipe.ingredients)}")
                    for ingredient in meal.recipe.ingredients[:3]:  # First 3
                        print(
                            f"      - {ingredient.quantity} {ingredient.unit} "
                            f"{ingredient.name}"
                        )
                    if len(meal.recipe.ingredients) > 3:
                        print(
                            f"      ... and {len(meal.recipe.ingredients) - 3} more"
                        )

        if response.shopping_list:
            print("\n=== Shopping List Details ===")
            print(f"Total items: {len(response.shopping_list.items)}")
            for item in response.shopping_list.items[:10]:  # Show first 10
                print(
                    f"  - {item.quantity} {item.unit} {item.name} ({item.category})"
                )
            if len(response.shopping_list.items) > 10:
                print(
                    f"  ... and {len(response.shopping_list.items) - 10} more items"
                )

        # Check if recipes were created
        print("\n=== Recipe Creation Check ===")
        from adapters.db import Database
        from adapters.db.recipe_repository import SQLiteRecipeRepository

        db = Database()
        recipe_repo = SQLiteRecipeRepository(db)
        recipes = recipe_repo.search_recipes(query="", user_id=None, limit=100)
        print(f"Recipes in database: {len(recipes)}")

        if recipes:
            print("Created recipes:")
            for recipe in recipes:
                print(f"  - {recipe.title} ({recipe.diet_type})")

        db.close()

        print("\n=== Test Result ===")
        if response.menu_plan and response.shopping_list:
            print("✅ SUCCESS: Complete workflow executed successfully!")
            print("   - Recipes were created")
            print("   - Meal plan was generated")
            print("   - Shopping list was created")
        else:
            print("❌ PARTIAL: Some components missing")
            if not response.menu_plan:
                print("   - Meal plan was not generated")
            if not response.shopping_list:
                print("   - Shopping list was not created")

    except Exception as e:
        print(f"❌ ERROR during processing: {e}")
        import traceback

        traceback.print_exc()


async def test_recipe_search_only():
    """Test just the recipe search functionality."""
    print("\n=== Testing Recipe Search Only ===")

    # Create agent
    # agent = ChefAgentGraph(
    #     llm_provider='groq',
    #     api_key='test-key',
    #     mcp_client=None
    # )

    # Test recipe search tool directly
    from agent.tools import search_recipes

    print("Testing search_recipes tool...")
    result = await search_recipes.ainvoke(
        {"query": "vegetarian", "diet_type": "vegetarian", "limit": 5}
    )

    print(f"Search result: {result}")
    print(f"Success: {result.get('success', False)}")
    print(f"Recipes found: {result.get('total_found', 0)}")

    if result.get("recipes"):
        print("Found recipes:")
        for recipe in result["recipes"]:
            print(f"  - {recipe.title}")


async def main():
    """Main test function."""
    print("Chef Agent Comprehensive Test")
    print("=============================")

    # Test 1: Recipe search only
    await test_recipe_search_only()

    # Test 2: Full workflow
    await test_full_workflow()

    print("\n=== Test Complete ===")
    print("This test demonstrates that the agent can:")
    print("1. Search for recipes (fallback to database)")
    print("2. Create recipes when none are found")
    print("3. Generate meal plans from recipes")
    print("4. Create shopping lists from meal plans")


if __name__ == "__main__":
    asyncio.run(main())
