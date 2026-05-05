# Issues Index — prei Revised Roadmap

> **Aligned with:** [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md)
> **Tracking issue:** open `tracking-product-strategy-pivot.md` as a GitHub issue and pin it.
>
> This README replaces the original phase numbering. All existing GitHub issues have been
> re-sequenced below according to the PM strategy critique. Issues that changed phase have
> a `⚠️ Strategy Note` indicating the required update to add to the GitHub issue body.

---

## How to Update Existing GitHub Issues

For each issue listed below with a `⚠️ Strategy Note`, add the following block at the **top**
of the GitHub issue body (before `## Phase X`):

```
> ⚠️ **Strategy Update (May 2026):** This issue has been re-prioritised per the
> [Product Strategy Pivot](#TRACKING_ISSUE_NUMBER) tracking issue.
> See `docs/PRODUCT_STRATEGY.md` for the full revised roadmap.
> **New phase:** [PHASE]. **Previous phase:** [ORIGINAL PHASE].
```

---

## New Issues to Create (Phase 1 — Critical Gaps)

| File | Title | Priority |
|---|---|---|
| `phase1-depreciation-tax-modeling.md` | Phase 1 — Depreciation & Tax Modeling | 🔴 Phase 1 |
| `phase1-hold-period-exit-analysis.md` | Phase 1 — Hold Period & Exit Analysis | 🔴 Phase 1 |
| `phase1-underwriting-score-v2.md` | Phase 1 — Underwriting Score v2 (replace `score_listing_v1`) | 🔴 Phase 1 |

---

## New Issues to Create (Phase 2 — Market Intelligence Gaps)

| File | Title | Priority |
|---|---|---|
| `phase2-market-selection-scoring.md` | Phase 2 — Market Selection Scoring | 🟠 Phase 2 |
| `phase2-brrrr-strategy-support.md` | Phase 2 — BRRRR Strategy Support | 🟠 Phase 2 |

---

## Existing Issues — Revised Priority & Required Updates

### ✅ Phase 1 — Underwriting Engine (Current Focus)

| Issue | Title | Status | Notes |
|---|---|---|---|
| #28 | Phase 2.4 — Property Report Detail View | ⚠️ Promoted to Phase 1 | Core underwriting display; do first |
| #27 | Phase 2.3 — CMA Engine Tests | ⚠️ Moved to Phase 2 | Supports market intelligence; correct priority |

**Update for #28:** Add strategy note — `New phase: Phase 1. Previous phase: Phase 2.4.`

**Update for #27:** Add strategy note — `New phase: Phase 2. Previous phase: Phase 2.3.`

---

### 🟠 Phase 2 — Market Intelligence

| Issue | Title | Status | Notes |
|---|---|---|---|
| #27 | CMA Engine Tests | ✅ Confirmed Phase 2 | Undervalued property detection is core |
| #29 | Phase 2.5 — Monthly Trend Time-Series | ⚠️ Moved to Phase 3 | Portfolio tracking, not market intelligence |

**Update for #29:** Add strategy note — `New phase: Phase 3 (Portfolio Tracking). Previous phase: Phase 2.5.`

---

### 🟡 Phase 3 — Portfolio Tracking

| Issue | Title | Status | Notes |
|---|---|---|---|
| #35 | Phase 4.1 — Portfolio What-If Scenario Modeling | ⚠️ Promoted to Phase 3 | High value; move up from Phase 4 |
| #29 | Phase 2.5 — Monthly Trend Time-Series | ⚠️ Moved here from Phase 2 | Time-series is portfolio, not market intelligence |

**Update for #35:** Add strategy note — `New phase: Phase 3. Previous phase: Phase 4.1. Rationale: portfolio what-if is a core portfolio tracking feature, not Phase 4 automation.`

---

### 🔵 Phase 4 — Automation & Scale (After Engine Is Proven)

| Issue | Title | Status | Notes |
|---|---|---|---|
| #31 | Phase 3.2 — Lead Ranking Service | ⚠️ Moved to Phase 4 | Ranking only makes sense after underwriting score v2 exists |
| #32 | Phase 3.3 — Recommendations Service | ⚠️ Moved to Phase 4 | Needs engine + market data foundation first |
| #34 | Phase 3.5 — Saved Search Nightly Tuning | ⚠️ Moved to Phase 4 | Automation; correct phase after engine |
| #38 | Phase 5.1 — Premium Data Adapters | ⚠️ Moved to Phase 4 | Data sourcing comes after engine; before Phase 5 collab |
| #19 | Government Property Lists | ⚠️ Moved to Phase 4 | Data sourcing; correct phase after engine |
| #13 | More Foreclosure Data | ⚠️ De-prioritized | Foreclosure monitoring is active investing; revisit only after passive use case is proven |

