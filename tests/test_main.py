from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint returns proper API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    # Verify API information structure
    assert data["message"] == "Chef Agent API"
    assert data["version"] == "1.0.0"
    assert "docs" in data
    assert "health" in data
    assert "chat" in data
    assert "recipes" in data
    assert "shopping" in data

    # Verify all endpoints are accessible
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health/"
    assert data["chat"] == "/api/v1/chat/"
    assert data["recipes"] == "/api/v1/recipes/"
    assert data["shopping"] == "/api/v1/shopping/"


def test_database_status():
    """Test database status endpoint."""
    response = client.get("/db/status")
    assert response.status_code == 200
    data = response.json()

    # Verify database status structure
    assert "status" in data
    assert "database_path" in data
    assert "recipes_count" in data
    assert "shopping_lists_count" in data
    assert data["status"] in ["connected", "error"]
    assert isinstance(data["recipes_count"], int)
    assert isinstance(data["shopping_lists_count"], int)


def test_health_check():
    """Test the basic health check endpoint."""
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()

    # Basic response structure
    assert data["status"] == "healthy"
    assert data["service"] == "chef-agent-api"
    assert data["version"] == "1.0.0"
    assert "message" in data


def test_detailed_health_check():
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    data = response.json()

    # Basic response structure
    assert data["status"] in [
        "healthy",
        "degraded",
    ]  # May be degraded in tests
    assert data["service"] == "chef-agent-api"
    assert data["version"] == "1.0.0"
    assert "checks" in data

    # Check that database connectivity is tested
    assert "database" in data["checks"]
    assert "status" in data["checks"]["database"]

    # Check that configuration is tested
    assert "configuration" in data["checks"]
    assert "status" in data["checks"]["configuration"]

    # Check that memory is tested
    assert "memory" in data["checks"]
    assert "status" in data["checks"]["memory"]
