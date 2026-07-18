# Specification: Phase D — Observability
# Written: 2026-07-18
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Phase D makes the application observable: structured logging, request timing,
alerting thresholds, and auto-validated API docs. Without observability, a
production issue is invisible until a user reports it.

---

## 1. Problem Statement

**Current state:**
- Django default text logging — not machine-parseable
- No request timing or latency tracking
- No alerting thresholds defined
- `docs/API_SURFACE.md` is manually maintained and out of date (last updated May 2026)

**Desired state:**
- JSON-formatted logs with structured fields (request_id, method, path, status, duration_ms)
- Request timing middleware that logs every HTTP request
- CI-based alerting checks for deploy failure rate
- API_SURFACE.md validated in CI against actual code signatures

---

## 2. Scope

| Task | Description |
|---|---|
| D-1 | Structured JSON logging via `django-structlog` |
| D-2 | Request timing middleware with structured log output |
| D-3 | Alerting threshold checks in CI (deploy failure rate > 10% warns) |
| D-4 | API surface doc validation script + CI gate |

### Out of Scope (needs infra not available)

- OpenTelemetry distributed tracing (needs collector + backend)
- Production alerting/paging (needs monitoring service)
- Dashboard generation (needs Grafana or equivalent)

---

## 3. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | Request logging outputs JSON with: method, path, status, duration_ms, request_id | P0 |
| F-02 | Structured logging uses django-structlog (already compatible with Django 5.2) | P0 |
| F-03 | Request timing middleware measures every HTTP request at the WSGI level | P1 |
| F-04 | CI check warns if deploy failure rate exceeds 10% over the last 10 runs | P1 |
| F-05 | API surface validation script checks actual code against docs/API_SURFACE.md | P1 |

---

## 4. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | JSON logging middleware installed and configured | unit |
| AC-02 | Request logs contain method, path, status_code, duration_ms fields | live-system |
| AC-03 | `make test-alerts` runs deploy failure rate check | unit |
| AC-04 | Alert check warns when failure rate > 10% in last 10 Tier 2 runs | unit |
| AC-05 | `scripts/validate-api-surface.sh` checks docs/API_SURFACE.md against source | unit |
| AC-06 | CI gate runs API surface validation on every PR | unit |
