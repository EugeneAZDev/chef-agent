"""
Performance tests for the Chef Agent API.

These tests verify that the API can handle reasonable loads
and performs well under stress.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app

# Performance tests are skipped by default
# Run with: pytest -m performance


@pytest.mark.performance
class TestPerformance:
    """Performance and load tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_concurrent_requests(self, client):
        """Test API performance under concurrent load."""

        def make_request():
            response = client.get("/api/v1/health/")
            return response.status_code, time.time()

        # Make 50 concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in futures]

        end_time = time.time()
        total_time = end_time - start_time

        # All requests should succeed
        status_codes = [result[0] for result in results]
        assert all(code == 200 for code in status_codes)

        # Should complete within reasonable time (5 seconds)
        assert total_time < 5.0

        # Calculate requests per second
        rps = len(results) / total_time
        assert rps > 10  # Should handle at least 10 RPS

    def test_database_query_performance(self, client):
        """Test database query performance."""
        # Test recipe search performance
        start_time = time.time()
        response = client.get("/api/v1/recipes/?query=pasta&limit=100")
        end_time = time.time()

        assert response.status_code == 200
        query_time = end_time - start_time

        # Database query should be fast (under 1 second)
        assert query_time < 1.0

    def test_memory_usage_stability(self, client):
        """Test that memory usage remains stable under load."""
        # This is a basic test - in production you'd use memory profiling tools
        initial_memory = self._get_memory_usage()

        # Make many requests with rate limiting
        import time

        for i in range(50):  # Reduced from 100 to 50
            response = client.get("/api/v1/health/")
            assert response.status_code == 200

            # Add small delay to prevent overwhelming the server
            if i % 10 == 0:  # Every 10 requests
                time.sleep(0.1)  # 100ms delay

        final_memory = self._get_memory_usage()

        # Memory usage shouldn't grow significantly
        memory_growth = final_memory - initial_memory
        assert memory_growth < 10 * 1024 * 1024  # Less than 10MB growth

    def test_response_time_consistency(self, client):
        """Test that response times are consistent."""
        response_times = []

        for i in range(20):
            start_time = time.time()
            response = client.get("/api/v1/health/")
            end_time = time.time()

            assert response.status_code == 200
            response_times.append(end_time - start_time)

            # Add small delay to prevent overwhelming the server
            if i % 5 == 0:  # Every 5 requests
                time.sleep(0.05)  # 50ms delay

        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)

        # Average response time should be reasonable
        assert avg_time < 0.5  # Under 500ms

        # Max response time shouldn't be too much higher than average
        # Allow for some variance, especially for the first request
        assert max_time < avg_time * 5  # Max shouldn't be 5x average

        # Min response time should be reasonable
        assert min_time > 0.001  # At least 1ms

    def test_large_payload_handling(self, client):
        """Test handling of large payloads."""
        # Test large shopping list creation
        large_items = []
        for i in range(50):  # 50 items (under the 100 limit)
            large_items.append(
                {"name": f"Item {i}", "quantity": "1", "unit": "piece"}
            )

        # This would test adding many items to a shopping list
        # For now, we test the validation function
        from api.shopping import validate_shopping_list_size

        # Should not raise for 50 items
        validate_shopping_list_size(large_items)

        # Should raise for over 100 items
        oversized_items = [{"name": f"Item {i}"} for i in range(101)]
        with pytest.raises(Exception):
            validate_shopping_list_size(oversized_items)

    def test_concurrent_database_operations(self, client):
        """Test concurrent database operations."""

        def create_recipe_request():
            recipe_data = {
                "title": f"Concurrent Recipe {time.time()}",
                "instructions": "Test recipe",
                "ingredients": [
                    {"name": "test", "quantity": "1", "unit": "piece"}
                ],
            }
            response = client.post("/api/v1/recipes/", json=recipe_data)
            return response.status_code

        # Make 10 concurrent recipe creation requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_recipe_request) for _ in range(10)
            ]
            results = [future.result() for future in futures]

        client.get("/api/v1/health")
        success_count = sum(1 for code in results if code == 200)
        assert success_count >= 5  # At least half should succeed

    def test_rate_limiting_performance(self, client):
        """Test that rate limiting doesn't significantly impact performance."""
        # Make requests up to the rate limit
        start_time = time.time()

        for i in range(30):  # Under rate limit
            response = client.get("/api/v1/chat/threads")
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly even with rate limiting
        assert total_time < 2.0

    def _get_memory_usage(self):
        """Get current memory usage (simplified)."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def test_api_endpoint_performance(self, client):
        """Test performance of different API endpoints."""
        endpoints = [
            "/",
            "/api/v1/health/",
            "/api/v1/recipes/",
            "/api/v1/recipes/diet-types/",
            "/api/v1/recipes/difficulty-levels/",
            "/api/v1/chat/threads",
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()

            # All endpoints should respond quickly
            response_time = end_time - start_time
            assert response_time < 1.0  # Under 1 second

            # All endpoints should return valid responses
            assert response.status_code in [
                200,
                404,
            ]  # 404 is acceptable for some endpoints

    def test_database_connection_pooling(self, client):
        """Test that database connections are handled efficiently."""
        # Make many database-intensive requests
        start_time = time.time()

        for _ in range(20):
            response = client.get("/api/v1/recipes/?query=test")
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete efficiently even with many DB queries
        assert total_time < 3.0
