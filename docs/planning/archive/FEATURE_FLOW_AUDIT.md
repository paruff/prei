# Feature-Flow Comprehensive Audit

> **Commit:** `76dd5ce`
> **Date:** 2026-07-07
> **Total pipeline tests:** 190 (all passing)
> **Files created:** 16 across 10 issues

---

## Issue Overview

| Issue | Title | File(s) | Tests | Status |
|-------|-------|---------|-------|--------|
| 1.1 | Core Data Models & State Machine | `prei/models/pipeline.py` | (inline) | ✅ |
| 1.2 | Pipeline Engine & Hooks | `prei/pipeline/engine.py` | 12 | ✅ |
| 2.1 | Canonical Schema & Ingestion | `prei/pipeline/handlers/discovery.py` | 42 | ✅ NEW |
| 2.2 | Screening Evaluator | `prei/pipeline/handlers/screening.py` | 31 | ✅ |
| 2.3 | Batch Screening Pipeline | `prei/pipeline/handlers/batch_screening.py` | 7 | ✅ |
| 2.4 | Comprehensive Tests | `tests/test_pipeline.py` | 30 | ✅ |
| 3.1 | Underwriting Solver | `prei/pipeline/handlers/underwriting.py` | 22 | ✅ |
| 3.2 | State Aggregator & Persistence | `prei/pipeline/engine.py` (enhanced) | 23 | ✅ |
| 3.3 | REST API & CLI | `prei/api/pipeline_routes.py`, `prei/cli.py` | 23 | ✅ |

---

## 1.1 Core Data Models & State Machine

**Files:** `prei/models/pipeline.py`

### Verified
- ✅ `PipelineStage` — 11-value string enum (GACS through KILLED)
- ✅ `PropertyAsset` — asset_id, address, current_stage, stage_history, kill_reason
- ✅ `StageLog` — immutable record with timestamps, reason, metrics
- ✅ `ALLOWED_TRANSITIONS` — static ruleset enforcing forward-only flow
- ✅ `transition_to()` — deterministic; raises `InvalidStageTransitionException` on illegal moves
- ✅ KILLED is terminal — no transitions out
- ✅ Bidirectional LEASING ↔ PORTFOLIO
- ✅ `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` (no deprecation warnings)

### Gaps
- ⚠️ No integration with Django models yet (standalone pydantic)

---

## 1.2 Pipeline Engine & Hooks

**Files:** `prei/pipeline/engine.py`

### Verified
- ✅ `PipelineEngine(repository)` — initialized with `AssetRepository`
- ✅ `register_hook(stage, hook_fn)` / `remove_hook(stage, hook_fn)` API
- ✅ `process_transition(asset, target, context)` — full lifecycle
- ✅ Pre-transition hook evaluation → KILLED on rejection
- ✅ Hook exceptions caught → KILLED
- ✅ Short-circuit on first hook failure
- ✅ `AssetRepository` ABC with `load()`, `save()`, `list_all()`
- ✅ `InMemoryAssetRepository` — deep-copy safe for testing

### Gaps
- None identified

---

## 2.1 Canonical Schema & Ingestion Sanitizer (NEW)

**Files:** `prei/pipeline/handlers/discovery.py`, `prei/pipeline/tests/test_discovery.py`

### Verified
- ✅ `DiscoverySanitizer.clean_address()` — regex-based normalizer
  - Strips punctuation, lowercases, collapses whitespace
  - Idempotent (normalizing twice yields same result)
  - Handles None/empty → empty string
- ✅ `compute_address_hash()` — SHA-256 hex digest (64 chars)
- ✅ `transform_input(raw, source)` — ETL with key fallback chains
  - MLS schema: `id`, `address`, `ListPrice`, `BedroomsTotal`, etc.
  - County schema: `parcel_id`, `FullStreetAddress`, `sale_price`, etc.
  - Minimal schema: only requires address
- ✅ `CanonicalPropertyPayload` — pydantic model with field validators
  - `coerce_float`: handles strings, floats, None → Optional[float]
  - `coerce_beds`: handles 3.0, "3", None → int
  - `coerce_baths`: handles "2.5", 2, None → float
  - Missing/empty secondary fields → None
