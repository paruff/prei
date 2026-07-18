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

## Implemented Features

### ✅ Phase 1 — The Underwriting Engine

Property input → full financial model → buy/no-buy recommendation.
One property, one user, no external integrations required.

**Implemented:**
- ✅ Property entry form with styled widgets (no Bootstrap)
- ✅ NOI, Cap Rate, CoC, DSCR, GRM calculations via `investor_app/finance/utils.py`
- ✅ **Underwriting Score v2** — Multi-signal scoring (1% Rule, CoC, DSCR, Cap Rate, GRM,
  After-Tax CoC) with "Strong Buy" / "Conditional" / "Pass" verdict
- ✅ **Depreciation schedule** — 27.5-year straight-line on residential improvements
- ✅ **After-tax cash flow** — applying depreciation paper loss to income
- ✅ **After-tax IRR** — annualized IRR over target hold period with exit cap scenario
- ✅ **Hold-period projection** — 5/7/10-year windows with rent growth, appreciation, sale proceeds
- ✅ **Deal Screener Dashboard** — KPI grid with color-coded verdicts for all properties
- ✅ **Property Detail Scorecard** — Full score breakdown with pass/fail flags
- ✅ **Verdict badges** — Reusable component (`{% include "components/verdict_badge.html" %}`)
- ✅ **Custom design system** — Token-driven CSS, no Bootstrap, fully responsive

### ✅ Phase 2 — Market Intelligence & BRRRR

**Implemented:**
- ✅ **Markets page** — Price-to-rent ratio, population growth, unemployment, employment diversity
  scores per ZIP code
- ✅ **Market refresh** — Scoped to user's properties only
- ✅ **BRRRR Strategy Support** — Full client-side calculator with:
  - ARV-based refinance analysis
  - Cash-out calculation and infinite CoC detection
  - Verdict banner (Full Cycle / Partial Recycle / Capital Trap)
  - DSCR warning when < 1.25
  - Server-side engine in `core/services/brrrr.py` with 25+ tests
- ✅ **Investment Targets** — Personalised thresholds (min CoC, min DSCR, max GRM, hold years)

### 🔄 Phase 3 — Portfolio Tracking (Planned)

Multi-property performance, time-series, equity dashboard.

- Multi-property tracking across entities/LLCs
- Time-series performance (monthly trend)
- BRRRR tracking (refinance events, equity recycling log)
- Portfolio what-if scenario modeling

### 🔄 Phase 4 — Automation & Scale (Planned)

Listing scanning and deal scoring — *after* the analysis engine is proven.

- Listing scanning and saved searches
- Lead ranking with new underwriting score
- Personalised recommendations
- Premium data adapters
- Government property lists

### 🔄 Phase 5 — Collaboration & Integration (Planned)

- Team collaboration / shared properties
- CRM workflow adapters
- DRF REST API
- Mobile access

---

## Architecture Highlights

| Component | Technology |
|---|---|
| Web Framework | Django 4.2 LTS |
| API Layer | Django REST Framework |
| Database | PostgreSQL (SQLite for local dev) |
| Frontend | Custom token-based design system (no Bootstrap) |
| Financial Math | Pure Python Decimal functions in `investor_app/finance/utils.py` |
| BRRRR Logic | Client-side JS + server-side engine in `core/services/brrrr.py` |
| CI | GitHub Actions (ruff, black, pytest — 897 tests passing) |
| Documentation | MkDocs with Material theme (Diátaxis framework) |

---

## What the Roadmap Gets Right (Keep These)

| Item | Notes |
|---|---|
| CMA engine | Correct and important — undervalued property detection is core to passive buying |
| `portfolio.py` aggregation | Essential for investors with 3+ properties |
| `Decimal` for all currency | Rare and commendable. Most hobby projects use float and get burned. |
| `finance/utils.py` architecture | Pure functions — no Django imports, testable in isolation |
| Portfolio what-if modeling | High value |
| Structured logging | Right instinct; keep |
| Team collaboration | Real workflow — spouses, partners, deal partners; keep in Phase 5 |
