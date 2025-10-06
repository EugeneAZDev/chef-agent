"""
Chef Agent FastAPI application.

This is the main entry point for the Chef Agent API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.db import Database
from api.limiter import rate_limit_middleware
from api.middleware import LoggingMiddleware, SecurityHeadersMiddleware

# Global database instance
db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for database initialization."""
    # Database is initialized via migrations in Dockerfile
    # or manually via: poetry run python -m scripts.migrate
    print("Chef Agent API started successfully")

    yield

    # Cleanup on shutdown
    db.close()
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


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Chef Agent API", "version": "1.0.0"}


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Chef Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
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
