## Product Strategy Pivot: Passive Investing Core

> **Labels:** `strategy`, `roadmap` · **Pin this issue.**
>
> Full context: [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md)

### Summary

A senior PM review identified a fundamental mismatch between prei's stated purpose (passive
residential real estate investing) and its actual roadmap (auction/foreclosure monitoring, which
is an *active* strategy). This issue tracks the pivot back to the correct target user and
re-sequences all open issues accordingly.

### Top 5 Gaps (Must Fix Before Phase 3+)

1. **No depreciation or tax modeling** — The single biggest gap for sophisticated passive
   investors. 27.5-year straight-line depreciation and after-tax cash flow are missing.
   (PAL rules and cost segregation are follow-on issues after the base depreciation schedule
   is implemented.) A passive investor's after-tax return is often 30–50% better than the
   pre-tax number; not modeling it undersells every deal.
   Create issue from: `docs/issues/phase1-depreciation-tax-modeling.md`

2. **No hold-period or exit analysis** — Every passive investor thinks in 5/7/10-year windows.
   The current model is static (today's metrics only). Year-by-year rent growth, equity build-up,
   appreciation scenarios, and net sale proceeds are all missing.
   Create issue from: `docs/issues/phase1-hold-period-exit-analysis.md`

3. **`score_listing_v1` is not an underwriting score** — It uses PPSF + freshness. The 1% Rule,
   GRM, cap rate vs. local market, and projected CoC are the actual buy/no-buy signals passive
   investors use.
   Create issue from: `docs/issues/phase1-underwriting-score-v2.md`

4. **No market selection intelligence** — Top .01% investors select markets *before* properties.
   Price-to-rent ratio, population growth, employment diversity, and landlord-friendliness are all
   absent.
   Create issue from: `docs/issues/phase2-market-selection-scoring.md`

5. **No BRRRR strategy support** — BRRRR (Buy, Rehab, Rent, Refinance, Repeat) is the dominant
   wealth-building strategy for passive investors going from 1 to 10+ properties. ARV estimation,
   rehab cost, post-rehab DSCR refinance, and cash-out calculation are missing.
   Create issue from: `docs/issues/phase2-brrrr-strategy-support.md`

### Revised Phase Order

| Phase | Focus | Key Issues |
|---|---|---|
| **Phase 1** | Underwriting Engine | #28 (property report, promoted) + new depreciation, hold-period, score-v2 |
| **Phase 2** | Market Intelligence | #27 (CMA, confirmed) + new market selection, new BRRRR |
| **Phase 3** | Portfolio Tracking | #35 (what-if, promoted from P4), #29 (time-series, moved from P2) |
| **Phase 4** | Automation & Scale | #31 (ranking), #32 (recommendations), #34 (saved search), #38 (premium data), #19 (gov lists), #30 (logging — cross-cutting, any time) |
| **Phase 5** | Collaboration & Integration | #36 (team collab), #33 (CRM), #37 (security), #40 (DRF API) |
| **Cut/Deferred** | Reconsidered | #39 (marketplace — feature creep), #41 (mobile push auctions — wrong use case) |

### Existing Issues to Update

The following open issues should have a `> ⚠️ Strategy Note` comment added (see each issue
section in `docs/issues/README.md` for the exact text):

- #13 More foreclosure data → De-prioritize; add note: "foreclosure monitoring is active investing; revisit in Phase 4 if passive use case is proven first"
- #19 Government property lists → Move to Phase 4
- #27 CMA Engine Tests → Confirmed Phase 2 (market intelligence)
- #28 Property Report Detail View → Promote to Phase 1 (core underwriting)
- #29 Monthly Trend Time-Series → Move to Phase 3 (portfolio tracking)
- #30 Structured Logging → Cross-cutting; can be implemented any time (Phase 4 ops prerequisite)
- #31 Lead Ranking → Move to Phase 4; update scoring criteria to use new underwriting score v2
- #32 Recommendations → Move to Phase 4 (needs engine + market data first)
- #33 CRM Workflow → Move to Phase 5 (integration concern)
- #34 Saved Search Nightly Tuning → Move to Phase 4
- #35 Portfolio What-If → Promote to Phase 3
- #36 Team Collaboration → Confirmed Phase 5
- #37 Production Security Hardening → Confirmed Phase 5 prerequisite
- #38 Premium Data Adapters → Move to Phase 4 (after engine proven)
- #39 Marketplace Models → **Close or label `wont-implement`** — feature creep; separate product
- #40 DRF REST API → Confirmed Phase 5
- #41 Mobile Push Notifications → **Close or label `wont-implement`** — wrong use case; auction-focused push notifications are not passive investing

### New Issues to Create

> ⚠️ **Before opening this tracking issue**, create the five new issues first using the
> `docs/issues/phase1-*` and `phase2-*` files as copy-paste bodies. Then replace the
> `docs/issues/` references above with the actual GitHub issue numbers before opening this issue.

Use the files in `docs/issues/` as copy-paste-ready bodies:

- [ ] `docs/issues/phase1-depreciation-tax-modeling.md` → create GitHub issue
- [ ] `docs/issues/phase1-hold-period-exit-analysis.md` → create GitHub issue
- [ ] `docs/issues/phase1-underwriting-score-v2.md` → create GitHub issue
- [ ] `docs/issues/phase2-market-selection-scoring.md` → create GitHub issue
- [ ] `docs/issues/phase2-brrrr-strategy-support.md` → create GitHub issue

### Definition of Done

- [ ] All existing phase issues updated with strategy-pivot reference note
- [ ] 5 new issues created from `docs/issues/` files
- [ ] #39 and #41 closed or labeled `wont-implement` with explanatory comment
- [ ] This tracking issue pinned to the repository
- [ ] `docs/PRODUCT_STRATEGY.md` merged to `main`

