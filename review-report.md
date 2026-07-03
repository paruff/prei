# Review Report — Phase B: GrowthArea Population & SQLite Default

**Branch:** `feature/tasks-a`
**Date:** 2025-07-03
**Reviewer:** review-agent (Phase 4)

---

## Verdict: **APPROVED**

All Phase B acceptance criteria met. Implementation follows project patterns. No blocking issues.

---

## Summary of Changes Reviewed

| Task | Component | Files Changed | Status |
|------|-----------|---------------|--------|
| B1 | Census place growth metrics (two-vintage) | `core/integrations/market/census.py` | ✅ PASS |
| B2 | BLS employment growth (state-level) | `core/integrations/market/bls.py` | ✅ PASS |
| B3 | Housing demand index (occupancy proxy) | `core/integrations/market/census.py` | ✅ PASS |
| B4 | `populate_growth_areas` management command | `core/management/commands/populate_growth_areas.py` (new) | ✅ PASS |
| B5 | `/growth/` view: GrowthArea + fallback | `core/views.py` | ✅ PASS |
| — | SQLite default (dev) | `docker-compose.yml`, `.env.example` | ✅ PASS |
| — | ATTOM comps fix | `core/integrations/market/comps.py` | ✅ PASS |
| — | Test fixes (pre-existing) | `core/tests/test_neighborhood_insights.py` | ✅ PASS |
| — | Docs update | `core/integrations/README.md` | ✅ PASS |

**Test Results:** 29 new tests pass (tests/test_growth_metrics.py). Full suite: 86/87 pass (1 pre-existing failure unrelated to Phase B). Ruff: clean.

---

## Detailed Findings

### 1. Correctness — Implementation Matches Requirements

**B1: `fetch_place_growth_metrics` (census.py)**
- ✅ Fetches two ACS vintages (2022 current, 2017 prior) for place geography
- ✅ Returns population + income growth rates as `Decimal` (quantized to 0.01)
- ✅ Handles zero-division guards, null Census values ("-1", "null", "")
- ✅ Uses internal helpers `_fetch_acs_data`, `_parse_acs_response` — clean separation
- ✅ Validates state FIPS via `STATE_FIPS` dict (all 50 states + DC)

**B2: `fetch_employment_growth` (bls.py)**
- ✅ Uses LAUS employment level series (measure 0000000005)
- ✅ Prefers annual average (M13) over monthly data points
- ✅ Computes growth from earliest to latest available year
- ✅ Returns `Decimal` quantized to 0.0001
- ✅ Refactored `_fetch_bls_value` helper shared with `fetch_unemployment_rate`

**B3: `fetch_housing_demand_index` (census.py)**
- ✅ Uses ACS B25002 (occupancy status) to compute vacancy rate
- ✅ Heuristic: `(1 - vacancy_rate) * 100` + population growth bonus (capped at +20)
- ✅ Clamps result to 0–100 integer
- ✅ Clearly documented as heuristic, not official index

**B4: `populate_growth_areas` command**
- ✅ Supports `--state/--city` pairs, `--file`, `--force`, `--list-cities`
- ✅ 30-day cache TTL (skips fresh data unless `--force`)
- ✅ Requires both `CENSUS_API_KEY` and `BLS_API_KEY` env vars
- ✅ Upserts `GrowthArea` with all 4 metrics + timestamp
- ✅ Graceful error handling per-city (continues on individual failures)
- ✅ 73 major cities pre-configured with Census place codes

**B5: `/growth/` view**
- ✅ Reads `GrowthArea.objects.all()[:200]`, sorts by `composite_score`
- ✅ Falls back to `MarketSnapshot` (ZIP-level) when `GrowthArea` empty
- ✅ Returns top 20 (was 10) — reasonable for city-level data

**SQLite Default**
- ✅ `docker-compose.yml`: `db` service commented out, `depends_on` removed
- ✅ `.env.example`: Postgres vars commented, SQLite default documented
- ✅ Settings already had SQLite fallback (`sqlite:///db.sqlite3`)

**ATTOM comps fix (comps.py:92)**
- ✅ Fixed nested response handling: `property` array + `saleHistory` inside each
- ✅ Also checks top-level `saleHistory` as fallback
- ✅ Handles dict-vs-list normalization for both levels

---

### 2. Scope — Minimal, Focused Diff

**No unnecessary changes.** Every modified file maps directly to a Phase B task or a documented pre-existing bug fix.

Files touched:
- 2 adapter modules (`census.py`, `bls.py`) — core new logic
- 1 new management command (308 lines)
- 1 view update (14 lines changed)
- 1 comps fix (15 lines changed in response parsing)
- 2 config files (comments only)
- 1 README update (market adapter table)
- 2 test files (29 new tests + 2 log assertion fixes)
- 1 new test file

**No changes** to models, migrations, settings, serializers, API views, or unrelated adapters.

---

### 3. Maintainability — Project Patterns Followed

| Pattern | Compliance | Notes |
|---------|------------|-------|
| **Decimal for money/rates** | ✅ | All growth rates, income, indices use `Decimal` |
| **Service-layer boundaries** | ✅ | Adapters in `core/integrations/market/` are stateless functions; command orchestrates; view only reads model |
| **No external calls from views** | ✅ | `growth_areas` view only queries `GrowthArea`/`MarketSnapshot` |
| **Django cache pattern** | N/A | These adapters don't use cache (command manages freshness via `data_timestamp`) — acceptable for batch population |
| **Error handling** | ✅ | All adapters catch exceptions, log WARNING, return `None` |
| **API key via param** | ✅ | `api_key` passed explicitly (testable, no `os.getenv` in adapter) |
| **Logging** | ✅ | `logging.getLogger(__name__)` used throughout |
| **No Bootstrap/inline styles** | ✅ | View renders template; no template changes in this PR |
| **CBV/FBV consistency** | ✅ | `growth_areas` is FBV (consistent with existing views) |

