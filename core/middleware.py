"""Request timing middleware — Phase D Observability.

Logs every HTTP request as structured JSON with: method, path,
status_code, duration_ms, and request_id.  Used by the deployment
pipeline to measure latency and detect regressions.
"""

from __future__ import annotations

import time
import uuid

import structlog

logger = structlog.get_logger(__name__)


class RequestTimingMiddleware:
    """Measure and log every HTTP request through the WSGI stack."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start) * 1000, 1)
        logger.info(
            "request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request.request_id,
        )
        return response
