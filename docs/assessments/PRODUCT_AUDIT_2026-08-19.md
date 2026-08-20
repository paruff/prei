# Product Audit — prei Residential RE Investing Workflows

**Date**: 2026-08-19
**Auditor**: AI-assisted review against PRODUCT_STRATEGY.md maturity matrix

---

## Executive Summary

prei is a **passive residential real estate investment analytics** platform for buy-and-hold investors. The core workflow spans Growth Areas → Discovery → Screening → Underwriting → Offer → Pipeline CRM → Portfolio → Leasing.

Current state: Most components are **ALPHA to BETA** with significant gaps in acceptance testing, UX polish, and end-to-end workflow verification.

---

## Maturity Assessment (vs. PRODUCT_STRATEGY.md July 2026)

| Component | Current | Target | Key Gaps |
|-----------|---------|--------|----------|
| **Growth Areas** | BETA | GA | Acceptance tests, seed data, data health dashboard |
| **Property Discovery** | ALPHA→BETA | BETA | Scraper reliability, saved searches, source health status |
| **Screening** | ALPHA (thin) | BETA | Batch filter/sort UX, criteria settings page, acceptance tests |
| **Underwriting** | BETA | GA | Side-by-side deal comparison, market cap rate in reports |
| **Offer Management** | ALPHA (thin) | BETA | MAO visualization, competition multiplier UX |
| **Pipeline CRM** | ALPHA (thin) | BETA | **Drag-and-drop kanban** (biggest UX gap) |
| **Portfolio Tracking** | BETA | GA | Time-series charts, equity dashboard |
| **BRRRR** | ALPHA (thin) | BETA | Visual projection timeline, equity recycle log |
| **Leasing Pipeline** | THIN SHELL | BETA | Backend wiring for kanban (drag-drop + API) |

---

## Top 7 Improvement Opportunities (Priority Order)

### **P0 — Pipeline CRM Kanban (Biggest UX Gap)**
- **Current**: List view only, no drag-and-drop, no stage transition API
- **Template exists**: `templates/pipeline/kanban.html` has full drag-drop markup + JS but **no backend endpoints**
- **Need**: `POST /pipeline/<pk>/advance/`, `POST /pipeline/<pk>/kill/`, `POST /pipeline/<pk>/hold/` endpoints + WebSocket/polling for real-time multi-user

### **P0 — Property Discovery Data Health**
- **Scrapers unreliable**: 11 TX counties, sheriff sales, ATTOM — no monitoring/alerting
- **No source health dashboard**: User can't see if HUD/USDA/VRM/County data is fresh
- **Need**: `DataSourceHealth` model + scheduled ingestion status + UI status page (partially in `system_status` view)

### **P1 — Screening Batch UX + Criteria Settings**
- **Screener page** (`/pipeline/screener/`) exists but **no filter/sort controls** on results table
- **Criteria page** (`/pipeline/screening-settings/`) — form exists but no live preview of kill impact
- **Need**: HTMX-powered filter bar, "simulate screening" button, save/version criteria

### **P1 — Leasing Pipeline Backend Wiring**
- **Kanban template** exists (`templates/leasing/kanban.html`) with columns: `LISTED → SCREENING → APPROVED → LEASED`
- **Zero backend**: No stage transition API, no tenant screening workflow, no lease document storage
- **Need**: Leasing stage model + API + tenant application form + e-sign integration

### **P2 — Deal Comparison UI (Underwriting)**
- **Math is solid** (58 parametrized tests verified), but **no side-by-side comparison**
- **Need**: Multi-property comparison view with aligned KPI columns, variance highlighting, export

### **P2 — Growth Areas Acceptance Tests + Seeded Data**
- **Works but empty on deploy**: Requires `populate_growth_areas` CLI command
- **No automated acceptance tests** against deployed artifact
- **Need**: Seed script for TX/FL/GA default markets, Playwright tests for Growth Explorer flow

