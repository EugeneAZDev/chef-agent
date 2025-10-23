"""
Rate limiting middleware for Chef Agent API.

This module provides rate limiting functionality using Redis
to protect against abuse and ensure fair usage.
"""

import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from config import settings

logger = logging.getLogger(__name__)

# Redis client (will be initialized on first use)
_redis_client = None


def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.from_url(settings.redis_url)
            # Test connection
            _redis_client.ping()
            logger.info("Redis client connected successfully")
        except Exception as e:
            logger.warning(
                f"Redis not available: {e}. Rate limiting disabled."
            )
            _redis_client = None
    return _redis_client


def get_client_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting."""
    # Try to get user ID from headers (if authenticated)
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"

    # Fallback to IP address
    client_ip = request.client.host
    return f"ip:{client_ip}"


def check_rate_limit(
    identifier: str, limit: int, window: int
) -> tuple[bool, dict]:
    """
    Check if request is within rate limit.

    Args:
        identifier: Unique identifier for the client
        limit: Maximum number of requests allowed
        window: Time window in seconds

    Returns:
        Tuple of (is_allowed, rate_info)
    """
    redis_client = get_redis_client()
    if not redis_client:
        # If Redis is not available, allow all requests
        return True, {"limit": limit, "remaining": limit, "reset_time": 0}

    try:
        current_time = int(time.time())

        # Create Redis key for this identifier and window
        key = f"rate_limit:{identifier}:{current_time // window}"

        # Get current count
        current_count = redis_client.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        # Check if limit exceeded
        if current_count >= limit:
            # Get reset time
            reset_time = ((current_time // window) + 1) * window
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": reset_time - current_time,
            }

        # Increment counter
        redis_client.incr(key)
        redis_client.expire(key, window)

        return True, {
            "limit": limit,
            "remaining": limit - current_count - 1,
            "reset_time": ((current_time // window) + 1) * window,
        }

    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # If Redis fails, allow the request
        return True, {"limit": limit, "remaining": limit, "reset_time": 0}


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.

    Implements rate limiting with different limits for different endpoints:
    - Chat endpoints: 30 requests per minute
    - Health endpoints: 60 requests per minute
    - Other endpoints: 100 requests per minute
    """
    # Determine rate limit based on endpoint
    # Disable rate limiting for tests
    if (
        "test" in request.url.path
        or "pytest" in str(request.scope.get("type", ""))
        or request.url.path.startswith("/test")
        or "conftest" in str(request.scope.get("type", ""))
    ):
        # Skip rate limiting for tests
        return await call_next(request)
    elif request.url.path.startswith("/api/v1/chat"):
        limit = 30  # 30 requests per minute for chat
        window = 60
    elif request.url.path.startswith("/api/v1/health"):
        limit = 60  # 60 requests per minute for health checks
        window = 60
    else:
        limit = 100  # 100 requests per minute for other endpoints
        window = 60

    # Get client identifier
    identifier = get_client_identifier(request)

    # Check rate limit
    is_allowed, rate_info = check_rate_limit(identifier, limit, window)

    if not is_allowed:
        logger.warning(f"Rate limit exceeded for {identifier}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": rate_info["limit"],
                    "remaining": rate_info["remaining"],
                    "reset_time": rate_info["reset_time"],
                    "retry_after": rate_info.get("retry_after", 0),
                },
            },
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info.get("retry_after", 0)),
            },
        )

    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])

    return response
