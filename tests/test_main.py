from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Chef Agent API"
    assert data["version"] == "1.0.0"
    assert "docs" in data
    assert "health" in data


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
