# Design: Phase D — Observability
# Written: 2026-07-18
# Status: Draft

---

## 1. Architecture

### D-1: Structured JSON Logging

Use `django-structlog` + `python-json-logger`. Configuration in `investor_app/settings.py`:

```python
import structlog

LOGGING = {
    "version": 1,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
```

### D-2: Request Timing Middleware

A lightweight Django middleware at `core/middleware.py`:

```python
import time, uuid, structlog

logger = structlog.get_logger(__name__)

class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info("request", method=request.method, path=request.path,
                     status=response.status_code, duration_ms=duration_ms,
                     request_id=request.request_id)
        return response
```

### D-3: Alerting Thresholds

A script `scripts/alert-check.sh` that queries the last 10 Tier 2 Governance runs and computes failure rate. Warnings via `::warning::` annotation in CI.

### D-4: API Surface Validation

A script `scripts/validate-api-surface.sh` that checks `docs/API_SURFACE.md` for stale function references by grepping the source code for documented functions. Fails CI if any documented function is missing from the source.

---

## 2. File Changes

| File | Change | Purpose |
|---|---|---|
| `requirements.txt` | Add `django-structlog`, `python-json-logger` | D-1 |
| `investor_app/settings.py` | Add structlog + JSON logging config | D-1 |
| `core/middleware.py` | New: RequestTimingMiddleware | D-2 |
| `investor_app/settings.py` | Register middleware | D-2 |
| `scripts/alert-check.sh` | New: deploy failure rate check | D-3 |
| `scripts/validate-api-surface.sh` | New: API surface validation | D-4 |
| `ci-quality.yml` | Add alert-check + api-surface gates | D-3, D-4 |
| `Makefile` | Add test-alerts, test-api-surface targets | D-3, D-4 |
