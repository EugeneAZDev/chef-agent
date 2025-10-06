"""
Rate limiting for Chef Agent API.
"""

import time
from typing import Dict

from fastapi import Request
from fastapi.responses import JSONResponse


class SimpleRateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for given IP."""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time
                for req_time in self.requests[client_ip]
                if req_time > minute_ago
            ]
        else:
            self.requests[client_ip] = []

        # Check if under limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[client_ip].append(now)
        return True

    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for given IP."""
        now = time.time()
        minute_ago = now - 60

        if client_ip not in self.requests:
            return self.requests_per_minute

        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] if req_time > minute_ago
        ]

        return max(0, self.requests_per_minute - len(self.requests[client_ip]))


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    client_ip = get_client_ip(request)

    if not rate_limiter.is_allowed(client_ip):
        remaining = rate_limiter.get_remaining_requests(client_ip)
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": (
                    f"Too many requests. "
                    f"Limit: {rate_limiter.requests_per_minute} per minute"
                ),
                "retry_after": 60,
                "remaining_requests": remaining,
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(rate_limiter.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining),
            },
        )

    response = await call_next(request)

    # Add rate limit headers
    remaining = rate_limiter.get_remaining_requests(client_ip)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    return response
