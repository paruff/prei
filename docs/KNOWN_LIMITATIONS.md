# Known Limitations — prei

> DORA AI Cap 3: This document is loaded as context before every code generation session.
> Agents read this file and do not make listed issues worse.
> Human-curated. Updated when new limitations are discovered or resolved.

---

## How to Use This File

**For agents:** Before generating code in any area listed below, read the limitation description.
If your implementation would worsen a listed issue, flag it in your PR rather than proceeding.

**For PMs:** When a limitation is fixed, remove it here and note it in the fix PR.

**For developers:** When you discover a new limitation, add it here immediately.
Format: `### [LIMIT-ID] Short description` followed by location, impact, workaround, and tracking issue.

---

## Active Limitations

### [LIMIT-01] FBI Crime Data Explorer (CDE) API — adapter returns dummy values

**Location:** `core/integrations/market/crime.py`

**Impact:** Crime scores shown in the UI are state-based dummy values (TX=2.5, CA=3.5, others=3.0), not real data. Users cannot make informed decisions using crime metrics.

**Workaround:** The UI labels the crime score as "placeholder — estimated from state averages." The existing `get_crime_score()` function signature is stable and backward-compatible; any future live adapter can replace the body without changing callers.

**Root cause:** The FBI CDE API at `api.usa.gov/crime/fbi/cde/` is gated behind `api.data.gov`, requiring a registered API key. A real key returns HTTP 404 on the same endpoints where `DEMO_KEY` gives meaningful error messages, suggesting either (a) incorrect endpoint path, (b) geography-level parameters that differ from the documentation, or (c) the CDE API has been superseded. SPIKE completed 2026-07-03; no viable path found in one session.

**Fix tracked in:** DECISION-2A (deferred). Not yet filed as a GitHub issue.

---

### [LIMIT-02] Housing Demand Index uses a vacancy-rate heuristic, not a real demand metric

**Location:** `core/integrations/sources/census.py` — `fetch_housing_demand_index()`

**Impact:** The index estimates demand from ACS vacancy data + population growth bonus, not from a genuine housing-demand survey or listing market data. Formula: `(1 - vacancy_rate) * 100 + up_to_20_points_population_growth_bonus`, clamped to [0, 100].

**Workaround:** Clearly labelled as "heuristic" in any UI display. The value is suitable for relative ranking (city A vs city B) but not as an absolute demand metric.

**Fix tracked in:** Not yet filed. A future phase could source a real demand index (e.g., Zillow market heat index, Realtor.com demand metrics) when an API becomes available.

---

### [LIMIT-03] CodeQL-driven removal of `exc_info=True` reduces debuggability

**Location:** `core/services/market_data.py` (8 calls), `core/integrations/market/schools.py` (1 call), `core/integrations/sources/attom_adapter.py` (2 calls)

**Impact:** `exc_info=True` was removed from 11 `logger.error()` calls because CodeQL flagged them as potential secret/PII leaks (exception messages could contain API keys in URLs or request data). These log lines no longer include tracebacks, making it harder to diagnose failures in those code paths.

**Workaround:** For alpha, developers can reproduce issues locally with `DEBUG=True` to get full tracebacks on stderr. Two other `exc_info=True` calls remain in `core/services/projections.py:269` and `core/management/commands/fetch_hud_source_index.py:139` — these were not flagged because they log to `logger.warning()` (less sensitive contexts). Do not add `exc_info=True` back to the affected calls without a sanitisation layer.

**Fix tracked in:** Post-MVP — implement a `sanitized_exc_info` helper that redacts URLs, API keys, and PII from exception messages before logging.

---

### [LIMIT-05] SQLite is the default database; Postgres reserved for post-MVP production

---

### [LIMIT-06] Production settings tests must explicitly set secure defaults to override `.env`

**Location:** `tests/test_production_settings.py`

**Impact:** The test subprocess imports `investor_app.settings` directly, which reads `.env` via `environ.Env.read_env()`. Since `.env` sets `SECURE_SSL_REDIRECT=False` for local HTTP development, the test must explicitly pass expected secure values in its env dict to verify the `if not DEBUG:` block's defaults. Without this, the test reflects `.env` values, not the code defaults.