- ✅ 42 tests: address normalization (parametrized), hashing, 3 schema formats, type coercion matrix, edge cases

### Gaps
- ⚠️ `price` made `Optional[float]` (not `float`) to match validator — spec had inconsistency

---

## 2.2 Screening Evaluator

**Files:** `prei/pipeline/handlers/screening.py`

### Verified
- ✅ `ScreeningThresholds` pydantic model with 6 fields
- ✅ `gross_yield(rent, price)` — pure arithmetic, handles zero/negative → 0.0
- ✅ `price_to_rent_ratio(rent, price)` — handles zero rent → inf
- ✅ `evaluate_screening_stage(asset_data, thresholds)` → `(bool, str|None)`
- ✅ Evaluation order: beds → baths → HOA → yield → ratio (cheapest first)
- ✅ Short-circuit on first failure
- ✅ Missing keys → check skipped (not failed)
- ✅ HOA exclusion: case-insensitive matching

### Gaps
- None identified

---

## 2.3 Batch Screening Pipeline

**Files:** `prei/pipeline/handlers/batch_screening.py`

### Verified
- ✅ `BatchScreeningProcessor(engine, thresholds, max_workers=8)`
- ✅ `process(property_dicts)` → `{processed, advanced, killed, execution_time_ms}`
- ✅ ThreadPoolExecutor for parallel evaluation
- ✅ Auto-advances GACS → DISCOVERY → SCREENING before evaluation
- ✅ Errors caught per-asset, counted as killed
- ✅ 1000 properties in ~1.3s

### Gaps
- None identified

---

## 2.4 Comprehensive Tests

**Files:** `tests/test_pipeline.py`

### Verified
- ✅ 30 tests covering all three validation categories
- ✅ State transition: illicit jumps (GACS→UNDERWRITING, GACS→PORTFOLIO, SCREENING→CLOSING, OFFER→TURNOVER, KILLED→anything)
- ✅ Screening math: division by zero, missing data, string coercion, empty HOA list
- ✅ 10-asset mock dataset: 3 pass, 6 fail distinct rules, 1 missing-rent pass
- ✅ Deterministic: same dataset → same counts
- ✅ Performance floor: evaluate_screening_stage <10ms

### Gaps
- None identified

---

## 3.1 Underwriting Solver

**Files:** `prei/pipeline/handlers/underwriting.py`

### Verified
- ✅ `UnderwritingInput` — 9 fields with sensible defaults
- ✅ `UnderwritingMetrics` — NOI, cap_rate, cash_on_cash, MAO
- ✅ `solve_underwriting(inputs, target_cap_rate)` → `UnderwritingMetrics`
- ✅ Computation: GPR → EGI → OpEx → NOI → Cap Rate → CoC → MAO
- ✅ Division-by-zero guards on all 4 return metrics (→ 0.0)
- ✅ 22 tests: pure arithmetic, defaults, edge cases, deterministic, sub-10ms

### Gaps
- ⚠️ All-cash assumption for CoC (no debt service model yet)

---

## 3.2 State Aggregator & Persistence

**Files:** `prei/pipeline/engine.py` (enhanced with TransactionalRepository, SqliteAssetRepository, StateAggregator)

### Verified
- ✅ `AssetRepository.begin/commit/rollback` — optional transaction hooks on ABC
- ✅ `TransactionalRepository` — thread-safe wrapper with buffer/commit/rollback
- ✅ `TransactionError` — raised on invalid transaction state
- ✅ `SqliteAssetRepository` — full SQLite persistence with WAL mode
  - JSON serialization of stage_history
  - Auto-commit individual saves outside explicit transactions
  - `begin()` is no-op if already in transaction
- ✅ `StateAggregator` — `count_by_stage()`, `summary()` with pipeline_flow breakdown
- ✅ 23 tests: transactional buffer/commit/rollback, SQLite save/load/update/transactions, aggregator counts/flow

### Gaps
- ⚠️ `SqliteAssetRepository.delete()` not implemented (soft delete via KILLED)
- ⚠️ InMemoryAssetRepository doesn't support `rollback()` (no-op)

---

## 3.3 REST API & CLI

**Files:** `prei/api/pipeline_routes.py`, `prei/cli.py`

