# Product Strategy: prei — Passive Residential Real Estate Investing

> **Source:** Senior PM critique of the original roadmap, May 2026.
> **Status:** Adopted. All new issues and roadmap decisions should align with this document.
> This file is listed in `.github/copilot-instructions.md` as a required context file.
> Read it before generating any feature work.

---

## TL;DR

The engineering foundation is solid — clean architecture, proper Decimal math, well-structured CI.
But the original roadmap is **engineering-led, not investor-outcome-led**. The product was
oriented around foreclosures and auction monitoring, which is an *active* investing strategy.
**prei's stated purpose is passive residential real estate investing.** That mismatch must be
corrected at the roadmap level before any further Phase 3–5 work proceeds.

---

## The Correct Mental Model for prei's Target User

**Passive residential RE investing means:**

- Buy-and-hold SFR (single-family rental) or small multifamily (2–4 units)
- Turnkey properties from providers in landlord-friendly markets
- Build-to-rent
- DST (Delaware Statutory Trust) or syndications as a limited partner

The primary workflow for this user is: **"I found a rental property. Help me decide if I should
buy it and at what price."** That workflow is almost entirely absent from the original roadmap.

---

## Revised Roadmap (Adopted)

### Phase 1 — The Underwriting Engine ✅ *Current focus*

Property input → full financial model → buy/no-buy recommendation.
One property, one user, no external integrations required.

**Must include:**
- NOI, Cap Rate, CoC, DSCR (already partially implemented)
- **Depreciation schedule** — 27.5-year straight-line on residential (currently missing)
- **After-tax cash flow** — applying depreciation paper loss to income (currently missing)
- **After-tax IRR** — the current `irr()` is pre-tax, which is nearly useless for RE vs. stock
  comparisons
- **Hold-period projection** — 5/7/10-year windows with rent growth, appreciation, sale proceeds
- **Underwriting score v2** — replace `score_listing_v1` (PPSF + freshness) with investor signals:
  1% Rule, GRM, cap rate vs. local market, projected CoC at years 1/3/5

### Phase 2 — Market Intelligence

Make the engine work with real data; add market selection tools.

**Must include:**
- Price-to-rent ratio by metro (Census/Zillow — public data)
- Population growth / net migration (Census Bureau — free)
- Employment diversity score (BLS — free)
- Landlord-friendliness index (eviction timeline, rent control laws by state)
- Rent growth rate by ZIP/metro
- **BRRRR strategy support** — ARV estimation from comps, rehab cost estimator, post-rehab
  DSCR refinance analysis, cash-out calculation, infinite CoC detection
