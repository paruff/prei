# Product Strategy: prei — Passive Residential Real Estate Investing

> **Source:** Senior PM critique of the original roadmap, May 2026.
> **Status:** Adopted. All features described below are implemented or in active development.
> This file is listed in `.github/copilot-instructions.md` as a required context file.
> Read it before generating any feature work.

---

## TL;DR

prei is a **passive residential real estate investment analytics** platform for buy-and-hold
investors. The core workflow: *"I found a rental property. Help me decide if I should buy it
and at what price."* The product is built around underwriting, market intelligence, BRRRR
analysis, and portfolio tracking — not auction monitoring or active trading.

---

## The Correct Mental Model for prei's Target User

**Passive residential RE investing means:**

- Buy-and-hold SFR (single-family rental) or small multifamily (2–4 units)
- Turnkey properties from providers in landlord-friendly markets
- Build-to-rent
- BRRRR (Buy, Rehab, Rent, Refinance, Repeat) — scaling from 1 to 10+ properties

---

## Maturity Definitions

| Level | Code | Tests | Acceptance Tests | UX/UI Review | Description |
|---|---|---|---|---|---|
| **GA** | ✅ | ✅ | ✅ | ✅ | Production-ready. Full lifecycle verified. |
| **BETA** | ✅ | ✅ | ⬜ | ⬜ | Functional, API works, math verified. Needs UX polish and acceptance tests. |
| **ALPHA** | ✅ | 🟡 | ⬜ | ⬜ | Works, but thin shell. Limited test coverage. |
| **THIN SHELL** | 🟡 | ⬜ | ⬜ | ⬜ | Placeholder UI or stub. Exists as proof of concept. |

---

## Product Component Maturity — July 2026

### 1. Growth Areas (Market Intelligence) — BETA

| Attribute | Status |
|---|---|
| Code | `core/services/market_scoring.py` + `core/management/commands/populate_growth_areas.py` |
| Model | `GrowthArea` with 8 migrations, composite score, FMR, employment, population |
| Tests | 8 test files covering views, API, integration, model |
| Acceptance tests | ⬜ None automated against the deployed artifact |
| UX | System page has "Analyze Growth Areas" button. No data/status dashboard for growth area health. |
| Data | 0 growth areas in default deployment — requires CLI command to populate |

**To promote to GA:** Add acceptance tests, system page data dashboard, seed initial growth areas.

### 2. Property Discovery — ALPHA → BETA

| Attribute | Status |
|---|---|
| Code | VRM source, foreclosure scrapers (11 TX counties), HUD REO, USDA REO, sheriff sales |
| Tests | Pipeline tests (264), county source tests, sheriff tests |
| Acceptance tests | 🟡 2 tests (growth areas API, foreclosures API) but no full discovery workflow test |
| UX | Discovery page with state selector. In-page results. No saved searches or alerts. |
| Data | Requires API keys (ATTOM, HUD). Some scrapers have placeholder data (FBI crime). |

**To promote to BETA:** Fix data/UX issues with scraper reliability, add saved searches, add status page showing data source health.

### 3. Screening — ALPHA (thin shell)

| Attribute | Status |
|---|---|
| Code | `core/services/scoring.py` (score_listing), `prei/pipeline/handlers/screening.py` |
| Tests | 4 unit tests for scoring functions. No pipeline integration tests for screening. |
| Acceptance tests | ⬜ None |
| UX | Pipeline screener page exists. Results show scores but no filtering/sorting controls. |

**To promote to BETA:** Add batch screening UI with filter/sort controls, screening criteria settings page, acceptance tests.

### 4. Underwriting — BETA

| Attribute | Status |
|---|---|
| Code | `investor_app/finance/utils.py` (40+ KPI functions), `core/services/scoring.py` (v2) |
| Tests | 58 parametrized edge cases verified against reference implementation (Phase B) |
| Acceptance tests | ⬜ None |
| UX | Property report page shows KPIs. No side-by-side deal comparison. |

**To promote to GA:** Side-by-side deal comparison UI, acceptance tests, market cap rate comparison in reports.

### 5. Offer Management — ALPHA (thin shell)

| Attribute | Status |
|---|---|
| Code | `prei/pipeline/handlers/offer.py` (124 lines, Pydantic models, 3 strategies) |
| Tests | 264 pipeline tests include offer handler tests |
| Acceptance tests | ⬜ None |
| UX | Offer form exists in pipeline. No MAO visualisation or competition analysis display. |

**To promote to BETA:** MAO visualization (price vs value graph), competition multiplier UX, acceptance tests.

### 6. Acquisition Pipeline (CRM) — ALPHA (thin shell)

| Attribute | Status |
|---|---|
| Code | `prei/pipeline/engine.py` + `orchestrator.py` + stage handlers |
| Tests | Pipeline engine tests (264). No stage-transition integration tests. |
| Acceptance tests | ⬜ None |
| UX | Pipeline list page with status filter. Not drag-and-drop. No kanban board. |

**Gap:** User expectation is a CRM-like kanban board with drag-and-drop stage transitions. Current implementation is a list with status filter. This is the biggest UX gap.

### 7. Portfolio Tracking — BETA

| Attribute | Status |
|---|---|
| Code | `Property` model, `RentalIncome`, `OperatingExpense`, `InvestmentAnalysis` |
| Tests | Property analysis tests, portfolio aggregation tests |
| Acceptance tests | ⬜ None |
| UX | Dashboard shows owned properties with KPIs. Portfolio summary computed server-side. |

**To promote to GA:** Time-series performance charts, equity dashboard, acceptance tests.

### 8. BRRRR Analysis — ALPHA (thin shell)

| Attribute | Status |
|---|---|
| Code | `core/services/brrrr.py` with server-side engine, client-side calculator |
| Tests | 25+ BRRRR-specific tests |
| Acceptance tests | ⬜ None |
| UX | Calculator page exists. No visual BRRRR projection timeline or equity recycling log. |

### 9. Leasing Pipeline — THIN SHELL

| Attribute | Status |
|---|---|
| Code | `core/services/leasing.py` (61 lines). Kanban template exists (drag-drop markup). |
| Tests | 1 test file (`test_leasing_views.py`) |
| Acceptance tests | ⬜ None |
| UX | Kanban board template with columns. No drag-and-drop functionality wired to backend. |

**Gap:** This is the thinnest component. The kanban board is HTML/CSS only — no JavaScript drag-and-drop, no backend stage transition API, no tenant screening workflow.

---

## Priority Matrix

| Priority | Component | Reason |
|---|---|---|
| **P0 — Next** | Acquisition Pipeline (CRM kanban) | Core workflow blocked without it. User cannot track deals. |
| **P0 — Next** | Property Discovery (data health) | Scrapers unreliable, no data source status dashboard. |
| **P1 — Soon** | Screening (UX + acceptance tests) | 90% of deals should die here. Needs batch filtering UX. |
| **P1 — Soon** | Leasing Pipeline (backend wiring) | Kanban template exists but isn't functional. |
| **P2 — Later** | Growth Areas (acceptance tests) | Works but needs UX polish and seeded data. |
| **P2 — Later** | Underwriting (deal comparison) | Math is solid. Needs better comparison UX. |
| **P2 — Later** | Offer Management (visualizations) | Thin shell. Needs MAO visualizations. |
| **P3 — Nice to have** | BRRRR (projection timeline) | Works for calculation, needs visual timeline. |
