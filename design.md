# Design & Plan: Alpha → MVP (Phase 1 close-out + Phase 2 verification)

Companion to `specification-alpha-mvp.md`. Covers only Phase 1 (close-out) and Phase 2
(verification) in implementation detail, per that spec's scoping — Phases 3/4 are
intentionally not designed yet.

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
