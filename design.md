# Design: Top 0.1% — Phase A (Foundation)
# Written: 2026-07-18 session with paruff
# Status: Draft

---

## 1. Architecture Overview

### A-1: CI Self-Test Guard

```
PR opened → ci-quality.yml runs (as today)
              └── new job: main-ci-guard
                  ├── fetch latest main CI run for Tier 2 Governance
                  ├── if conclusion != "success": block merge
                  └── if conclusion == "success": pass
```

A new workflow `main-ci-guard.yml` runs on `pull_request` events. It uses the GitHub API (via `gh` CLI or actions/github-script) to check the latest run of the `Tier 2 Governance — Build, Publish & Attest` workflow on the `main` branch. If that run is not `success`, the guard fails, preventing PR merge.

**Design decision:** Use a separate workflow rather than adding to ci-quality.yml. This keeps the guard independent and allows it to run in parallel.

### A-2: HTTP Acceptance Tests (expanded from tests/acceptance/)

Add 3 new test files to `tests/acceptance/`:
- `test_property_pipeline.py` — tests the property creation + analysis workflow via HTTP
- `test_authentication.py` — tests login, session, protected endpoints
- `schemas.py` — Pydantic models for response validation

Existing `test_api.py` and `test_pages.py` remain unchanged.

### A-3: Acceptance Tests in PR Gates

Add a job to `ci-quality.yml`:

```yaml
acceptance:
  name: "🌐 Acceptance Tests"
  runs-on: ubuntu-latest
  needs: [tests-e2e]  # run after e2e, just needs the codebase
  steps:
    - uses: actions/checkout@v7
    - uses: ./.github/actions/python-setup
    - name: Install deps
      run: pip install httpx beautifulsoup4 pydantic
    - name: Start Docker container
      run: docker compose up -d && sleep 10
    - name: Run acceptance tests
      env:
        BASE_URL: http://localhost:8000
      run: python -m pytest tests/acceptance/ -q --tb=short
```

**Design decision:** Run against a local docker compose instance. This tests the actual artifact (Docker image) rather than just the source code.

### A-4: Build-Time Monitoring

Add timing to the `build-image` step in `docker-publish.yml`:

```yaml
- name: Build image (timed)
  id: build
  uses: docker/build-push-action@v7
  ...

- name: Check build time
  if: always() && steps.build.outcome == 'success'
  run: |
    # Warnings are informational; will become hard failures in Phase D
    echo "Build completed at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Add a `job-start` / `job-finish` timestamp comparison step that logs elapsed time.

### A-5: Pydantic Response Models

```python
# tests/acceptance/schemas.py

from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

class ListingsResponse(BaseModel):
    count: int
    results: list
    next: str | None = None
    previous: str | None = None

class GrowthArea(BaseModel):
    name: str
    city: str
    state: str
    composite_score: float
    employment_growth: float | None = None
    population_growth: float | None = None

class GrowthAreasResponse(BaseModel):
    areas: list[GrowthArea]
    state: str
    totalResults: int

class ForeclosuresResponse(BaseModel):
    resultsCount: int
    dataSources: list
    location: str
```

Tests use `HealthResponse.model_validate(resp.json())` instead of `resp.json()["status"] == "ok"`.

---

## 2. File Changes

| File | Change | Purpose |
|---|---|---|
| `.github/workflows/main-ci-guard.yml` | New | A-1: CI self-test |
| `tests/acceptance/schemas.py` | New | A-5: Pydantic models |
| `tests/acceptance/test_property_pipeline.py` | New | A-2: Pipeline HTTP tests |
| `tests/acceptance/test_authentication.py` | New | A-2: Auth HTTP tests |
| `tests/acceptance/test_api.py` | Modified | A-5: Use Pydantic models |
| `tests/acceptance/test_pages.py` | Modified | A-5: Use Pydantic models |
| `.github/workflows/ci-quality.yml` | Modified | A-3: Add acceptance gate |
| `.github/workflows/docker-publish.yml` | Modified | A-4: Build-time monitoring |
| `Makefile` | Modified | N/A: Add `make test-acceptance-hdrs` target for CI |
| `requirements.txt` | Modified | N/A: Add pydantic (already exists) |

---

## 3. Constraints & Risks

| Risk | Mitigation |
|---|---|
| CI guard uses GitHub API rate limits | Cache the result per PR push |
| docker compose up may be slow in CI | Use cached layers, limit to 120s timeout |
| Acceptance tests need a running container | ci-quality.yml starts one via docker compose |
| Pydantic models may not match actual API shape | Write tests for the models against real responses first |
| Build-time monitoring adds noise | Start with warn-only, escalate to hard fail in Phase D |