### **P3 — BRRRR Visual Timeline + Equity Log**
- **Calculator works** (client + server), but **no visual projection**
- **Need**: Year-by-year equity recycle chart, cash-out refi waterfall, sensitivity sliders

---

## Code Quality Observations

| Area | Issue | Severity |
|------|-------|----------|
| **Duplication** | `create_from_vrm/foreclosure/hud/usda/county` in `pipeline.py` — 5 nearly identical functions | Medium |
| **Hardcoded thresholds** | Screening weights (20/15/10/5 pts) in `screening.py` — not user-configurable | Low |
| **Missing indexes** | `PipelineProperty` queries filter by `user+stage+status` — no composite index | Medium |
| **N+1 in portfolio** | `compute_portfolio_performance` loops properties → queries `MonthlyActuals` each | High |
| **Test gaps** | **No Playwright E2E tests for any full workflow (discovery→screen→underwrite→offer)** | **Critical** |

---

## Recommended Implementation Sequence

### Phase 1: TDD Foundation (Week 1)
1. **Playwright E2E test suite** for full workflow: Growth Explorer → Discovery → Screening → Underwriting → Offer → Pipeline
2. CI integration with headless browser

### Phase 2: Pipeline Kanban Backend (Week 2)
1. Stage transition API endpoints (`advance`, `kill`, `hold`, `reactivate`)
2. WebSocket/polling for real-time updates
3. Drag-drop frontend already exists — wire it up

### Phase 3: Data Health & Screening UX (Week 3)
1. DataSourceHealth model + scheduled ingestion monitoring
2. Screening filter/sort + criteria simulation

### Phase 4: Leasing & Comparison (Week 4+)
1. Leasing pipeline backend
2. Deal comparison UI

---

## Files Referenced in Audit

### Core Services
- `core/services/market_scoring.py` — GACS composite scoring
- `core/management/commands/populate_growth_areas.py` — Growth area population
- `core/models/growth.py` — GrowthArea, MarketSnapshot models
- `core/services/sources/registry.py` — Discovery source registry (6 sources)
- `core/services/screening.py` — 9-criteria screening (4 hard kill, 5 soft)
- `core/services/underwriting.py` — NOI, Cap Rate, CoC, MAO solver
- `core/services/scoring.py` — v2 investor-grade underwriting score (6 signals)
- `core/services/offer.py` — Offer price optimization (3 strategies)
- `core/services/pipeline.py` — Pipeline lifecycle (11 stages, 5 source creators)
- `core/services/brrrr.py` — BRRRR analysis (pure math + Django orchestrator)
- `core/services/portfolio.py` — Portfolio aggregates, variance analysis

### Finance Math (verified 58 parametrized tests)
- `investor_app/finance/utils.py` — Core KPIs (NOI, Cap Rate, CoC, DSCR, IRR)
- `investor_app/finance/mortgage.py` — Monthly mortgage, carrying costs
- `investor_app/finance/taxes.py` — Depreciation, after-tax cashflow
- `investor_app/finance/strategies.py` — BRRRR, flip, buy-and-hold math

### Templates (key workflow pages)
- `templates/growth_explorer.html` — State picker, results table
- `templates/property_discovery.html` — Source selection, discovery modal
- `templates/pipeline/screener.html` — Screening results table
- `templates/pipeline/kanban.html` — **Drag-drop kanban (frontend only)**
- `templates/brrrr_calculator.html` — Client-side BRRRR calculator
- `templates/leasing/kanban.html` — Leasing kanban (frontend only)

---

## Next Actions

1. **Save this audit** → `docs/assessments/PRODUCT_AUDIT_2026-08-19.md` ✅
2. **Create implementation plan** with `writing-plans` skill
3. **Start TDD**: Write Playwright E2E tests for discovery→screen→underwrite→offer
4. **Then**: Implement Pipeline Kanban drag-drop backend