### Verified
- ✅ `GET /api/v1/pipeline/summary` — returns StateAggregator.summary()
- ✅ `GET /api/v1/pipeline/assets` — list all assets
- ✅ `GET /api/v1/pipeline/assets/{id}` — single asset detail (404 if missing)
- ✅ `POST /api/v1/pipeline/assets` — create at GACS (409 if duplicate, 422 if missing fields)
- ✅ `POST /api/v1/pipeline/transition` — manual transition (422 on illicit jump/invalid stage)
- ✅ `DELETE /api/v1/pipeline/assets/{id}` — soft delete (→ KILLED)
- ✅ `configure_repository()` — DI for testing
- ✅ CLI: `prei-cli pipeline summary`, `ingest --source <file> [--run-screening]`, `transition`
- ✅ 23 tests: all endpoints, error codes, CLI ingest/transition

### Gaps
- ⚠️ FastAPI app not wired into Django (standalone microservice)
- ⚠️ No authentication on API endpoints
- ⚠️ No production ASGI entrypoint yet

---

## What's Missing from the Feature-Flow Process

### Pipeline Stage Handlers
| Stage | Handler | Status |
|-------|---------|--------|
| GACS | — | Default start state |
| DISCOVERY | `discovery.py` | ✅ New (this session) |
| SCREENING | `screening.py` | ✅ |
| UNDERWRITING | `underwriting.py` | ✅ |
| OFFER | — | ❌ **Missing** |
| DUE_DILIGENCE | — | ❌ **Missing** |
| CLOSING | — | ❌ **Missing** |
| TURNOVER | — | ❌ **Missing** |
| LEASING | — | ❌ **Missing** |
| PORTFOLIO | — | ❌ **Missing** |

### Architectural Gaps
1. **Django integration** — Pipeline models are pydantic-only, not Django models
   - No migration files for pipeline assets
   - No Django admin integration
   - No database-backed repository wired into the Django app

2. **Authentication** — REST API has no auth layer
   - No API keys, JWT, or session auth
   - CLI has no credential management

3. **Production deployment**
   - No ASGI entrypoint (`main.py` with uvicorn)
   - No Docker Compose config for the API microservice
   - No CI/CD for the API

4. **Monitoring**
   - No health check endpoint
   - No structured logging (JSON logs)
   - No metrics collection

5. **Pipeline wiring**
   - No orchestration connecting the stages (discovery → screening → underwriting → ...)
   - Each handler is standalone; no higher-level "run_pipeline(asset)" function
   - No webhook/callback system for stage transitions

6. **Data validation**
   - `DiscoverySanitizer.transform_input()` returns `CanonicalPropertyPayload` but no code connects it to `PipelineEngine` or `BatchScreeningProcessor`
   - No end-to-end integration test from raw JSON → discovery → screening → underwriting

### Recommended Next Issues
| Priority | Issue | Description |
|----------|-------|-------------|
| 🔴 P0 | Pipeline Orchestrator | `run_pipeline(asset_id)` that chains discovery → screening → underwriting |
| 🔴 P0 | Django Pipeline Models | Django ORM models + migration for pipeline assets + admin |
| 🟡 P1 | Offer Handler | `prei/pipeline/handlers/offer.py` — offer price optimization |
| 🟡 P1 | API Auth | JWT or API key auth for FastAPI endpoints |
| 🟢 P2 | Production ASGI entrypoint | `prei/main.py` with uvicorn, health check, middleware |
| 🟢 P2 | CI/CD Pipeline | GitHub Actions for pipeline tests + API deployment |

---

## Test Coverage Summary

| Module | Test File | Count |
|--------|-----------|-------|
| State Machine (pipeline.py) | (tested via engine + pipeline) | — |
| Engine + Repositories | `test_engine.py` + `test_repository.py` | 35 |
| Discovery | `test_discovery.py` | 42 |
| Screening | `test_screening.py` | 31 |
| Batch Screening | `test_batch_screening.py` | 7 |
| Underwriting | `test_underwriting.py` | 22 |
| REST API + CLI | `test_api.py` | 23 |
| Integration (10-asset) | `tests/test_pipeline.py` | 30 |
| **Total** | | **190** |
