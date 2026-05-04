## Plan: Real Estate Investment Scanner MVP

A phased plan to evolve the current Django app into a hands-free investment scanner. Focus first on a solid foundation (data, KPIs, dashboard), then add analytics, automation, and integrations. Each step maps to specific modules and files for clarity while keeping precision with Decimal math and robust testing.

### Steps
1. Phase 1 — Foundation: Solid data + filters + basic scoring
2. Phase 2 — Intelligence: Advanced analytics + reports
3. Phase 3 — Automation: Pipelines + alerts + recommendations
4. Phase 4 — Pro Tools: Portfolio modeling + collaboration
5. Phase 5 — Expansion: Partnerships + APIs + mobile

### Further Considerations
1. Data sources: Choose compliant MLS/APIs vs. scraping; add adapters.
2. Background tasks: Queue (Celery/Django-Q) and Redis; compose services.
3. Precision: Decimal boundaries, numpy-financial conversions, guardrails.

## Plan: Phase 1 — Foundation

Establish core listing ingest, filtering, V1 scoring, alerts, and a usable dashboard.

### Steps
1. Ingest Model & Store: Add `Listing` in `core/models.py` (source, address, price, beds/baths, sq_ft, property_type, URL, posted_at); migrations.
2. Scraper Adapters: Create `core/integrations/sources/` with pluggable adapters (e.g., `realtor.py`, `zillow.py`) returning normalized `Listing` dicts; management command `fetch_listings` in `core/management/commands/`.
3. Filters & Query API: Add filter serializer/forms in `core/views.py` or `core/filters.py` for price, type, beds, location; expose filtered queryset to dashboard.
4. V1 Scoring: Implement `finance/utils.py` `score_listing_v1(listing)` using price per sq ft, freshness, basic heuristics; add unit tests under `core/tests/test_scoring.py`.
5. Alerts: Add `core/services/alerts.py` to evaluate filters+score thresholds and enqueue notifications (email/SMS placeholders); basic settings in `investor_app/settings.py`.
6. Dashboard: Extend `templates/dashboard.html` to show filtered listings, V1 score, quick-save; add `core/views.py` list view; integration tests `core/tests/test_views_listings.py`.
7. Env + CI: Ensure `.env.example` includes API keys, rate limits; CI logs per Copilot instructions; verify `pytest -q` covers unit and integration.

## Plan: Phase 2 — Intelligence Layer

Add analytics: deal analyzer KPIs, neighborhood insights, comparative analysis, and property reports.

### Steps
1. Deal Analyzer: Extend `finance/utils.py` with ROI, cap_rate, cash_on_cash, rehab estimates, projected cash flow; guard divide-by-zero; strict Decimal; unit tests `core/tests/test_deal_analyzer.py`.
2. Neighborhood Insights: Add `core/integrations/market/` adapters (comps, rent estimates, crime, schools); normalize to `MarketSnapshot` model in `core/models.py`; integration tests gated in CI.
3. CMA Engine: Implement `core/services/cma.py` to find undervalued properties via comps and pricing trends; tests with fixtures under `core/tests/`.
4. Interactive Reports: Create `templates/property_report.html` and `core/views.py` detail view; include due diligence pack (history, tax info, schools, crime, rent estimates) from integrations.
5. Trend Series: Build monthly time-series for rents/expenses in `core/models.py` helpers; portfolio summaries in `core/services/portfolio.py`; charts via minimal JS or server-side summaries.
6. Logging & Errors: Add structured logs around analytics pipelines in `investor_app/settings.py` logging config; tests for error paths and safe fallbacks.

## Plan: Phase 3 — Automation & Efficiency

Make workflows hands-free: scheduled scans, lead organization, AI suggestions, and integrations.

### Steps
1. Schedulers: Add `fetch_listings` cron-like command and optional Celery/Django-Q worker; extend `docker-compose.yml` with `worker` and `redis`.
2. Lead Organization: Implement `core/services/ranking.py` for smart ranking beyond V1; group by score, category, urgency; list views in `core/views.py`.
3. Recommendations: Add `core/services/recommendations.py` to suggest deals using user behavior and saved deals; tests with synthetic data.
4. Workflow Integrations: Create adapters `core/integrations/crm/` (webhook/email/calendar); optional endpoints under `investor_app/urls.py`; gated integration tests.
5. Saved Search Tuning: Add `core/models.py` `SavedSearch` with learning adjustments; nightly job to tweak filters based on outcomes.

## Plan: Phase 4 — Pro-Level Tools

Support advanced investors, teams, and portfolio modeling.

### Steps
1. Portfolio Modeling: Add scenarios in `core/services/portfolio.py` for multi-deal what-if; UI forms and views; tests.
2. Risk Profiles: Configurable weighting for risk tolerance and rehab comfort in `investor_app/settings.py`; apply in ranking and analyzer.
3. Bulk Uploads: Management command and view to analyze MLS exports/CSV; validate schemas; performance optimizations.
4. Collaboration: Sharing models (teams), notes, and projections; permissions/groups in auth; export CSV/PDF endpoints.
5. Security & Ops: Harden production settings, add monitoring hooks, and audit trails; expand CI and perf tests.

## Plan: Phase 5 — Expansion & Monetization

Scale with partnerships, APIs, and mobile.

### Steps
1. Premium Data: Integrate paid tax/zoning/land-use providers with `core/integrations/premium/`; feature flags for access.
2. Marketplace: Models and views for connecting buyers, agents, lenders, contractors; simple moderation and ratings.
3. API Access: Add `investor_app/urls.py` REST endpoints (DRF optional) for listings and analytics; rate limiting.
4. Mobile App: Ship a minimal API-compatible mobile client; push notifications; reuse alert service.

## Further Considerations
1. Integrations: Option A—APIs (preferred, compliant). Option B—Scrapers (respect ToS, robust error handling). Option C—Data vendors (paid).
2. Task runner: Option A—Celery + Redis (scalable). Option B—Django Q (simpler). Option C—Cron-only for MVP.
3. Charts: Option A—Server-side summaries + light JS. Option B—Client chart libs later.
4. Permissions: Start single-tenant; add roles/teams in Phase 4.
5. Testing: Unit for utilities; integration for views; gate heavy external tests via dedicated CI workflow.