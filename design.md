# Design & Plan: Alpha → MVP (Phase 1 close-out + Phase 2 verification)

Companion to `specification.md`. Covers only Phase 1 (close-out) and Phase 2
(verification) in implementation detail, per that spec's scoping — Phases 3/4 are
intentionally not designed yet.

## Appendix A: Growth Area Explorer Design

This appendix covers the Growth Area Explorer as Stage 1 of the purchase pipeline.
See `specification.md` §1.1 for the business context and methodology decisions.

### A.1 Purchase Pipeline Architecture

```
                    ┌──────────────────────┐
                    │  Growth Area Explorer │  ← Stage 1: WHICH CITY?
                    │  (/growth-explorer/)  │
                    └──────────┬───────────┘
                               │ user selects a city
                               ▼
                    ┌──────────────────────┐
                    │  Market Deep-Dive     │  ← Stage 2: WHICH NEIGHBORHOOD?
                    │  (ZIP-level data)     │     (not yet implemented)
                    └──────────┬───────────┘
                               │ user selects a ZIP/neighborhood
                               ▼
                    ┌──────────────────────┐
                    │  Property Search      │  ← Stage 3: WHICH PROPERTY?
                    │  (VRM / ATTOM)        │
                    └──────────┬───────────┘
                               │ user selects a property
                               ▼
                    ┌──────────────────────┐
                    │  Underwriting         │  ← Stage 4: GOOD DEAL?
                    │  (calc suite)         │
                    └──────────────────────┘
```

### A.2 Data Sources

| Source | Data | Granularity | Status |
|---|---|---|---|
| Census ACS | Population, income, housing occupancy | Place (city) | ✅ Integrated |
| Census ACS (query) | Building permits (BPS series) | Place (city) | ❌ Not yet used |
| BLS LAUS | Employment | State | ✅ Integrated |
| ATTOM | Property-level rent/sale comps | Property/ZIP | ✅ Integrated (elsewhere) |
| MarketSnapshot | ZIP-level rent index, price trend, population | ZIP | ✅ Model exists, 0 rows |
| GreatSchools/API | School ratings | ZIP/School district | ❌ Not integrated |
| FBI crime data | Crime stats | City/MSA | ❌ DECISION-2 pending |

### A.3 Scoring Methodology

**Current approach (may change):**

```
composite_score = pop_growth * 0.25 + emp_growth * 0.35
                + income_growth * 0.25 + housing_demand_index * 0.15
```

**Recommendation:** Keep current as default; add user-configurable weights in the UI.
The model stores raw factors; scoring is computed at display time.

**Critical bug to fix:** The `composite_score` property does not guard against `None`
values. If any factor is None, it crashes with TypeError. The view must validate all
factors before computing a score, or the property must handle None gracefully.

### A.4 Key Decisions (resolving the pending ones from the prior plan)

| Decision | Answer | Rationale |
|---|---|---|
| DECISION-1: GrowthArea vs MarketSnapshot split | **GrowthArea is primary; MarketSnapshot is secondary overlay.** GrowthArea (city-level) drives the top-of-funnel area discovery. MarketSnapshot (ZIP-level) provides granular rent/price data for Stage 2 deep-dive. Both remain; they serve different pipeline stages. | City-level screening first, ZIP-level drill-down second — they're sequential, not competing. |
| DECISION-2: Crime data source | **Deferred.** Adding crime data is valuable but requires evaluation of data quality, update frequency, and API cost. FBI UCR data is free but lags by 1-2 years. Revisit as a Phase 3 enhancement. | Not blocking the purchase pipeline. |

### A.5 Pre-population Strategy

Two complementary approaches:
1. **Management command** (`populate_growth_areas`) — batch-populates 73 major cities. Should be run once before first use (or as a CI/data-pipeline step).
2. **Live POST flow** (`growth_explorer` view) — discovers any U.S. city on demand via Census place wildcard query. Works for any state, not just the 73 pre-seeded cities.

**Trade-off:** The POST flow is slow (sequential API calls for ~20 places = 20 Census + 1 BLS). For a fast initial experience, pre-populate. For depth on any state, use the live explorer.

### A.6 Risk Items

