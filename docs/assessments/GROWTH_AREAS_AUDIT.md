# Growth Areas — Comprehensive Audit

> **Date:** 2026-07-07
> **Scope:** All Growth Area Explorer logic, data sources, templates, views, models, tests

---

## 1. Architecture Overview

```
User clicks "Analyze State"
  │
  ▼
growth_explorer view (POST)
  │
  ├─ 1. discover_places_in_state()  ─── Census API, single query for top 10 places
  │
  ├─ 2. FREDAdapter().fetch_state_employment_growth()  ─── FRED {STATE}NA series
  │
  ├─ 3. For each place (up to 10):
  │     ├─ fetch_place_growth_metrics()  ─── 2× Census ACS calls (current + prior vintage)
  │     ├─ fetch_housing_demand_index()  ─── 1× Census ACS call
  │     └─ upsert GrowthArea row
  │
  ├─ 4. Sort results by composite_score DESC
  │
  └─ 5. Render growth_explorer.html with results table
```

**Total API calls per analysis:** 1 (discover) + 1 (FRED) + (10 × 3 Census) = **32 calls**

---

## 2. Data Sources

### 2.1 Census ACS (American Community Survey)
- **Endpoint:** `api.census.gov/data/{vintage}/acs/acs5`
- **Auth:** `CENSUS_API_KEY` env var (free at api.census.gov)
- **Vintage auto-detection:** `get_acs_vintages()` queries `/data.json`, caches result
  - Current: latest available 5-year (e.g., 2024)
  - Prior: 3-5 years earlier (e.g., 2021)
  - Fallback: 2023/2019 if API unreachable
- **Variables used:**
  - `B01001_001E` — Total population (required)
  - `B19013_001E` — Median household income (required)
  - `B25001_001E` — Total housing units (optional)
- **Queries per analysis:** 21 (1 discover + 10 places × 2 vintages) — down from 41 after 20→10 limit
- **Timeout:** 15s per call (down from 30s)
- **Retry:** 3 attempts with 2s/4s backoff
- **Rate limit:** None documented; generous

### 2.2 FRED (Federal Reserve Economic Data)
- **Endpoint:** `api.stlouisfed.org/fred/series/observations`
- **Auth:** `FRED_API_KEY` env var (free at fred.stlouisfed.org)
- **Series:** `{STATE}NA` — "All Employees: Total Nonfarm" (CES survey)
  - e.g., `TXNA`, `CANA`, `FLNA`
- **Growth calculation:** Annual averages over 5 years, earliest vs latest year
- **Rate limit:** 120 req/min — no practical limit for this use case
- **Timeout:** 15s
- **Fallback:** Returns `None` → view uses `Decimal("0")`

### 2.3 BLS (Deprecated — replaced by FRED)
- **Status:** Removed from all growth analysis paths
- **Reason:** Free tier limited to 25 req/day — exhausted after a single state analysis
- **Adapter retained:** `core/integrations/market/bls.py` still exists for backward compat
- **Tests retained:** `BlsEmploymentGrowthTest` tests the module directly

---

## 3. Model: GrowthArea

**File:** `core/models.py`

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `state` | CharField(2) | No | Two-letter state code |
| `city_name` | CharField(100) | No | Place name without state |
| `metro_area` | CharField(100) | Yes | Currently same as city_name |
| `population_growth_rate` | Decimal(6,2) | **No** | Growth as fraction (0.05 = 5%) |
| `employment_growth_rate` | Decimal(6,2) | Yes | Migration 0021 made nullable |
| `median_income_growth` | Decimal(6,2) | **No** | Growth as fraction |
| `housing_demand_index` | IntegerField | Yes | 0-100 scale |
| `supply_constraint_index` | IntegerField | Yes | 0-100 scale (GA-6, migration 0022) |
| `data_timestamp` | DateTimeField | Yes | When data was last refreshed |
| `created_at/updated_at` | auto | — | Standard timestamps |

**Unique constraint:** `(state, city_name)` — one row per city per state

**Known gap:** `population` is NOT stored — carried in template context only. On re-render, population data is lost. `composite_score` is a `@property`, not a DB field — computed at render time, cannot be sorted in DB.

---

## 4. Views

### 4.1 `growth_explorer` (main analysis page)

| Aspect | Status | Notes |
|--------|--------|-------|
| GET → form | ✅ | Renders state picker |
| POST → error | ✅ | Missing key, invalid state, no places |
| POST → success | ✅ | Creates/updates GrowthArea rows |
| API key detection | ✅ | Census required; FRED optional |
| FRED status | ✅ | Info banner when FRED key missing |
| Progress feedback | ✅ | AJAX overlay with stages + timer |
| Timeout handling | ✅ | 130s timeout with auto-retry |
| Slow API fallback | ✅ | 15s timeout per call, 3 retries |
| Bootstrap classes | ❌ | Templates use Bootstrap (policy violation) |

### 4.2 `growth_areas` (cached results page)