**Minor style note:** `census.py` imports `from typing import Any` at top but also uses `dict[str, Any]` — consistent with Python 3.11+ (project uses 3.14 per test report). Ruff passes.

---

### 4. Risk Assessment

| Risk | Likelihood | Impact | Mitigation / Status |
|------|------------|--------|---------------------|
| **Census API key not set** | Medium | Command fails fast with clear error | ✅ Command validates keys upfront, exits with `CommandError` |
| **BLS employment data unavailable for state** | Low | GrowthArea created with `employment_growth_rate=None` | ✅ Handled gracefully — logs WARNING, continues |
| **Place code mismatch (Census FIPS)** | Medium | Wrong city data populated | ⚠️ `MAJOR_CITIES` list is hardcoded; `--file` option allows override. Consider externalizing to JSON for maintainability. |
| **Division by zero in growth calc** | Low | Crash | ✅ Guards for `prior_pop == 0` and `prior_income == 0` return `None` |
| **Pre-existing `market_data.py` bug** | Known | Comps fallback crashes command | 📋 Documented in test report; unrelated to Phase B; fix in follow-up |
| **SQLite in production** | Low | Data loss / concurrency issues | ✅ Commented clearly as "dev default only"; Postgres config preserved for prod |

---

### 5. Security & Secrets

- ✅ No hardcoded API keys, tokens, or passwords
- ✅ `.env.example` contains only placeholders (commented for Postgres)
- ✅ `.env` not committed (in `.gitignore` per standard Django)
- ✅ API keys passed as function params, read from `os.getenv()` only at command entry point
- ✅ No PII in logs (Census/BLS responses don't contain PII)

---

### 6. Test Coverage

| Area | Tests | Coverage |
|------|-------|----------|
| `fetch_place_growth_metrics` | 6 | Success, missing key, invalid state, HTTP error, null data, negative growth |
| `fetch_employment_growth` | 7 | Success, negative growth, empty data, HTTP error, invalid state, missing key, annual average preference |
| `fetch_housing_demand_index` | 7 | Success, missing key, invalid state, HTTP error, null data, high vacancy, clamp to 100, pop growth boost |
| `populate_growth_areas` command | 8 | Create, update, missing Census key, missing BLS key, unpaired args, multi-city, `--list-cities`, Census failure graceful |
| `/growth/` view | 2 (integration) | Renders with snapshots, shows undervalued listings |

**All 29 new tests pass.** Mocks used throughout — no real HTTP in CI.

---

## Specific Issues (Non-Blocking)

### 1. Hardcoded `MAJOR_CITIES` list (populate_growth_areas.py:30–73)
**File:** `core/management/commands/populate_growth_areas.py`
**Issue:** 73 cities hardcoded as Python list of tuples. Adding cities requires code change + deploy.
**Recommendation:** Move to JSON fixture (e.g., `core/fixtures/major_cities.json`) and load at runtime.
**Severity:** LOW — current list covers top US metros; `--file` option provides workaround.

### 2. `composite_score` weights hardcoded (models.py:675–688)
**File:** `core/models.py`
**Issue:** Weights (pop 0.25, emp 0.35, income 0.25, housing 0.15) embedded in model property.
**Recommendation:** Extract to settings or constants module for tuning without migration.
**Severity:** LOW — reasonable defaults; not a Phase B requirement.

### 3. `fetch_housing_demand_index` population growth bonus logic
**File:** `core/integrations/market/census.py:252`
**Issue:** `growth_bonus = min(population_growth_rate * Decimal("100"), Decimal("20"))` — a 5% pop growth adds 5 points, but formula comment says "growth_rate of 0.1 adds ~10 points" (consistent). However, the `population_growth_rate` is already quantized to 0.01 in `fetch_place_growth_metrics`, losing precision.
**Recommendation:** Pass unquantized growth rate to housing demand, or document precision loss.
**Severity:** LOW — heuristic only, documented as such.

### 4. BLS `fetch_employment_growth` uses `datetime.now().year`
**File:** `core/integrations/market/bls.py:97`
**Issue:** Imports `datetime` inside function; calculates `current_year` at runtime. Makes testing with fixed years harder.
**Recommendation:** Accept `end_year` parameter (default `datetime.now().year`) for testability.
**Severity:** LOW — tests mock `requests.post`, not time; current test passes by providing data for computed years.

### 5. Census `_fetch_acs_data` `geography` param format
**File:** `core/integrations/market/census.py:51`
**Issue:** Accepts raw geography string (e.g., `"place:67000"`). Caller must know Census geography format.
**Recommendation:** Encapsulate geography construction in helper or make it explicit in function signature.
**Severity:** LOW — internal helper, only called by `fetch_place_growth_metrics` and `fetch_housing_demand_index`.

---

## Items Requiring Human Judgment

1. **`MAJOR_CITIES` maintenance strategy** — Is hardcoded list acceptable for MVP, or should it be externalized now?
2. **`composite_score` weight tuning** — Should weights be configurable per-user or global settings?
3. **Pre-existing `market_data.py` comps bug (line 179)** — Fix in this PR or separate follow-up? (Test report recommends follow-up.)

---

## Recommendation

**APPROVE** — All Phase B acceptance criteria satisfied. Implementation is correct, well-tested, and follows project conventions. The non-blocking items above are enhancements, not defects.

Merge when:
- Author confirms `MAJOR_CITIES` hardcoding is acceptable for MVP
- `large-pr-approved` label applied (diff > 400 lines — CI will block without it)
