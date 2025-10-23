"""
Integration test for Chef Agent API endpoints.

This test verifies that the API endpoints work correctly
and don't get stuck in generic responses.
"""

# requests not used
import time

import pytest


@pytest.mark.integration
class TestChefAgentAPI:
    """Test Chef Agent API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:8070"
        self.test_thread_id = f"test_{int(time.time())}"
        self.test_user_id = f"user_{int(time.time())}"

    def test_simple_chat_endpoint(self, test_server):
        """Test that simple chat endpoint works."""
        response = test_server.post(
            "/api/v1/chat/simple-chat",
            json={
                "message": "vegetarian",
                "thread_id": self.test_thread_id,
                "user_id": self.test_user_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "thread_id" in data
        print(f"Simple chat response: {data['message']}")

    def test_message_endpoint_with_vegetarian(self, test_server):
        """Test that message endpoint works with vegetarian diet."""
        response = test_server.post(
            "/api/v1/chat/message",
            json={
                "message": "vegetarian",
                "thread_id": self.test_thread_id,
                "user_id": self.test_user_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "thread_id" in data

        # This should FAIL if agent returns generic message
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in data["message"]
        ), f"Agent returned generic message: {data['message']}"

        print(f"Message endpoint response: {data['message']}")

    def test_message_endpoint_with_traditional(self, test_server):
        """Test that message endpoint works with traditional diet."""
        response = test_server.post(
            "/api/v1/chat/message",
            json={
                "message": "traditional ukrainian cooking",
                "thread_id": f"{self.test_thread_id}_2",
                "user_id": self.test_user_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # This should FAIL if agent returns generic message
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in data["message"]
        ), f"Agent returned generic message: {data['message']}"

        print(f"Traditional diet response: {data['message']}")

    def test_message_endpoint_with_days(self, test_server):
        """Test that message endpoint works with diet and days."""
        response = test_server.post(
            "/api/v1/chat/message",
            json={
                "message": "vegetarian for 3 days",
                "thread_id": f"{self.test_thread_id}_3",
                "user_id": self.test_user_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # This should FAIL if agent returns generic message
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert (
            generic_message not in data["message"]
        ), f"Agent returned generic message: {data['message']}"

        print(f"Diet + days response: {data['message']}")

    def test_agent_state_persistence(self, test_server):
        """Test that agent state persists across messages."""
        thread_id = f"{self.test_thread_id}_persistence"

        # First message - should set diet goal
        response1 = test_server.post(
            "/api/v1/chat/message",
            json={
                "message": "vegetarian",
                "thread_id": thread_id,
                "user_id": self.test_user_id,
            },
        )

        assert response1.status_code == 200
        data1 = response1.json()
        print(f"First message response: {data1['message']}")

        # Second message - should ask for days
        response2 = test_server.post(
            "/api/v1/chat/message",
            json={
                "message": "3 days",
                "thread_id": thread_id,
                "user_id": self.test_user_id,
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()
        print(f"Second message response: {data2['message']}")

        # Should not return generic message on second call
        generic_message = (
            "I'm here to help you plan your meals! Please tell me about "
            "your dietary goals"
        )
        assert generic_message not in data2["message"], (
            f"Agent returned generic message on second call: "
            f"{data2['message']}"
        )

    def test_agent_creates_recipes_and_shopping_lists(self, test_server):
        """Test that agent creates recipes and shopping lists."""
        thread_id = f"{self.test_thread_id}_creation"

        # Send complete request
        response = test_server.post(
            "/api/v1/chat/message",
            json={
                "message": "vegetarian for 3 days",
                "thread_id": thread_id,
                "user_id": self.test_user_id,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check if agent created meal plan or shopping list
        has_meal_plan = data.get("menu_plan") is not None
        has_shopping_list = data.get("shopping_list") is not None

        print(f"Response: {data['message']}")
        print(f"Has meal plan: {has_meal_plan}")
        print(f"Has shopping list: {has_shopping_list}")

        # At least one should be created
        assert (
            has_meal_plan or has_shopping_list
        ), "Agent should create either meal plan or shopping list"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