Reads from `GrowthArea.objects.all()[:200]`, falls back to `MarketSnapshot`.
Sorts by `composite_score` in Python memory (200 rows is fine).

---

## 5. Templates

### 5.1 `growth_explorer.html`
- **AJAX form submission** — fetch() with AbortController
- **Loading overlay** with 5 stages and elapsed timer
- **Results table** with composite score, growth rates, action links
- **Empty state** with troubleshooting guidance
- **Error states** for missing keys, invalid state, no places

### 5.2 `growth_areas.html`
- Simple table of previously analyzed growth areas
- Links to Explorer for new analysis
- Lighter UI — no loading overlay needed

### 5.3 Policy Violations
- **Bootstrap classes** throughout both templates (`btn`, `card`, `d-flex`, `row`, `col-md-*`)
- **Inline CSS** in `growth_explorer.html` (loading overlay styles in `<style>` block)
- **Hardcoded hex colors** — CSS variables used in inline styles but some fallbacks hardcoded

---

## 6. Composite Score Formula

**File:** `core/models.py` — `GrowthArea.composite_score` (property)

| Component | Weight | Notes |
|-----------|--------|-------|
| Population growth | 0.20 | 5-year fractional growth |
| Employment growth | 0.35 | State-level from FRED |
| Income growth | 0.20 | 5-year median income growth |
| Housing demand | 0.10 | 0-100 index |
| Supply constraint | 0.15 | 0-100 index (GA-6) |

Score = weighted sum of components, each normalized to 0-100 scale.
Growth rates (fractions) converted: `rate * 100` to get percentage, then weight applied.

---

## 7. Supply Constraint Index (GA-6)

**Function:** `compute_supply_constraint_index(pop_growth, housing_units_growth)`

Formula: `diff = pop_growth - housing_units_growth`
Index: `max(0, min(100, round(diff * 500 + 50)))`

- Gap of 0% → score 50 (neutral)
- Gap of +10% → score 100 (tight supply)
- Gap of -10% → score 0 (oversupply)

**Notes:**
- Housing unit variable (`B25001_001E`) is optional — if missing, supply constraint is None
- Calibration heuristic: ±10% gap drives full 0-100 range
- No documented calibration rationale

---

## 8. Known Issues

### 🔴 Critical (blocks functionality)

None currently.

### 🟡 High (should fix next)

| Issue | Location | Impact |
|-------|----------|--------|
| No `population` field in GrowthArea model | `core/models.py` | Population lost on re-render; only available immediately after analysis |
| Bootstrap classes in templates | Both .html files | Policy violation (AGENTS.md hard rule) |
| API keys in plain env vars | `.env` | Standard for local dev but not production-grade |
| `composite_score` is a @property | `core/models.py` | Cannot sort in DB; must load all rows into memory |

### 🔵 Medium (nice to have)

| Issue | Location | Impact |
|-------|----------|--------|
| No background processing | `core/views.py` | Browser waits 20-60s for response |
| Inline CSS in template | `growth_explorer.html` | Mixes presentation with markup |
| No pagination on growth_areas | `core/views.py` | Fixed at 200 rows |
| No cache for FRED nonfarm data | FRED adapter | Same state analyzed multiple times = repeated calls |
| `_parse_acs_response` null check | `census.py:424` | Null/suppressed `B25001_001E` not handled as optional in all paths |

### ⚪ Low (cosmetic/minor)

| Issue | Location |
|-------|----------|
| `import time` inside function body | `census.py:336`, `fred_adapter.py:333` |
| `import datetime` inside function body | `bls.py:143`, `fred_adapter.py:333` |
| `logger.warning(f"...")` f-string | `fred_adapter.py:267` |
| Stale `ACS_VINTAGE`/`ACS_VINTAGE_PRIOR` constants | `census.py:30-31` |
| Place codes hardcoded in management command | `populate_growth_areas.py:32-74` |

---

## 9. Test Coverage

### 9.1 Unit Tests (mocked, fast)

| Test File | Tests | Status | Notes |
|-----------|-------|--------|-------|
| `tests/test_growth_metrics.py` | 29 | ✅ All pass | Census, BLS, housing demand, command |
| `core/tests/test_growth_explorer.py` | 11 | ✅ All pass | View GET/POST/errors |
| **Total unit** | **40** | ✅ | |

### 9.2 Integration Tests (live API, slow)

| Test File | Tests | Status | Notes |
|-----------|-------|--------|-------|
| `core/tests/test_integration_growth_explorer.py` | 38 | ✅ 38/38 pass | ACS vintages, place discovery, growth metrics, FRED employment, supply constraint, end-to-end for TX/VA/CA |
| **Total integration** | **38** | ✅ | Requires `CENSUS_API_KEY` + `FRED_API_KEY` |

### 9.3 Test Gaps

| Missing Test | Risk | Priority |
|-------------|------|----------|
| `_parse_acs_response` with null optional var | Medium — C1 from review | Medium |
| `compute_supply_constraint_index` standalone | Low — tested indirectly | Low |
| View POST with timeout | Low — simulated via mock | Low |
| FRED adapter `fetch_state_employment_growth` unit test | Low — covered by integration | Low |

