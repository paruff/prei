# Specification: Phase A — CI/Test Quality Gaps (docs/TOP_01_PLAN.md)
# Written: 2026-07-27
# Status: MERGED (PR #323)

---

## 0. Problem

`docs/TOP_01_PLAN.md` Phase A identifies 5 gaps between this repo's CI pipeline
and a genuinely trustworthy one: acceptance/BDD suites that don't exercise real
HTTP, a PR-gate acceptance job that only `--collect-only`s instead of running,
an unbounded Docker build step, and acceptance tests that only check status
codes instead of response shape.

## 1. Requirements

- A-1: `main-ci-guard.yml` blocks PR merges on Tier-2 (post-merge) failure.
- A-2: `tests_bdd/`'s pipeline acceptance suite drives real HTTP requests
  (via pytest-django's `live_server`) instead of `django.test.Client`.
- A-3: `tests/acceptance/*.py` actually executes in the PR-gate tier
  (`ci-quality.yml`), not just `--collect-only`, via a `live_server` fallback
  when `BASE_URL` is unset.
- A-4: `docker-publish.yml`'s `build-image` job enforces a real 10-minute
  build-time budget (soft check + hard `timeout-minutes` backstop).
- A-5: All `tests/acceptance/*.py` files validate response shape via
  `schemas.py` Pydantic models, not just raw status codes.

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-A1-01 | `main-ci-guard.yml` fails the PR check when Tier 2 fails | ci |
| AC-A2-01 | `pytest tests_bdd/` passes using `live_server` + `httpx.Client` | unit |
| AC-A2-02 | POST-based BDD steps include a real CSRF token | unit |
| AC-A3-01 | `pytest tests/acceptance/` passes with no `BASE_URL` set (live_server fallback) | unit |
| AC-A3-02 | `ci-quality.yml`'s `acceptance-check` job runs tests for real, not `--collect-only` | ci |
| AC-A3-03 | `BASE_URL`-driven runs (`make test-acceptance`, `post-deployment.yml`) are unaffected | unit |
| AC-A4-01 | `build-image` job has `timeout-minutes: 10` | ci |
| AC-A4-02 | "Check build time" step fails the job if duration exceeds 600s | ci |
| AC-A5-01 | All 9 files in `tests/acceptance/` import and use `schemas.py` models | unit |
