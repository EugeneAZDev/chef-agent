"""
Security middleware for Chef Agent API.
"""

import re

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def scrub_sensitive_data(content: str) -> str:
    """Scrub sensitive data from logs."""
    # Scrub API keys
    content = re.sub(r"gsk_[a-zA-Z0-9]{48}", "[GROQ-KEY]", content)
    content = re.sub(r"sk-[a-zA-Z0-9]{48}", "[OPENAI-KEY]", content)

    # Scrub other sensitive patterns
    content = re.sub(r"\b\d{10,}\b", "[ID]", content)
    content = re.sub(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]", content
    )

    return content


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Additional security headers
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log requests and responses with sensitive data scrubbing."""

    async def dispatch(self, request: Request, call_next):
        # Log request
        request_info = f"{request.method} {request.url.path}"
        if request.query_params:
            request_info += f"?{request.query_params}"

        print(f"🔵 {request_info}")

        response: Response = await call_next(request)

        # Log response
        response_info = (
            f"{response.status_code} "
            f"{response.headers.get('content-type', '')}"
        )
        print(f"🟢 {response_info}")

        return response
