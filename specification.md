# Specification: Alpha → MVP Roadmap (Purchase → Maintain → Sell)

> Supersedes the phase framing in `docs/PRODUCT_STRATEGY.md` where it conflicts with
> verified current code state (see "Corrections" below). Does not replace that
> document — extends it with maintain/sell phases it doesn't cover.

## 0. Corrections to existing docs (verified by reading the code, not assumed)

| Doc says | Code actually shows | Confidence |
|---|---|---|
| `PRODUCT_STRATEGY.md`: Phase 3 "Portfolio Tracking" = 🔄 Planned | `core/services/portfolio.py` (539 lines) already implements CoC/vacancy/expense variance, YTD cashflow, and a "flag for attention" function, backed by `MonthlyActuals` model + 3 test files (`test_portfolio.py`, `test_portfolio_variance.py`, `test_portfolio_scenarios.py`) | High — read directly |
| N/A | `investor_app/` (a whole separate Django app with duplicate `Property`/`RentalIncome`/`OperatingExpense` models) is **not in `INSTALLED_APPS`** and nothing imports it | High — verified via settings.py + grep |
| N/A | `docs/KNOWN_LIMITATIONS.md` is still the unfilled placeholder template | High — read directly |

**Not yet verified (flagging, not assuming):** whether `templates/portfolio_dashboard.html` actually displays the variance/flag data `compute_portfolio_performance()` returns, or whether the service is ahead of the UI. This needs a manual check before Phase 2 is called "done."

---

## Phase 1 — Purchase (primary focus; mostly built, closing remaining gaps)

**Definition:** everything from "here's a property/market" to "should I buy it, at what price."

The end-to-end purchase pipeline has three stages that pass data forward:

```
Area Discovery ──→ Market Deep-Dive ──→ Property Underwriting
   (which city?)      (neighborhood/ZIP)    (is this deal good?)
```

### Already implemented (per `PRODUCT_STRATEGY.md`, cross-checked against models/services)
- Property entry, NOI/Cap Rate/CoC/DSCR/GRM, Underwriting Score v2, depreciation, after-tax IRR, hold-period projection, BRRRR calculator, market intelligence (Census/BLS), investment targets.

### 1.1 Area Discovery — Growth Area Explorer (this spec)

The **Growth Area Explorer** is Stage 1 of the purchase pipeline. Its job is to answer: *"In which metropolitan area or city should I look for investment properties?"*

#### Current implementation
| Component | Status | Notes |
|---|---|---|
| `GrowthArea` model | ✅ Exists (core/models.py:643) | City-level; composite_score @property |
| `growth_explorer` view (POST) | ✅ Exists (core/views.py:706) | Calls Census + BLS APIs for any state |
| `growth_explorer.html` template | ✅ Exists | Full UI with form, table, loading state |
| `growth_areas` view (GET, fallback) | ✅ Exists (core/views.py:679) | Reads GrowthArea, falls back to MarketSnapshot |
| `growth_areas.html` template | ✅ Exists | Simpler table; uses MarketSnapshot fields |
| `populate_growth_areas` mgmt command | ✅ Exists | Pre-seeds 73 major cities with place codes |
| Census integration | ✅ Exists | `core/integrations/market/census.py` |
| BLS integration | ✅ Exists | `core/integrations/market/bls.py` |
| API endpoint | ✅ Exists | `/api/v1/real-estate/growth-areas` |
| Tests | ✅ Exists | 3 test files covering view, model, API |
| **Data in DB** | ❌ **EMPTY** | GrowthArea count = 0, MarketSnapshot count = 0 |
| **Scoring methodology validation** | ❌ **UNVALIDATED** | Weights are arbitrary, no empirical basis |
| **Pipeline integration** | ❌ **PARTIAL** | Links to VRM browse; no watchlist or compare |

#### Methodology decisions

The current composite score uses four factors with fixed weights:

| Factor | Weight | Source | Granularity |
|---|---|---|---|
| Population growth rate | 0.25 | Census ACS (5yr vintage compare) | Place (city) |
| Employment growth rate | 0.35 | BLS LAUS | State-level only |
| Median income growth | 0.25 | Census ACS (5yr vintage compare) | Place (city) |
| Housing demand index | 0.15 | Census ACS occupancy data | Place (city) |

**Known problems with this methodology:**
1. **Arbitrary weights** — no empirical or theoretical basis for the factor weights.
2. **Missing leading indicators** — no school quality, crime, climate risk, construction pipeline, rent-to-price ratio, zoning regulation, or supply constraint data.
3. **Geographic granularity gap** — city-level data masks neighborhood-level variation. Stage 2 (Market Deep-Dive) should handle ZIP/neighborhood granularity.
4. **State-level employment** — all cities in one state share the same employment growth figure, making it useless for intra-state comparison.
5. **Data age** — ACS_VINTAGE = "2022" is hardcoded; growth trends may have shifted.
6. **Scoring may crash** — composite_score property does not guard against None values in its factors.

