"""
Test diet goal extraction directly.
"""

import pytest

from adapters.mcp.http_client import ChefAgentHTTPMCPClient
from agent.graph import ChefAgentGraph
from config import settings


class TestDietGoalExtraction:
    """Test diet goal extraction functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = ChefAgentHTTPMCPClient()
        self.agent = ChefAgentGraph(
            llm_provider="groq",
            api_key=settings.groq_api_key,
            mcp_client=self.mcp_client,
        )

    def test_extract_diet_goal_vegetarian(self):
        """Test that vegetarian is extracted correctly."""
        result = self.agent._extract_diet_goal("vegetarian")
        assert result == "vegetarian"

    def test_extract_diet_goal_traditional(self):
        """Test that traditional is extracted correctly."""
        result = self.agent._extract_diet_goal("traditional ukrainian cooking")
        assert result == "traditional"

    def test_extract_diet_goal_regular(self):
        """Test that regular is extracted correctly."""
        result = self.agent._extract_diet_goal("regular diet")
        assert result == "regular"

    def test_extract_diet_goal_keto(self):
        """Test that keto is extracted correctly."""
        result = self.agent._extract_diet_goal("keto diet")
        assert result == "keto"

    def test_extract_diet_goal_no_match(self):
        """Test that no diet is extracted when no keywords match."""
        result = self.agent._extract_diet_goal("hello world")
        assert result is None

    def test_extract_diet_goal_case_insensitive(self):
        """Test that extraction is case insensitive."""
        result = self.agent._extract_diet_goal("VEGETARIAN")
        assert result == "vegetarian"

    def test_extract_diet_goal_partial_match(self):
        """Test that partial matches work."""
        result = self.agent._extract_diet_goal("I want vegetarian food")
        assert result == "vegetarian"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