**Update for #31:** Add strategy note — `New phase: Phase 4. Previous phase: Phase 3.2. Also update acceptance criteria: scoring criteria must use score_listing_v2 (not score_listing_v1) once the underwriting score v2 issue is complete.`

**Update for #32:** Add strategy note — `New phase: Phase 4. Previous phase: Phase 3.3. Rationale: personalised recommendations require a proven underwriting engine and market data first.`

**Update for #34:** Add strategy note — `New phase: Phase 4. Previous phase: Phase 3.5.`

**Update for #38:** Add strategy note — `New phase: Phase 4. Previous phase: Phase 5.1. Premium data is a data-sourcing concern for the automation phase, not a Phase 5 collaboration feature.`

**Update for #19:** Add strategy note — `New phase: Phase 4. Previous phase: standalone. Government property lists feed the automation/scanning phase.`

**Update for #13:** Add strategy note — `De-prioritized: foreclosure/auction monitoring is an active investing strategy, which is out of scope for prei's passive investing focus. Revisit in Phase 4 only after the passive underwriting engine is proven and user-validated.`

---

### 🟣 Phase 5 — Collaboration & Integration

| Issue | Title | Status | Notes |
|---|---|---|---|
| #30 | Phase 2.6 — Structured Logging | ✅ Confirmed | Cross-cutting ops prerequisite; implement any time |
| #33 | Phase 3.4 — CRM Workflow Adapters | ⚠️ Moved to Phase 5 | Integration concern; correct in Phase 5 |
| #36 | Phase 4.3 — Team Collaboration | ✅ Confirmed Phase 5 | Real workflow; correctly placed |
| #37 | Phase 4.5 — Production Security Hardening | ✅ Confirmed | Cross-cutting; implement before first real users |
| #40 | Phase 5.3 — DRF REST API | ✅ Confirmed Phase 5 | Collaboration & integration |

**Update for #30:** No phase change. Add strategy note confirming it's on-track: `Confirmed: structured logging is a cross-cutting operational requirement. Can be implemented at any time without blocking the underwriting engine.`

**Update for #33:** Add strategy note — `New phase: Phase 5. Previous phase: Phase 3.4. CRM is an integration concern; defer until the core engine and automation phases are complete.`

---

### ❌ Reconsidered / Cut from Core Scope

| Issue | Title | Recommendation | Reason |
|---|---|---|---|
| #39 | Phase 5.2 — Marketplace Models & Views | **Close or label `wont-implement`** | Feature creep; a marketplace is a separate product |
| #41 | Phase 5.4 — Mobile Push Notifications | **Close or label `wont-implement`** | Auction-focused push notifications are the wrong use case; mobile access (general) is Phase 5 |

**Update for #39:** Add strategy note then close or label `wont-implement` — `This issue is out of scope for prei's core passive investing product. A marketplace connecting investors to agents/lenders/contractors is a separate product with its own user acquisition, trust & safety, and legal requirements. Close until prei reaches product-market fit with the core underwriting engine.`

**Update for #41:** Add strategy note then close or label `wont-implement` — `This issue was scoped around push notifications for auction/foreclosure alerts, which is an active investing use case. prei's target use case is passive residential investing. General mobile access (REST API mobile clients) is in scope via #40 (DRF REST API), but auction-specific push notifications are not.`

---

## Full Revised Roadmap Summary

```
Phase 1 — Underwriting Engine (NEW issues + #28 promoted)
  ├── #28  Property Report Detail View          [promoted from P2]
  ├── NEW  Depreciation & Tax Modeling
  ├── NEW  Hold Period & Exit Analysis
  └── NEW  Underwriting Score v2

Phase 2 — Market Intelligence
  ├── #27  CMA Engine Tests                     [confirmed]
  ├── NEW  Market Selection Scoring
  └── NEW  BRRRR Strategy Support

Phase 3 — Portfolio Tracking
  ├── #35  Portfolio What-If Scenario Modeling  [promoted from P4]
  └── #29  Monthly Trend Time-Series            [moved from P2]

Phase 4 — Automation & Scale
  ├── #31  Lead Ranking Service                 [moved from P3]
  ├── #32  Recommendations Service              [moved from P3]
  ├── #34  Saved Search Nightly Tuning          [moved from P3]
  ├── #38  Premium Data Adapters                [moved from P5]
  ├── #19  Government Property Lists            [moved from standalone]
  └── #13  More Foreclosure Data                [de-prioritized]

Phase 5 — Collaboration & Integration
  ├── #30  Structured Logging                   [confirmed; any time]
  ├── #33  CRM Workflow Adapters                [moved from P3]
  ├── #36  Team Collaboration                   [confirmed]
  ├── #37  Production Security Hardening        [confirmed]
  └── #40  DRF REST API                         [confirmed]

Cut / Reconsidered
  ├── #39  Marketplace Models                   [close — feature creep]
  └── #41  Mobile Push Notifications (auction)  [close — wrong use case]
```