**Recommended direction (from discovery):**
- Keep the current four-factor approach as a default but **add user-adjustable weight sliders** so investors can weight factors according to their strategy.
- **Add supply-constraint proxy** (building permit data from Census or local sources) — a market with high demand AND low supply is the sweet spot.
- **Add rent-to-price ratio** as a cash-flow viability filter (from MarketSnapshot or ATTOM).
- **Link to Stage 2** — clicking a city should show ZIP-level rent/price/demand detail before jumping to property search.
- **Pre-populate** via the management command OR fix the POST flow so it reliably writes data.

### Remaining gaps (this phase, in priority order)
1. **Growth Area Explorer data pipeline** — DB is empty (0 rows in GrowthArea and MarketSnapshot). The POST flow at `/growth-explorer/` should work, but either API calls are failing or the user hasn't submitted the form. Fix the root cause so data flows reliably.
2. **Login works reliably in local/dev.** Root cause identified: `DJANGO_ENV=production` + `DEBUG=False` forces `SESSION_COOKIE_SECURE=True`, breaking cookies over plain HTTP. Fix: ensure `.env` has `DJANGO_ENV=development`/`DEBUG=True` for local use; document this prominently (README already mentions it but a first-run script would prevent the mistake).
3. **Remove `investor_app`** (confirmed dead/unregistered) or explicitly document why it's kept, to stop it confusing future contributors or agents about which `Property` model is real.
4. **Resolve the two pending decisions from the prior market-data plan** (crime data source choice; GrowthArea vs MarketSnapshot split) — these were left open on purpose and should be closed before Phase 1 is called "done," since growth-area screening is part of the purchase workflow.
5. **Populate `docs/KNOWN_LIMITATIONS.md`** with real entries (starting with the two above) instead of the placeholder.

### Acceptance criteria — Phase 1 close-out
- AC1: Fresh clone + `.env.example` copy + documented steps → successful login without manual settings debugging.
- AC2: `investor_app` either deleted (with migration verified not to break `manage.py migrate` on a fresh DB) or has a one-line comment in `settings.py` explaining why it's intentionally unregistered.
- AC3: DECISION-1 and DECISION-2 from the prior market-data plan have a written answer (even if the answer is "defer," it must be written down, not silently unresolved).
- AC4: `KNOWN_LIMITATIONS.md` has at least the two items above filled in, template markers removed.

---

## Phase 2 — Maintain: Financial tracking (your stated first priority)

**Definition:** ongoing per-property financial performance vs. underwritten projections, across a portfolio.

### Verification tasks (do these before building anything new — the backend may already satisfy this phase)
1. Confirm `portfolio_dashboard.html` surfaces: `calculate_coc_variance`, `calculate_vacancy_variance`, `calculate_expense_variance`, `calculate_ytd_cashflow`, `check_flag_for_attention` — I have not checked the template itself, only the service functions that exist.
2. Confirm `portfolio_actuals_add` (the monthly-actuals entry form) is reachable from the dashboard UI and works end-to-end for a logged-in user with ≥1 property.
3. Confirm test coverage in the 3 existing portfolio test files actually exercises the variance/flag functions (not just aggregation) — I read the function list, not the test bodies.

### Only if verification finds real gaps — candidate new work
- A recurring reminder/nudge (email or in-app) to log monthly actuals — **not currently implemented anywhere I found** (no scheduled task infra beyond the management commands you invoke manually).
- Exposing `flag_for_attention` results as a visible dashboard alert, if not already surfaced.

### Explicitly NOT in this sub-phase (per your answer: financial first)
- Maintenance requests, vendor tracking, tenant/lease management — see Phase 3.

### Acceptance criteria — Phase 2 (financial) close-out
- AC1: A logged-in user with 2+ properties can enter a month of actuals and see variance vs. underwriting on the dashboard, without any new backend code (verification only) OR with the specific gap closed if verification finds one.
- AC2: Written confirmation (in `KNOWN_LIMITATIONS.md` or a short note) of what "flag for attention" currently does and whether it's visible in the UI.

---

## Phase 3 — Maintain: Operational (deferred — outline only, not designed in detail)

You said financial tracking first; I'm intentionally **not** designing data models for this yet, since doing so now would mean guessing at scope you haven't confirmed (tenant management? vendor invoicing? work-order status tracking? all three?). Placeholder scope for future specification:
- Maintenance/repair request tracking (status, cost, vendor)
- Vendor/contractor directory
- Tenant and lease record-keeping (lease dates, rent amount, renewal alerts)

**When you're ready to scope this, that's a new clarifying-question round, not something I'll assume here.**

---

## Phase 4 — Sell (deferred — outline only)

No model currently exists for a sale/disposition event (I checked `core/models.py` — there is hold-period *projection* logic for exit scenarios, but nothing that records an actual sale). Placeholder scope for future specification:
- Disposition/Sale event model (sale price, closing costs, date)
- Realized vs. projected return reconciliation (compare actual sale to the original underwriting)
- Capital gains / depreciation recapture estimate — **this touches tax calculations; if built, needs the same "flag uncertainty, don't invent tax rules" rigor as the rest of this spec, and likely a disclaimer that it's not tax advice.**

Not scheduled yet — flagged here only so it's visible in the roadmap, per your "eventually" framing.