---

## 10. Security Assessment

| Check | Status | Notes |
|-------|--------|-------|
| API keys in env vars | ✅ Standard practice |
| No hardcoded secrets | ✅ Pre-commit gitleaks + detect-private-key |
| No PII in URLs | ✅ State/city in query params |
| Address in log context | ⚠️ `address1=` logged at INFO in ATTOM adapter |
| CSRF protection | ✅ Django middleware |
| XSS (template escaping) | ✅ Django auto-escapes; no `|safe` on user input |
| SQL injection | ✅ Django ORM |
| No auth on growth pages | ⚠️ `growth_explorer` and `growth_areas` are public |

---

## 11. Performance

| Metric | Current | Acceptable? |
|--------|---------|-------------|
| Time per Census call | ~2-5s (median) | ✅ |
| Time per full analysis (10 places) | ~30-60s | ⚠️ Borderline |
| Time per full analysis (worst case) | ~4 min (all retries) | ❌ |
| Memory per analysis | ~50MB | ✅ |
| DB reads (results page) | <200 rows | ✅ |
| DB writes (per analysis) | 10 rows | ✅ |

### Bottlenecks
1. Sequential Census calls — 21 sequential requests × 2-5s = 40-105s
2. No parallelization — each place's 2 vintage calls are sequential
3. No HTTP/2 multiplexing — `requests` library opens new connection per call

---

## 12. Dependency Graph

```
growth_explorer view
  ├── core/integrations/market/census.py
  │     ├── requests.get() → api.census.gov
  │     ├── get_acs_vintages()
  │     │     └── requests.get() → api.census.gov/data.json
  │     └── _fetch_acs_data() (called 21 times)
  │           └── requests.get() → api.census.gov/data/{vintage}/acs/acs5
  │
  ├── core/integrations/sources/fred_adapter.py
  │     └── FREDAdapter.fetch_state_employment_growth()
  │           └── get_series_observations()
  │                 └── requests.get() → api.stlouisfed.org/fred/series/observations
  │
  └── core/models.py (GrowthArea)
        └── composite_score (property)
              └── compute_supply_constraint_index()
```

No circular dependencies. Layer boundaries respected (no views calling models directly, no adapters calling views).

---

## 13. UX Flow Analysis

### Current Flow
1. User navigates to `/growth-explorer/` → sees state picker + "How It Works" card
2. Selects state from dropdown
3. Clicks "Analyze State"
4. **Loading overlay** appears with animated stages:
   - "Discovering top places in state..." (0-5s)
   - "Fetching population and income data..." (5-15s)
   - "Analyzing growth metrics..." (15-45s)
   - "Computing composite scores..." (45-60s)
5. Results table renders with 10 cities sorted by score
6. User can click "View Foreclosures" to see VRM properties in that state

### UX Score: 7/10

**Strengths:**
- Clear progress feedback during long wait
- Timed stage transitions give sense of progress
- Graceful timeout recovery (130s)
- Specific error messages per failure mode
- FRED key status indicator

**Weaknesses:**
- 30-60 second wait is unavoidable without async architecture
- No parallel API calls — sequential makes it slow
- Results page doesn't persist population data
- Bootstrap classes inconsistent with project design system

---

## 14. Recommendations

### Immediate (next sprint)
1. Add `population` field to GrowthArea model — persisted data won't be lost
2. Move `composite_score` to DB field with precomputation — enables DB-native sorting
3. Replace Bootstrap classes with project design system tokens — policy compliance

### Short-term (next 2 sprints)
4. Convert analysis to background task + polling — eliminates browser timeout risk
5. Parallelize Census calls (places are independent) — cuts analysis time by 3-5×
6. Add FRED adapter caching — same state analyzed twice = no redundant API calls

### Medium-term (next quarter)
7. Add auth to growth pages — currently public, should respect user scoping
8. Add pagination/infinite scroll to growth_areas results
9. Consider Redis cache for ACS vintages across workers (currently in-memory, per-worker)
10. Add CSV export of analysis results

---

## 15. Summary

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Functionality** | ✅ 9/10 | All core features work. BLS→FRED fixed rate limiting. |
| **Test Coverage** | ✅ 8/10 | 40 unit + 38 integration tests. Gaps in optional-var null handling. |
| **UX/UI** | 🟡 7/10 | Good feedback during long wait, but Bootstrap violation + no population persistence. |
| **Security** | ✅ 8/10 | Standard Django practices. Public pages need auth consideration. |
| **Performance** | 🟡 6/10 | 30-60s analysis is slow. Sequential calls are bottleneck. No parallelization. |
| **Maintainability** | ✅ 8/10 | Clean layer separation. Good docstrings. Some inline imports need fixing. |
| **Dev Experience** | ✅ 9/10 | Integration tests against live APIs. Mock tests for CI. |
