## Build Report — pydantic→Django consolidation (remove `prei/`, port services to `core/services/`)

**Status:** COMPLETE

---

### Tasks Completed

| Task     | Title | Lines Changed | Status |
| -------- | ----- | ------------- | ------ |
| TASK-01 | Port discovery services (sanitizer, `CanonicalPropertyPayload`, `process_discovery_batch`) to `core/services/discovery.py` + `discovery_processor.py`, pydantic-free | ~300 | DONE |
| TASK-02 | Port sources (base, registry, county, reo_sources, vrm_source, file_source) to `core/services/sources/` | ~600 | DONE |
| TASK-03 | Port screening evaluator (`ScreeningThresholds`, `evaluate_screening_stage`, `screen_batch`) to `core/services/screening.py` | ~151 | DONE |
| TASK-04 | Port underwriting + offer solvers to `core/services/underwriting.py` / `offer.py` (Decimal; LIMIT-21) | ~250 | DONE |
| TASK-05 | Rewrite Growth Explorer bridge in `core/views/__init__.py` to use `core.services` | ~12 | DONE |
| TASK-06 | Rewrite VRM `run_pipeline` bridge to use `core.services` | ~13 | DONE |
| TASK-07 | Migrate tests + BDD steps to `core.services.*`; delete orchestrator/state-machine test sections | ~950 | DONE |
| TASK-08 | Remove `prei/models/pipeline.py`, `prei/pipeline/engine.py`, `prei/pipeline/orchestrator.py` | −3 files | DONE |
| TASK-09 | Remove `prei/api/`, `prei/cli.py`, `prei/pipeline/tests/test_api.py` (fastapi/click consumers) | −5 files | DONE |
| TASK-10 | Delete entire `prei/` package; zero `from prei`/`import prei` repo-wide (AC-10-1) | −all | DONE |
| TASK-11 | Drop `fastapi`/`uvicorn`/`click`; keep `pydantic` (acceptance tests); update KNOWN_LIMITATIONS (LIMIT-21 resolved), ARCHITECTURE.md, CHANGE_IMPACT_MAP.md (AC-11-3) | ~40 | DONE |

### Artifacts Produced

- [x] Source code files — `core/services/{discovery,discovery_processor,screening,underwriting,offer,landlord_data}.py`, `core/services/sources/` (all pydantic-free, ruff/mypy clean)
- [x] Manifests — n/a (no new K8s surface; this is a Django app repo)
- [x] Pipeline — n/a (CI config unchanged; verified prei docker image is the Django web image, not a separate FastAPI surface)
- [x] Overlays — n/a
- [x] Tests — 9 test files + `tests_bdd/steps/pipeline_steps.py` migrated to `core.services.*`
- [x] Docs — `docs/KNOWN_LIMITATIONS.md`, `docs/ARCHITECTURE.md`, `docs/CHANGE_IMPACT_MAP.md` updated

### Validation Results

| Check     | Status |
| --------- | ------ |
| Lint      | PASS (`ruff check .` — All checks passed) |
| Typecheck | PASS (2 pre-existing mypy errors in untouched files: `tests/acceptance/conftest.py:69` no-any-return, `tests_bdd/conftest.py:31` `__init__` misc) |
| Tests     | PASS (full suite 1791 passed, 1 skipped, 256 deselected in 445s; e2e subset 19 passed; local unit 35 passed) |
| Policy    | PASS (AC-10-1 no prei imports; AC-10-3 suite green with prei gone; governance: no Bootstrap/secrets/float-currency violations in new code) |

### Blockers

None.

### Notes

- `pydantic` retained in `requirements.txt` because `tests/acceptance/{schemas,test_api.py}` still import it; `fastapi`/`uvicorn`/`click` had zero remaining consumers.
- `ScreeningThresholds`/`screen_batch` remain float-based (transient ratio math, by design); Decimal conversion happens at the persistence boundary; `underwriting.py` + `offer.py` are Decimal.
- Bridge sites are stats-only (no persistence), matching AC-05-2 "identical behavior".
- `CLAUDE.md` working-tree change is unrelated/pre-existing (not part of this plan).
- Log entry appended to `.agents/logs/2026-07-31.jsonl`.
