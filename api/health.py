"""
Health check API endpoints.

This module provides health check and system status endpoints
for monitoring and diagnostics.
"""

import logging
from sqlite3 import OperationalError
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from adapters.db.database import Database
from config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Basic health check",
    description="Check if the API is running and responsive",
)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns basic system information and status.
    """
    return {
        "status": "healthy",
        "service": "chef-agent-api",
        "version": "1.0.0",
        "message": "Chef Agent API is running",
    }


@router.get(
    "/detailed",
    response_model=Dict[str, Any],
    summary="Detailed health check",
    description="Comprehensive health check including database and dependencies",
)
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint.

    Returns comprehensive system status including:
    - API status
    - Database connectivity
    - Memory usage
    - Configuration status
    """
    health_status = {
        "status": "healthy",
        "service": "chef-agent-api",
        "version": "1.0.0",
        "checks": {},
    }

    # Check database connectivity
    try:
        db = Database(settings.sqlite_db)
        conn = db.get_connection()

        # Test database query
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recipes")
        recipe_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM shopping_lists")
        shopping_list_count = cursor.fetchone()[0]

        health_status["checks"]["database"] = {
            "status": "healthy",
            "recipe_count": recipe_count,
            "shopping_list_count": shopping_list_count,
        }

        db.close()

    except OperationalError as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    except Exception as e:
        logger.error(f"Unexpected error during database health check: {e}")
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    # Check configuration
    try:
        config_checks = {
            "groq_configured": bool(settings.groq_api_key),
            "openai_configured": bool(
                getattr(settings, "openai_api_key", None)
            ),
            "redis_configured": bool(settings.redis_url),
            "debug_mode": settings.debug,
        }

        health_status["checks"]["configuration"] = {
            "status": "healthy",
            "details": config_checks,
        }

    except Exception as e:
        logger.error(f"Configuration health check failed: {e}")
        health_status["checks"]["configuration"] = {
            "status": "error",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    # Check memory usage
    try:
        import psutil

        memory = psutil.virtual_memory()
        health_status["checks"]["memory"] = {
            "status": "healthy",
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent,
        }

    except ImportError:
        health_status["checks"]["memory"] = {
            "status": "unknown",
            "message": "psutil not available",
        }

    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        health_status["checks"]["memory"] = {
            "status": "error",
            "error": str(e),
        }

    return health_status


@router.get(
    "/ready",
    response_model=Dict[str, Any],
    summary="Readiness check",
    description="Check if the service is ready to accept requests",
)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Verifies that all critical services are available
    and the API is ready to handle requests.
    """
    try:
        # Check database connectivity
        db = Database(settings.sqlite_db)
        db.connect()
        db.close()

        # Check if at least one LLM provider is configured
        llm_configured = (
            bool(settings.GROQ_API_KEY)
            or bool(settings.OPENAI_API_KEY)
            or bool(settings.OLLAMA_BASE_URL)
        )

        if not llm_configured:
            raise HTTPException(
                status_code=503, detail="No LLM provider configured"
            )

        return {
            "status": "ready",
            "message": "Service is ready to accept requests",
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503, detail=f"Service not ready: {str(e)}"
        )
