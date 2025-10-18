"""
Chef Agent FastAPI application.

This is the main entry point for the Chef Agent API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.db import Database
from api import chat_router, health_router, recipes_router, shopping_router
from api.limiter import rate_limit_middleware
from api.middleware import LoggingMiddleware, SecurityHeadersMiddleware


def validate_environment():
    """Validate required environment variables."""
    # Skip validation during testing
    import sys

    if any("pytest" in arg for arg in sys.argv):
        return

    from config import settings

    if not settings.groq_api_key:
        raise EnvironmentError(
            "Missing required environment variable: GROQ_API_KEY"
        )


# Global database instance
db = Database()

# Validate environment after settings are loaded
validate_environment()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database initialization."""
    # Database is initialized via migrations in Dockerfile
    # or manually via: poetry run python -m scripts.migrate
    print("Chef Agent API started successfully")

    yield

    # Cleanup on shutdown - close MCP clients first, then database
    try:
        # Close any active MCP connections
        from api.chat import _agent

        if _agent and hasattr(_agent, "mcp_client"):
            await _agent.mcp_client.disconnect()
    except Exception as e:
        print(f"Error closing MCP client: {e}")

    # Close database connections
    try:
        db.close()
    except Exception as e:
        print(f"Error closing database: {e}")

    print("Chef Agent API stopped")


app = FastAPI(
    title="Chef Agent API",
    description="AI-powered meal planning and shopping list management",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8501",
    ],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

# Add rate limiting
app.middleware("http")(rate_limit_middleware)

# Include API routers
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(recipes_router)
app.include_router(shopping_router)


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Chef Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health/",
        "chat": "/api/v1/chat/",
        "recipes": "/api/v1/recipes/",
        "shopping": "/api/v1/shopping/",
    }


@app.get("/db/status")
def database_status():
    """Check database connection status."""
    try:
        conn = db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) as count FROM recipes")
        recipe_count = cursor.fetchone()["count"]

        cursor = conn.execute("SELECT COUNT(*) as count FROM shopping_lists")
        list_count = cursor.fetchone()["count"]

        return {
            "status": "connected",
            "database_path": db.db_path,
            "recipes_count": recipe_count,
            "shopping_lists_count": list_count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