- CMA engine (already planned in #27 — correctly prioritized)

### Phase 3 — Portfolio Tracking

Multi-property performance, time-series, equity dashboard.

**Includes:**
- Multi-property tracking across entities/LLCs
- Time-series performance (monthly trend — already in #29, correctly prioritized)
- BRRRR tracking (refinance events, equity recycling log)
- Portfolio what-if scenario modeling (already in #35 — move from Phase 4 to here)

### Phase 4 — Automation & Scale

Listing scanning and deal scoring — *after* the analysis engine is proven.

**Includes:**
- Listing scanning and saved searches (#34)
- Lead ranking with new underwriting score (#31)
- Personalised recommendations (#32)
- Premium data adapters (#38)
- Government property lists (#19)

### Phase 5 — Collaboration & Integration

**Includes:**
- Team collaboration / shared properties (#36)
- CRM workflow adapters (#33)
- DRF REST API (#40)
- Mobile access (general, not push notification-first)

**Reconsidered / Cut:**
- **#39 Marketplace Models & Views** — cut from core scope; feature creep and a separate product
- **#41 Mobile Push Notifications (auction-focused)** — cut or defer; wrong use case for passive
  investors

---

## Critical Issues With the Current Implementation

### 1. `finance/utils.py` Violates Its Own Architecture Rule
`investor_app/finance/utils.py` imports `from core.models import InvestmentAnalysis, Listing, Property`.
Pure financial functions must have **zero Django imports** — this makes the module untestable in
isolation and violates the architecture. Fix before adding any new financial functions.

### 2. `score_listing_v1` Is Not a Feature
It combines price-per-square-foot and freshness. Replace with a multi-signal underwriting score
(see Phase 1 scope above). Issue: see `docs/issues/phase1-underwriting-score-v2.md`.

### 3. `estimate_insurance()` Hardcodes $1,200 / year
Insurance is highly geographic — Florida vs. Ohio vs. California can be 3–10× different.
This produces dangerously wrong numbers for real decisions. Read rate from settings/env var.

### 4. `InvestmentAnalysis` Is a Snapshot, Not a History
The model stores one set of KPIs per property (`updated_at`). A time-series of analysis snapshots
is far more valuable. Address in Phase 3 portfolio tracking work.

### 5. No `Loan` Model in `core/models.py`
Mortgages aren't tracked. This means refinancing scenarios, amortization schedules, and equity
calculations must be passed in manually every time. Fundamental data model gap — required before
Phase 3 BRRRR work.

### 6. `Listing.SOURCE_CHOICES` Is Scaffold
Only `("dummy", "Dummy")` and `("external", "External")`. Needs real taxonomy: `mls`, `zillow`,
`redfin`, `attom`, `hud`, `turnkey_provider`, `off_market`, etc.

### 7. `KNOWN_LIMITATIONS.md` Is a Placeholder
It lists `[LIMIT-01] [PLACEHOLDER]`. Every AI agent session is supposed to read this before
acting. As-is, it is noise. Populate it with the real limitations above.

### 8. `API_SURFACE.md` Services Section Is a Placeholder
`[service_module].[function_name](params)` — the most important part of the context file for
AI agents is empty. Populate before any service-layer work.

---

## What the Roadmap Gets Right (Keep These)

| Item | Notes |
|---|---|
| CMA engine | Correct and important — undervalued property detection is core to passive buying |
| `portfolio.py` aggregation | Essential for investors with 3+ properties |
| `Decimal` for all currency | Rare and commendable. Most hobby projects use float and get burned. |
| `finance/utils.py` architecture | Pure functions is the right call (fix the Django import violation) |
| Phase 4.1 Scenario Modeling (#35) | High value — move to Phase 3 |
| Structured logging (#30) | Right instinct; keep |
| Team collaboration (#36) | Real workflow — spouses, partners, deal partners; keep in Phase 5 |

---

## Roadmap Realignment Summary Table

| Original Phase | Issue | Revised Phase | Reason |
|---|---|---|---|
| Phase 1 | Auction/foreclosure scanning | Phase 4 | Not passive; narrow market |
| Phase 2 | Market snapshots | Phase 1–2 | Critical for buy decision |
| Phase 3 | Recommendations engine (#32) | Phase 4 | Needs engine + market data first |
| Phase 4.1 | Portfolio what-if (#35) | Phase 3 | Core portfolio feature |
| Phase 5 | Mobile push for auctions (#41) | Cut/last | Wrong use case for passive investors |
| Phase 5.2 | Marketplace (#39) | Cut from core | Feature creep; separate product |
| *Not in plan* | Depreciation/tax modeling | **Phase 1** | #1 reason people invest in RE |
| *Not in plan* | Hold period projections | **Phase 1** | Every investor models this |
| *Not in plan* | After-tax IRR | **Phase 1** | Pre-tax IRR is incomplete |
| *Not in plan* | BRRRR analysis | **Phase 2** | Most popular wealth-building strategy |
| *Not in plan* | Market selection scoring | **Phase 2** | Market first, deal second |

---

## Tracking Issue

Open GitHub issue: **"Product Strategy Pivot: Passive Investing Core"**
See `docs/issues/tracking-product-strategy-pivot.md` for the body.
Label it `strategy` and `roadmap`. Pin it to the repository.
