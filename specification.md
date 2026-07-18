# Specification: Top 0.1% — Phase A (Foundation)
# Written: 2026-07-18 session with paruff
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Phase A addresses the 5 critical gaps identified in TOP_01_PLAN.md:
1. CI self-test to prevent broken-main merges
2. HTTP-level acceptance tests as the primary artifact verification layer
3. Acceptance tests in PR quality gates
4. Build-time monitoring with regression alerts
5. Pydantic response models for schema-level test assertions

---

## 1. Problem Statement

**Current state:**
- CI on main was broken for 3 commits before detection. No guard prevents merging when CI is red on main.
- BDD tests use Django's TestClient — they test source code, not the artifact.
- Acceptance tests (tests/acceptance/) exist but aren't in PR quality gates.
- No build-time visibility or regression detection.
- Acceptance tests use loose dict-access assertions rather than typed schema validation.

**Desired state:**
- PR merges are blocked if CI on main is red.
- All critical user journeys are covered by HTTP-level acceptance tests using httpx.
- Acceptance tests run on every PR via the ci-quality.yml workflow.
- Build times are logged in CI, and a build exceeding 10 minutes triggers a warning.
- Acceptance test assertions use Pydantic models for full response shape validation.

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | PR merge gate checks if latest main CI run is green; blocks merge if red | P0 |
| F-02 | HTTP-level acceptance test suite covers: health, login, discovery, listings API, growth areas, foreclosures, property analysis pipeline | P0 |
| F-03 | Acceptance tests use httpx (already installed) and assert on JSON structure + HTML content | P0 |
| F-04 | Acceptance tests run in ci-quality.yml as a parallel PR gate | P1 |
| F-05 | Build-time is logged in docker-publish.yml with a 10-minute warning threshold | P1 |
| F-06 | Response assertions use Pydantic models instead of dict-access | P1 |

### 2.2 Non-Functional Requirements

| ID | Description |
|---|---|
| N-01 | Acceptance test suite must complete within 120 seconds |
| N-02 | Build-time check must not add meaningful overhead |
| N-03 | CI guard must not create false positives (should check specific job, not entire workflow) |

### 2.3 Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | `main-ci-guard` workflow runs on PR events and fails if the latest `Tier 2 Governance` run on main is not green | unit |
| AC-02 | `tests/acceptance/` directory contains ≥12 HTTP-level tests using httpx | unit |
| AC-03 | All acceptance tests pass against a local container with `BASE_URL=http://localhost:8000` | live-system |
| AC-04 | `ci-quality.yml` includes a job that runs `pytest tests/acceptance/` | unit |
| AC-05 | `docker-publish.yml` build-image step logs start + end timestamps and warns if elapsed >600s | unit |
| AC-06 | Pydantic models exist for: HealthResponse, ListingsResponse, GrowthAreasResponse, ForeclosuresResponse | unit |
| AC-07 | Acceptance tests use Pydantic model_validate() instead of dict access | unit |

---

## 4. Out of Scope

- BDD fixture rewrite (existing tests remain as-is; new httpx tests are additive)
- Canary deployments (Phase C)
- SLO dashboards (Phase D)
- Financial math verification (Phase B)
