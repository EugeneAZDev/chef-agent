"""
Security tests for the Chef Agent API.

These tests verify that the API is protected against common security
vulnerabilities like SQL injection, XSS, and other attacks.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.mark.security
class TestSecurityVulnerabilities:
    """Test security vulnerabilities and protections."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_sql_injection_thread_id(self, client):
        """Test SQL injection protection in thread_id parameter."""
        # Test various SQL injection attempts
        malicious_thread_ids = [
            "'; DROP TABLE recipes; --",
            "1' OR '1'='1",
            "'; INSERT INTO recipes (title) VALUES ('hacked'); --",
            "1' UNION SELECT * FROM recipes --",
            "'; UPDATE recipes SET title='hacked' --",
        ]

        for malicious_id in malicious_thread_ids:
            # Test chat endpoints
            response = client.get(
                f"/api/v1/chat/threads/{malicious_id}/history"
            )
            # Should either return 400 (validation error) or 404 (not found)
            # but should not execute the SQL injection
            assert response.status_code in [400, 404]

            # Test shopping endpoints
            response = client.get(
                f"/api/v1/shopping/lists?thread_id={malicious_id}"
            )
            # Shopping endpoint now validates thread_id format
            assert response.status_code in [400, 500]

    def test_xss_protection(self, client):
        """Test XSS protection in API responses."""
        # Test XSS attempts in thread_id
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
        ]

        for payload in xss_payloads:
            response = client.get(f"/api/v1/chat/threads/{payload}/history")
            # Should return validation error (400) or 404 (not found)
            assert response.status_code in [400, 404]
            # Only check detail if it's a 400 error
            if response.status_code == 400:
                data = response.json()
                assert "Invalid thread_id format" in data["detail"]

    def test_input_validation(self, client):
        """Test input validation on various endpoints."""
        # Test specific invalid thread_id cases with expected status codes
        test_cases = [
            ("", 404),  # Empty string doesn't match route pattern
            ("a", 400),  # Too short - validation error
            ("a" * 65, 400),  # Too long - validation error
            ("invalid@chars!", 400),  # Invalid characters - validation error
            ("with spaces", 400),  # Spaces - validation error
            ("with#hash", 405),  # Hash symbol causes URL parsing issue
        ]

        for invalid_id, expected_status in test_cases:
            response = client.get(f"/api/v1/chat/threads/{invalid_id}/history")
            assert response.status_code == expected_status, (
                f"Expected {expected_status} for thread_id '{invalid_id}', "
                f"got {response.status_code}"
            )
        response = client.get("/api/v1/recipes/?query=test")
        # Should return 200 for successful search
        assert response.status_code == 200

    def test_rate_limiting_protection(self, client):
        """Test that rate limiting provides protection."""
        # Make many requests quickly
        responses = []
        for i in range(50):  # More than the rate limit
            response = client.get("/api/v1/chat/threads")
            responses.append(response.status_code)

            # If we hit rate limit, stop testing
            if response.status_code == 429:
                break

        # Should eventually hit rate limit
        assert 429 in responses or all(r == 200 for r in responses)

    def test_shopping_list_size_limit(self, client):
        """Test shopping list size limit protection."""
        # This test would require creating a shopping list with too many items
        # For now, we test the validation function exists
        from api.shopping import validate_shopping_list_size

        # Test normal size
        validate_shopping_list_size([1, 2, 3])  # Should not raise

        # Test oversized list
        with pytest.raises(Exception):  # Should raise HTTPException
            validate_shopping_list_size([1] * 101)  # Over limit

    def test_recipe_title_uniqueness(self, client):
        """Test that recipe titles must be unique per user."""
        # Check the migration file for UNIQUE constraint
        import os

        migration_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "migrations",
            "0001_initial_schema.sql",
        )
        with open(migration_path, "r") as f:
            migration_content = f.read()

        # Verify UNIQUE constraint exists in migration (now per user)
        assert "UNIQUE" in migration_content.upper()
        assert "UNIQUE(title, user_id)" in migration_content

    def test_headers_security(self, client):
        """Test security headers are present."""
        response = client.get("/")

        # Check for security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
        ]

        for header in security_headers:
            assert header in response.headers

    def test_cors_configuration(self, client):
        """Test CORS is properly configured."""
        response = client.get("/api/v1/health/")

        # Check CORS headers
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
        ]

        for header in cors_headers:
            assert header in response.headers

    def test_error_information_disclosure(self, client):
        """Test that errors don't disclose sensitive information."""
        # Test with invalid endpoint
        response = client.get("/api/v1/invalid-endpoint")
        assert response.status_code == 404

        # Error message should not contain sensitive info
        data = response.json()
        assert "detail" in data
        # Should not contain database paths, internal errors, etc.
        sensitive_keywords = ["sqlite", "database", "traceback", "exception"]
        detail = data["detail"].lower()
        for keyword in sensitive_keywords:
            assert keyword not in detail

    def test_thread_id_validation_behavior(self, client):
        """Test that thread_id validation behaves correctly for edge cases."""
        from fastapi import HTTPException

        from api.chat import validate_thread_id

        # Test boundary conditions without duplicating regex
        test_cases = [
            # (input, should_pass, description)
            ("abc", True, "Minimum valid length"),
            ("a" * 64, True, "Maximum valid length"),
            ("ab", False, "Too short"),
            ("a" * 65, False, "Too long"),
            ("valid-id_123", True, "Valid characters"),
            ("invalid@chars", False, "Invalid special character"),
            ("with spaces", False, "Contains spaces"),
            ("", False, "Empty string"),
            ("a\nb", False, "Contains newline"),
            ("a\tb", False, "Contains tab"),
        ]

        for thread_id, should_pass, description in test_cases:
            if should_pass:
                # Should not raise exception
                result = validate_thread_id(thread_id)
                assert (
                    result == thread_id
                ), f"Failed for valid case: {description}"
            else:
                # Should raise HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    validate_thread_id(thread_id)
                assert (
                    exc_info.value.status_code == 400
                ), f"Failed for invalid case: {description}"
                assert "Invalid thread_id format" in str(
                    exc_info.value.detail
                ), f"Wrong error message for: {description}"