**Workaround:** As of commit fixing this issue, the two affected test calls (`test_debug_false_enforces_secure_defaults` and `test_debug_false_enforces_secure_defaults_in_production`) explicitly pass `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, and `SECURE_HSTS_INCLUDE_SUBDOMAINS` in their env dicts. If `.env` gains new security-related entries, add them to the test's explicit env as well.

**Fix tracked in:** A deeper fix would be to have the test subprocess override `env_file` or skip `.env` reading entirely for the test scenario. However, that would require changing `settings.py`, which has its own risks. Current workaround is acceptable.

---

### [LIMIT-08] GrowthArea vs MarketSnapshot split — inconsistent fallback between HTML view and API

**Location:** `core/views.py:672` (HTML `growth_areas()`), `core/api_views.py:225` (API `growth_areas_list()`)

**Impact:** The HTML `/growth/` page and the `/api/growth-areas/` endpoint both serve growth-area data, but they diverge on fallback behavior:
- **HTML view** falls back to `MarketSnapshot` (ZIP-level) when `GrowthArea` (city-level) is empty.
- **API endpoint** returns an empty array with `"No growth data available"` when `GrowthArea` is empty — no `MarketSnapshot` fallback.

This means a user who runs the API pre-`populate_growth_areas` gets empty results, while the HTML page still shows data. After `populate_growth_areas` is run, both use `GrowthArea` and are consistent.

**Root cause:** DECISION-1 specified that both endpoints should read from `GrowthArea` as the primary source. The HTML view's `MarketSnapshot` fallback was kept for transitional backward compatibility during alpha while `populate_growth_areas` might not have been run yet. The API was built without this transitional fallback, creating the inconsistency.

**Workaround:** Run `python manage.py populate_growth_areas --list-cities` to confirm city data is loaded. If populated, both endpoints use `GrowthArea` and are consistent. If not yet populated, the HTML view still serves `MarketSnapshot`-derived data while the API returns empty.

**Recommended fix (post-MVP):** Either (a) add `MarketSnapshot` fallback to the API endpoint for consistency with the HTML view, or (b) remove the `MarketSnapshot` fallback from the HTML view and document that `populate_growth_areas` must be run before growth features are available. Option (b) is cleaner long-term — `GrowthArea` is a semantic superset of `MarketSnapshot` for the growth use case.

**Fix tracked in:** Not yet filed. Depends on whether the alpha deployment runs `populate_growth_areas` automatically.

---

### [LIMIT-09] Remaining `exc_info=True` calls not covered by CodeQL fix

**Location:** `core/services/projections.py:269`, `core/management/commands/fetch_hud_source_index.py:139`

**Impact:** Two `exc_info=True` calls remain in the codebase. `projections.py` logs IRR computation failures (no PII risk — inputs are Decimal cashflows). `fetch_hud_source_index.py` logs a file-load failure with the exception type and message, including `exc_info=True` (low risk — file path and OS error only).

**Workaround:** These are low-risk because they do not log URLs, request data, or user input. However, if these code paths are ever refactored to include user-supplied values in the log message, `exc_info=True` should be replaced with a sanitised alternative.

**Fix tracked in:** Not yet filed. Inclusion in the post-MVP sanitised-logging helper (see LIMIT-03) is recommended.

---

### [LIMIT-10] PipelineProperty address fields are denormalized — become stale if source record changes

**Location:** `core/models.py` — `PipelineProperty.address`, `PipelineProperty.address_hash`

**Impact:** When PipelineProperty is created from VRM or ForeclosureProperty, the address is copied (denormalized) onto the PP record. If the source record is later updated by a re-scrape, the PP address becomes stale. There is no auto-sync mechanism in alpha.

**Workaround:** Users should be aware that pipeline property addresses reflect the state at creation time. A future `sync_from_source` management command or signal-based approach could keep them current.

**Fix tracked in:** Post-MVP — backlog.

---

### [LIMIT-11] Yield-based screening skipped for non-VRM source types

**Location:** `core/services/screening.py` — `_eval_gross_yield()`, `_eval_price_to_rent_ratio()`

**Impact:** Gross yield and price-to-rent ratio screening criteria require a rent estimate. Only VrmProperty has `projected_monthly_rent`. ForeclosureProperty, county records, and manual entries have no rent data, so these criteria are silently skipped with a note. No Rentcast integration exists to fill the gap.

**Workaround:** Yield-based criteria are effectively VRM-only in alpha. Adding a Rentcast adapter (or other rent-estimate API) would enable yield screening for all source types.

**Fix tracked in:** Not yet filed.

---

### [LIMIT-12] Newly acquired Property records are incomplete at creation

**Location:** `core/services/pipeline.py` — `convert_to_property_record()`

**Impact:** When a PipelineProperty is converted to a Property record via the closing view, the Property is created with minimal fields (address, purchase_price). Fields like sqft, monthly_rent_gross, loan details, and property_type are either defaulted or empty. Financial analysis will be invalid until the user completes the record in Portfolio.

**Workaround:** After acquisition, users should navigate to Portfolio and edit the new Property record to fill in sqft, rent, loan terms, etc. The portfolio dashboard shows an "awaiting completion" banner for incomplete properties.

**Fix tracked in:** Post-MVP — could pre-fill more fields from pipeline/underwriting data.

---

### [LIMIT-13] AuctionAlert not wired to PipelineProperty

**Location:** `core/models.py` — `AuctionAlert`

**Impact:** The AuctionAlert model exists but is not connected to PipelineProperty. Users cannot configure alerts for specific pipeline properties (e.g., "notify me when auction date changes"). This is a known gap from the original design.

**Workaround:** Manually monitor auction dates via the pipeline detail view. No automated notifications.

**Fix tracked in:** Backlog — post-MVP.

---

### [LIMIT-14] Leasing pipeline is tenant-acquisition tracking only

**Location:** `core/models.py` — `LeasingPipelineProperty`

**Impact:** The leasing pipeline tracks tenant acquisition (listing → lease signed → move-in). It does not cover ongoing property management: maintenance requests, rent collection, lease renewals, or tenant communications. These are planned for Phase 3.

**Workaround:** After a lease is signed and the property is stabilized, users should manage ongoing operations in Portfolio. The leasing pipeline is specifically for pre-lease and move-in tracking.

**Fix tracked in:** Phase 3 (not yet scheduled).

---

### [LIMIT-15] Screening re-run on criteria change is synchronous

**Location:** `core/views.py` — `pipeline_screening_settings()`

**Impact:** When a user updates screening criteria, the view re-screens all ACTIVE pipeline properties at DISCOVERED or SCREENING stage synchronously within the HTTP request. For users with many pipeline properties, this could cause noticeable page load delays. There is no background task / Celery integration in alpha.

**Workaround:** Keep the number of active pipeline properties manageable (< 100). For larger portfolios, the re-screen count is shown in the success message so users are aware of how many properties were evaluated.

**Fix tracked in:** Post-MVP — add Celery/background-task support for re-screening.

---

### [LIMIT-16] No multi-user pipeline sharing

**Location:** All pipeline views and `PipelineProperty` model

**Impact:** Pipeline property ownership is per-user (`ForeignKey(User)`). There is no team-based sharing — users on the same team cannot view or manage each other's pipeline entries. This is a deliberate simplification for alpha.

**Workaround:** Users can share information manually. A future phase could add team-based access control similar to Property sharing.

**Fix tracked in:** Post-MVP — backlog.

---

### [LIMIT-17] GACS-based screening requires pre-populated GACS scores

**Location:** `core/services/screening.py` — `_eval_gacs_score()`

**Impact:** The `min_gacs_score` screening criterion evaluates a property's market Growth Area Composite Score. If GACS scores have not been populated (via `populate_growth_areas` management command), no GrowthArea record exists for the property's state+city, and the criterion is silently skipped with a note. Users who configure a min_gacs_score but haven't populated growth data will see the criterion ignored.

**Workaround:** Run `python manage.py populate_growth_areas` to populate GACS scores. The criterion is skipped (with a note) until scores are available.

**Fix tracked in:** Could be improved by checking for GACS data availability in the UI. Not yet filed.

---

### [LIMIT-19] GrowthArea.rent_growth_rate field exists but is never populated

**Location:** `core/models/growth.py` — `GrowthArea.rent_growth_rate` field

**Impact:** The field is declared and has a help text suggesting it comes from Census ACS, but no code path populates it. It is not displayed in any template, not included in GACS, and has no data source wired to it. Future agents seeing the field may assume rent growth data is available when it is not.

**Workaround:** None. The field stays null until a rent growth data source is integrated (HUD FMR longitudinal data or ACS B25064 series).

**Fix tracked in:** GACS-FMR-1 — wire HUD FMR or ACS gross rent data into GrowthArea.

---

## Resolved Limitations

### [LIMIT-R01] Docker container permissions — `app` user could not write `db.sqlite3`

**Fixed in:** `Dockerfile` line 49 — changed `chown -R app:app /app/.runtime` to `chown -R app:app /app`.

**Impact before fix:** The container ran as `app` user, but `db.sqlite3` at `BASE_DIR` was owned by root. Attempts to write to the database caused a `PermissionError`, making the container non-functional without volume-mount workarounds.

**Fix date:** 2026-07-03 (included in PR #196).

**Note:** The fix grants the `app` user write access to the entire `/app` tree, not just `/app/.runtime`. This is acceptable for alpha. If a finer-grained permission model is needed later (defence in depth), create a dedicated `/app/data/` subdirectory and chown only that directory.

### [LIMIT-R02] GrowthArea composite_score was a Python @property, not a DB column

**Fixed in:** GrowthArea model refactored to store composite_score as a persisted DecimalField.

**Impact before fix:** Sorting GrowthAreas by composite_score happened in Python memory via sorted(), which would not scale to thousands of entries. No DB index could support this sort, and pagination queries could not filter/sort by score on the database side.

**Fix date:** 2026-07-08 (models refactored)

**Note:** Promoted to persisted `DecimalField`, computed on `save()`. DB-level `.order_by('-composite_score')` used in growth_areas view (lines 701, 733). GACS scores are now fully queryable and sortable at the database level.
