"""Request timing middleware — Phase D Observability.

Logs every HTTP request as structured JSON with: method, path,
status_code, duration_ms, and request_id.  Emits OTEL spans for
uFawkesObs integration when OTEL is configured.
"""

from __future__ import annotations

import time
import uuid

import structlog

try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind

    _otel_available = True
except ImportError:  # pragma: no cover
    _otel_available = False

logger = structlog.get_logger(__name__)
if _otel_available:
    tracer = trace.get_tracer("prei.http")


class RequestTimingMiddleware:
    """Measure and log every HTTP request through the WSGI stack."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        # OTEL span for uFawkesObs tracing
        span = None
        if _otel_available:
            span = tracer.start_span(
                f"{request.method} {request.path}",
                kind=SpanKind.SERVER,
                attributes={
                    "http.method": request.method,
                    "http.url": request.path,
                    "request.id": request.request_id,
                },
            )

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start) * 1000, 1)

        if span is not None:
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.duration_ms", duration_ms)
            span.set_status(
                trace.StatusCode.OK
                if response.status_code < 500
                else trace.StatusCode.ERROR
            )
            span.end()

        logger.info(
            "request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request.request_id,
        )
        return response
