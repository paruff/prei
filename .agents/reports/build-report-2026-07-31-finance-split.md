## Build Report — Finance utils split + audit finding resolution (LIMIT-20)

**Status:** COMPLETE

---

### Tasks Completed

| Task | Title | Lines Changed | Status |
| -------- | ----- | ------------- | ------ |
| SPLIT-1 | Create `investor_app/finance/mortgage.py` (9 functions: mortgage, carrying costs, break-even rent, paydown, appreciation, ROI components) | ~330 | DONE |
| SPLIT-2 | Create `investor_app/finance/taxes.py` (11 functions: depreciation, tax benefits, after-tax IRR/CF, hold-period projections, sale proceeds, recapture) | ~640 | DONE |
| SPLIT-3 | Create `investor_app/finance/scoring.py` (5 primitives: 1% rule, GRM, price-to-rent, market normalization helpers) | ~150 | DONE |
| SPLIT-4 | Create `investor_app/finance/strategies.py` (8 functions: flip, rental, vacation, BRRRR calculators; `estimate_rehab_cost` decoupled from settings) | ~400 | DONE |
| SPLIT-5 | Rewrite `investor_app/finance/utils.py` to core math + Django-coupled analysis only; delete aliases (`calculate_noi`/`calculate_cap_rate`/`calculate_cash_on_cash`/`calculate_irr`), dead `score_listing_v1`, and deprecated `score_listing_v1_deprecated` chain | ~231 (net −2116) | DONE |
| IMPORTERS | Update 17 importers (services, api_views, views, tests) to canonical module locations | ~120 | DONE |
| AUDIT-1 | Remove dead service-layer duplicate `calculate_noi` from `core/services/property_service.py` (+ export in `__init__.py`, delete `tests/test_property_service.py`) | −45 | DONE |
| AUDIT-2 | Delete duplicate pure `score_listing_v2` tests (`TestScoreListingV2` in `tests/test_underwriting_score.py`); production version remains only in `core/services/scoring.py` | −161 | DONE |
| VERIFY | Fix behavior regression: `total_return_summary` must keep returning `purchase_price` key (moved copy dropped it) | +3 | DONE |
| DOCS | Mark LIMIT-20 resolved in `docs/KNOWN_LIMITATIONS.md` | +8 | DONE |

### Artifacts Produced

- [x] Source code files — `investor_app/finance/{mortgage,taxes,scoring,strategies}.py`
- [x] Source code files — rewritten `investor_app/finance/utils.py`
- [ ] Manifests in `manifests/` — N/A (no K8s surface touched)
- [ ] Pipeline in `pipeline-spec.yaml` — N/A (no CI pipeline change)
- [ ] Overlays in `overlays/` — N/A (no GitOps change)

### Validation Results

| Check | Status |
| --------- | ------ |
| Lint (ruff) | PASS |
| Typecheck (mypy, touched files) | PASS |
| Tests (full suite) | PASS — 1803 passed, 1 skipped, 261 deselected |
| Policy | PASS — no governance violations; `postgres`, `migration-safety`, `gitops` untouched |

Pre-existing mypy error in `tests/acceptance/conftest.py:69` (no-any-return) is unrelated to this change — file unmodified.

### Blockers

None.

### Dual-pipeline (pydantic `prei` vs Django) findings

Per the user's directive to resolve the dual-pipeline question "using Django," investigated how much production code depends on the pydantic `prei` side:

- **Django is the load-bearing pipeline**: `core/models/pipeline.py` (`PipelineAsset`, `PipelineProperty`), `core/services/pipeline.py`, screening, leasing, notifications, and ~20 prod/test files. This is the source of truth.
- **`prei` pydantic side is a standalone FastAPI microservice, not mounted**: `prei/api/pipeline_routes.py` (FastAPI router) and `prei/cli.py` are not referenced by any Django URLconf, `INSTALLED_APPS`, docker-compose service, or CI deploy. `prei/pipeline/orchestrator.py` is imported only by tests.
- **One production coupling**: `core/views/__init__.py` imports `prei.integrations.landlord_data.get_state_landlord_score` (top-level) and lazily imports `DiscoveryProcessor`/`BatchScreeningProcessor`/`ScreeningThresholds`/`PipelineEngine`/`InMemoryAssetRepository`/`discover_from_all` for the Growth Explorer bridge (P0 fix from `docs/assessments/AUDIT_GA_PIPELINE.md`).
- **Recommendation**: keep the pydantic discovery/screening *processors* (they are the only working bridge from Growth Explorer into pipeline screening, and they are Decimal-based after Phase B) but do not build new state on pydantic models (`PropertyAsset`/`StageLog`); persist pipeline state via Django `PipelineProperty`/`PipelineAsset`. Full removal of the pydantic state machine, FastAPI routes, and CLI is a separate reviewed change requiring PM sign-off — it touches the orchestrator, handlers, 11 test files, and the Growth Explorer bridge. Filed as a follow-up recommendation, not executed here.

The finance-utils split itself is independent of that decision: `prei/pipeline/{orchestrator,handlers/underwriting}.py` still import only `to_decimal`/`cap_rate`/`cash_on_cash` from `investor_app.finance.utils`, all of which remain in place.
