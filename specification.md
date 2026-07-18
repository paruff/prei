# Specification: Post-Deployment Acceptance Pipeline
# Written: 2026-07-18 session with paruff
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

The current `post-deployment.yml` runs 3 curl-based HTTP 200 checks against a deployment URL. This does not test content correctness, performance, or security. Phase 3 replaces this with a proper post-deployment acceptance pipeline: HTTP-level content assertions, Lighthouse performance budgets, DAST security scanning, and automated rollback on any failure.

---

## 1. Problem Statement

**Current state:**
- `post-deployment.yml` checks 3 endpoints for HTTP 200 only
- No content validation (a 200 with error HTML passes)
- No performance measurement
- No security scanning against the live system
- Rollback exists as fallback but has no trigger criteria beyond "smoke failed"

**Desired state:**
- HTTP acceptance tests that validate JSON structure, field values, and error responses
- Lighthouse performance budgets with pass/fail gates
- OWASP ZAP DAST scanning for common web vulnerabilities
- Automated rollback on any gate failure
- Results visible as PR checks and deployment logs

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | Acceptance tests must make real HTTP requests to the deployed URL | P0 |
| F-02 | Tests must assert on JSON response structure and content, not just status codes | P0 |
| F-03 | Tests must cover: health endpoint, login page, listings API, growth areas API, foreclosures API | P0 |
| F-04 | Performance tests must measure TTFB, LCP, CLS with pass/fail thresholds | P1 |
| F-05 | Security scanning must detect common web vulnerabilities (XSS, CSRF, injection) | P1 |
| F-06 | Rollback must trigger automatically if any gate fails | P0 |
| F-07 | Results must be logged to the workflow run for debugging | P1 |

### 2.2 Non-Functional Requirements

| ID | Description |
|---|---|
| N-01 | Acceptance test suite must complete within 120 seconds |
| N-02 | Lighthouse run must complete within 60 seconds per URL |
| N-03 | Security scan must complete within 180 seconds |
| N-04 | Tests must be idempotent (safe to run multiple times against the same URL) |
| N-05 | Tests must not modify production data |

### 2.3 Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | Health endpoint returns `{"status": "ok"}` with HTTP 200 | live-system |
| AC-02 | Login page returns HTML with a form element containing password field | live-system |
| AC-03 | Listings API returns JSON with `count` (int) and `results` (list) keys | live-system |
| AC-04 | Growth areas API returns JSON array or object with `results` key | live-system |
| AC-05 | Foreclosures API returns JSON array or object with `results` key | live-system |
| AC-06 | Discovery page returns HTML with HTTP 200 | live-system |
| AC-07 | Static CSS is served with correct Content-Type header | live-system |
| AC-08 | Health API returns JSON with `status` key | live-system |
| AC-09 | Lighthouse TTFB is under 1000ms for the health endpoint | live-system |
| AC-10 | Lighthouse performance score is above 50 (informational) | live-system |
| AC-11 | OWASP ZAP scan completes with no HIGH or CRITICAL alerts | live-system |
| AC-12 | Rollback runs `git revert` on GitOps repo when any gate fails | live-system |

---

## 3. Success Criteria

This feature is complete when:

1. `post-deployment.yml` has 4 jobs: `smoke`, `acceptance`, `performance`, `security`
2. `acceptance` runs HTTP-level tests with content assertions (not just 200)
3. `performance` runs Lighthouse CI with budgets
4. `security` runs OWASP ZAP baseline scan
5. `rollback` triggers automatically on any failure
6. All existing PR gates still pass
7. Running `make test-acceptance` locally works against a running container

---

## 4. Out of Scope

- Canary deployments (Phase 4)
- Synthetic monitoring (Phase 4)
- Playwright E2E tests against the container (Phase 2 scope, separate work)
- Full financial KPI correctness tests (requires dedicated spec)