1. **Census API rate limits/quota** — free Census key allows 500 calls/day. A single state analysis makes 21-41 calls. Scale: ~12-24 full state analyses per day.
2. **ACS vintage staleness** — ACS_VINTAGE = "2022" is hardcoded. Should auto-detect latest available vintage.
3. **Empty-state UX** — when GrowthArea and MarketSnapshot are both empty, the user sees "No market snapshots available" or a blank results table. Need helpful empty states (e.g., "Try Analyze State above to discover growth cities using Census/BLS data").
4. **JavaScript failure on POST** — the form's submit handler shows "Analyzing…" but if the POST request fails (network error, timeout), the button stays disabled with no recovery. Add error handling or timeout fallback.

## 1. Sequencing (do in this order)

```
1. Login fix (env config only — no code change, just docs/first-run script)
        │
2. investor_app decision (delete or document) ──┐
        │                                        │
3. DECISION-1 / DECISION-2 resolution ───────────┤── can run in parallel
        │                                        │
4. KNOWN_LIMITATIONS.md populated ◄──────────────┘
        │
        ▼
5. Phase 2 verification (template check, e2e manual test, test-body review)
        │
        ▼
6. Only if gaps found: close them (nudge/reminder, UI exposure fixes)
```

Rationale for this order: login blocks *any* manual verification of Phase 2, so it must
be first. The `investor_app` decision and the two pending market-data decisions are
independent of each other and of login, so they can run in parallel once login works.

## 2. Task breakdown

| ID | Task | Type | Depends on | Notes |
|---|---|---|---|---|
| P1-1 | Fix local `.env` (`DJANGO_ENV=development`, `DEBUG=True`) and confirm login works | Config | — | No code change |
| P1-2 | Add a first-run check (e.g. a `manage.py check --deploy`-style warning, or a comment at the top of `settings.py`) so this misconfiguration is caught earlier next time | Code, small | P1-1 | Prevents recurrence, not just a one-time fix |
| P1-3 | Decide: delete `investor_app` or document why kept | Decision + code | — | If deleting: run `manage.py migrate` on a fresh DB after removal to confirm nothing breaks; check `investor_app/tests` and `investor_app/finance` aren't imported elsewhere first (I have not re-verified `investor_app/finance` usage — check before deleting) |
| P1-4 | Resolve DECISION-1 (GrowthArea vs MarketSnapshot) | Decision | — | From prior plan — still open |
| P1-5 | Resolve DECISION-2 (crime data source) | Decision + code | — | From prior plan — still open |
| P1-6 | Populate `KNOWN_LIMITATIONS.md` | Docs | P1-3, P1-4, P1-5 | Replace placeholder, add real entries |
| P2-1 | Manually verify `portfolio_dashboard.html` against `compute_portfolio_performance()` output | Verification | P1-1 | Read the template, compare field-by-field to the service's return dict |
| P2-2 | Manually verify `portfolio_actuals_add` end-to-end (logged-in user, 2+ properties, submit form, see updated dashboard) | Verification | P1-1 | |
| P2-3 | Read test bodies of `test_portfolio.py`, `test_portfolio_variance.py`, `test_portfolio_scenarios.py` to confirm variance/flag functions are actually exercised (not just aggregation) | Verification | — | I only listed function signatures, not test assertions |
| P2-4 | (Conditional) Build monthly-actuals reminder mechanism, if P2-1/P2-2 show it's genuinely missing and wanted | Code | P2-1, P2-2 | Do not build speculatively — only if verification confirms the gap AND you confirm you want it |
| P2-5 | (Conditional) Expose `flag_for_attention` in the dashboard UI, if not already visible | Code, small | P2-1 | |

## 3. What I'm explicitly not designing here

- Any new Django models — Phase 1/2 close-out requires **zero new models** based on what I've verified. If P2-1 through P2-3 turn up a real gap requiring a new field or model, that's a small addition to this design, not a rewrite.
- Phase 3 (operational maintenance) and Phase 4 (sell) data models — per the spec, these need a separate scoping conversation before design work starts.

## 4. Risk notes

- **P1-3 (deleting investor_app):** I verified it's unregistered and unimported from `core`, but I have not exhaustively checked every script/CI config (e.g. `scripts/`, `Makefile`, CI workflows) for references to `investor_app`. Grep for `investor_app` repo-wide before deleting, not just within `core/`.
- **P2 verification tasks are manual, not automatable from what I've read** — I don't have a way to render your actual dashboard template or run your test suite from here; these need to be done in your own dev environment.
