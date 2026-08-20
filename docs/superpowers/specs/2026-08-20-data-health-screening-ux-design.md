# Phase 3 Design: Data Health & Screening UX

**Date**: 2026-08-20
**Status**: Approved for implementation
**Audit reference**: docs/DEVEX_PLAN.md (P0 Property Discovery + P1 Screening UX)

---

## 1. Problem Statement

Data scrapers run in background threads with no visibility into success/failure. The screening settings page lacks a way to preview filter impact before saving. There is no version history for screening criteria changes.

---

## 2. Architecture

### 2.1 Refresh All Sources Button

**Location:** `templates/system.html` (Data Operations section)

Add a single "Refresh All Sources" button that triggers all ingestion tasks (HUD, USDA, counties) in parallel background threads. The page polls `DataSourceHealth` every 2 seconds via fetch, updating each source row with a spinner → checkmark/error transition.

**Endpoint:** `POST /system/refresh-all/` → returns `{status: "started"}` immediately. Triggers HUD, USDA, and county ingestion in background threads.

**Polling:** JS polls `GET /system/health-json/` every 2 seconds. Returns `[{source_name, last_run, record_count, status, consecutive_errors}, ...]`. Poll stops when all sources show `status != "unknown"` or after 60 seconds.

### 2.2 Circuit Breaker (DataSourceHealth-based)

**Model change:** Add `consecutive_errors` field to `DataSourceHealth`:
```python
consecutive_errors = models.IntegerField(default=0)
```

**Behavior:**
- On success: `consecutive_errors = 0`, `status = "ok"`
- On failure: `consecutive_errors += 1`, `status = "error"`, `error_message = str(exc)`
- If `consecutive_errors >= 3`: skip source, log "circuit open for {source}"
- Migration: `core/migrations/00XX_add_consecutive_errors.py`

**Retry logic in scrapers:**
- 30-second timeout per HTTP request
- 1 retry with 2s exponential backoff
- After retry fails: update `DataSourceHealth` with error, increment counter

### 2.3 E2E Tests for Data Health

**File:** `tests/e2e/test_data_health_e2e.py`

Tests:
1. `test_system_page_renders` — load `/system/`, verify "Data Source Health" heading
2. `test_data_source_table_structure` — verify table has Source/Last Run/Records/Status columns
3. `test_refresh_all_button_exists` — verify button is visible and clickable
4. `test_refresh_triggers_background_jobs` — click button, verify message appears

### 2.4 Screening Filter Bar (Vanilla JS)

**Location:** `templates/pipeline/screener.html`

Add filter controls above the results table:
- Price range (min/max inputs)
- Minimum gross yield (%)
- Maximum price-to-rent ratio
- Minimum bedrooms
- State dropdown
- Property type checkboxes

Each filter change triggers `fetch('/pipeline/screener/filter/')` with query params. Returns HTML fragment (table body). Replace `#screener-results` via `innerHTML`. Filters persist via URL query params (shareable/bookmarkable).

**Endpoint:** `GET /pipeline/screener/filter/?min_price=X&max_price=Y&...` → returns rendered HTML fragment of filtered table rows.

### 2.5 Preview Impact Button

**Location:** `templates/pipeline/screening_settings.html`

Add "Preview Impact" button below the form (before Save). On click:
1. Read current form values
2. `fetch('/pipeline/screening/preview/', {method: 'POST', body: formData})`
3. Display result: "X of Y properties would pass screening (Z killed)"

**Endpoint:** `POST /pipeline/screening/preview/` → returns `{total: N, passed: N, killed: N}`

### 2.6 Auto-Version on Save

**New model:** `ScreeningCriteriaVersion`
```python
class ScreeningCriteriaVersion(models.Model):
    criteria = models.ForeignKey(ScreeningCriteria, on_delete=models.CASCADE, related_name='versions')
    snapshot = models.JSONField()  # serialized criteria fields
    created_at = models.DateTimeField(auto_now_add=True)
```

**Behavior:** On every save of `ScreeningCriteria`, create a `ScreeningCriteriaVersion` with a JSON snapshot of all fields. Show last 5 versions on the settings page.

**Migration:** `core/migrations/00XX_screeningcriteriaversion.py`

---

## 3. File Map

| File | Change |
|------|--------|
| `core/models/pipeline.py` | Add `consecutive_errors` to `DataSourceHealth`; add `ScreeningCriteriaVersion` |
| `core/views/__init__.py` | Add `refresh_all_sources`, `health_json`, `screening_preview`, `screener_filter` views |
| `core/urls.py` | Add 4 new URL patterns |
| `templates/system.html` | Add Refresh All button + polling JS |
| `templates/pipeline/screener.html` | Add filter bar + fetch JS |
| `templates/pipeline/screening_settings.html` | Add Preview Impact button + version history |
| `tests/e2e/test_data_health_e2e.py` | New E2E tests |
| `tests/e2e/test_screening_ux_e2e.py` | New E2E tests |

---

## 4. Out of Scope (Deferred)

- WebSocket/real-time updates (polling is sufficient for now)
- HTMX adoption (vanilla JS per user preference)
- Scraper implementation for new sources (only hardening existing ones)

---

## 5. Acceptance Criteria

1. "Refresh All Sources" button triggers all ingestion tasks and shows live status
2. Circuit breaker skips sources with 3+ consecutive errors
3. Screening filter bar filters results without page reload
4. Preview Impact shows kill count without saving
5. Every screening criteria save creates an automatic version
6. All new features covered by E2E tests

---

## 6. Dependencies

- Existing `DataSourceHealth` model and `DataSourceHealthMonitor`
- Existing `ScreeningCriteria` model and `pipeline_screening_settings` view
- Existing `pipeline_screener` view (will be extended with filter endpoint)
- Playwright E2E test harness from Phase 1
