# Design: Testing Pyramid Restructure

**Date:** 2026-08-01
**Status:** APPROVED — awaiting implementation

---

## Problem

The current CI test structure has one monolithic "unit tests" job running ~1500
tests via keyword exclusion (`-k "not e2e and not ..."`). Real unit tests (pure
functions, no DB) are indistinguishable from integration tests (DB, fixtures) and
live tests (external APIs). This causes:

1. "Unit" test job takes 5+ minutes
2. Live tests (`test_live_sources.py`) leak into unit runs and fail without API keys
3. No way to fail fast on pure unit tests before running slow integration
4. Markers exist in pytest.ini but aren't enforced via `-m` — only weak `-k` keyword matching
5. `.coveragerc` still references deleted `prei` package

## Design

### Testing Pyramid

```
                        ┌─────────────────────────────┐
                        │ post-deployment smoke         │  on deploy to production
                        │ live-sources                  │  on main push (non-gating)
                        ├─────────────────────────────┤
                        │ acceptance (httpx HTTP)       │  ~500 tests
                        ├─────────────────────────────┤
                        │ smoke  (Docker container)     │  docker-publish only
                        ├─────────────────────────────┤
                        │ e2e (full browser flows)      │  ~100 tests
                        ├─────────────────────────────┤
                        │ integration (DB, no external) │  ~800 tests, ~2 min
                        ├─────────────────────────────┤
                        │ unit (pure, no DB, <50ms)     │  ~700 tests, ~45 sec
                        ├─────────────────────────────┤
                        │ static-analysis               │  lint, typecheck, secrets
                        └─────────────────────────────┘
```

### Layer Mappings

| Layer               | Marker       | Needs | CI Job Name      | Required? |
|---------------------|-------------|-------|------------------|-----------|
| static-analysis     | n/a         | n/a   | `🔍 Lint` / `🔷 Typecheck` / `🔑 Secrets` | Yes |
| unit                | `unit`      | No DB, no HTTP, no filesystem | `🧪 Unit Tests` | Yes |
| integration         | `integration` | DB + fixtures, no external APIs | `🔗 Integration Tests` | Yes |
| smoke               | `smoke`      | Docker container build + startup | `🐳 Container Smoke` | Yes (docker-publish) |
| e2e                 | `e2e`       | Browser / Docker Compose | `E2E Tests` | Yes |
| acceptance          | `acceptance` | httpx against live_server | `🌐 Acceptance Tests` | Yes |
| live-sources        | `live`       | Real API keys (HUD, ATTOM, etc.) | `🌍 Live APIs` | No (non-gating, main push) |

### File Organization

All test files live in `tests/` root. Each file gets ONE file-level `pytestmark`:

```python
pytestmark = pytest.mark.unit                    # pure functions
pytestmark = pytest.mark.integration             # needs DB
pytestmark = pytest.mark.e2e                     # full pipeline flow
pytestmark = pytest.mark.smoke                   # container/Docker
pytestmark = pytest.mark.acceptance              # httpx HTTP
pytestmark = pytest.mark.live                    # real external APIs
```

Files with mixed test types (e.g. some pure functions + some DB tests) are split.

## Implementation Plan

### Phase 1: Pytest config + markers

1. Update `pytest.ini` — add `unit`, `smoke`, `acceptance` markers
2. Set default `addopts` to `-m "unit or integration"` (fast safe default for bare `pytest`)
3. Update `conftest.py` — auto-apply markers where possible via `pytest_collection_modifyitems`

### Phase 2: Annotate all 114 test files

1. Categorize by what the test ACTUALLY needs:
   - No DB at all → `unit` (~40 files)
   - DB but no external APIs → `integration` (~40 files)
   - DB + external third-party APIs → `live` (~4 files)
   - Docker container → `smoke` (~3 files)
   - httpx HTTP → `acceptance` (~9 files)
   - Full pipeline flow → `e2e` (~5 files)
2. Split mixed files
3. Run full suite to verify no regressions

### Phase 3: Rewrite CI workflow

1. Update `ci-quality.yml` test jobs to use `-m unit`, `-m integration`, etc. instead of `-k` filters
2. Set proper `needs:` dependencies (integration needs unit to pass first, etc.)
3. Update `pr-gates-pass` to reference new job names

### Phase 4: Fix config files

1. Update `.coveragerc` — remove `prei` from `source =`
2. Clean up any stale `__pycache__` and `.pyc` files in deleted directories

### Phase 5: Update Makefile

1. Replace `-k` filters with `-m` markers in all test targets
2. Add `make test-unit-fast` for CI-compatible unit runner
3. Verify `make check` runs through all layers

## Files To Modify

| File                        | Change                          |
|-----------------------------|---------------------------------|
| `pytest.ini`                | Add markers, update addopts      |
| `.github/workflows/ci-quality.yml` | Rewrite test jobs with `-m`  |
| `Makefile`                  | Update test targets              |
| `.coveragerc`               | Remove `prei` from sources       |
| ~30+ test files             | Add `pytestmark` marker         |
