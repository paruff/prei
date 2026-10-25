# Plan: beta readiness

**From:** [intent.md](intent.md) and [spec.md](spec.md), 2026-10-24 · **Status:** draft
**Status of work lives on the board, never here:** [Real Estate Investor project](https://github.com/users/paruff/projects/3) (how it works: [AGENTS.md](AGENTS.md) "Workflow"). Update this file in the same PR when implementation departs from it.

## Release milestones

Each release is a GitHub milestone, and each row is one issue in that milestone. A row with no issue yet says `no issue yet`.

### Beta A: rent data and GACS

| Row | Work | Spec | Issue |
|---|---|---|---|
| A1 | Rentcast spike: key, TX/FL/TN coverage, latency < 500ms | FR-1, AC-1 | no issue yet |
| A2 | Rentcast adapter and rent fallback chain VRM → Rentcast → ATTOM → HUD FMR | FR-1, AC-2, NFR-1 | no issue yet |
| A3 | ATTOM rent probe; add it to the chain if the field exists | FR-2 | no issue yet |
| A4 | GACS backtest script and published report | FR-3, AC-3, NFR-2 | no issue yet |
| A5 | GACS signal completion: schools, supply constraint, county employment | FR-4 | no issue yet |

### Beta B: crime data and background work

| Row | Work | Spec | Issue |
|---|---|---|---|
| B1 | FBI CDE retry with the correct endpoint | FR-5 | no issue yet |
| B2 | Crime adapter fallback (SpotCrime, CityProtect) if B1 fails | FR-5, AC-4, NFR-3 | no issue yet |
| B3 | Async re-screen, discovery batch and VRM scrape | FR-7, AC-6, NFR-4 | no issue yet |

### Beta C: security headers

| Row | Work | Spec | Issue |
|---|---|---|---|
| C1 | django-csp: CSP, Permissions-Policy and CORP headers | FR-9, AC-8 | no issue yet |
| C2 | SRI on external scripts in `base.html` | FR-9, AC-9 | no issue yet |
| C3 | Authenticated ZAP scan: 0 FAIL, 0 WARN | FR-9 | no issue yet |

### Later (no milestone)

Portfolio analytics, leasing pipeline completion, advanced market intelligence, partner API. Deferred by the 2026-10-24 decisions: team pipeline sharing (#371, #372; single-user for now) and local Postgres (SQLite stays local).

## Files that change

| Row | Files |
|---|---|
| A1–A3 | `core/integrations/sources/rentcast_adapter.py` (new), `core/integrations/sources/attom_adapter.py`, `core/services/screening.py` (`_get_rent_estimate` fallback chain), `core/integrations/health_monitor.py` |
| A4–A5 | `scripts/backtest_gacs.py` (new), `core/services/market_scoring.py`, `core/integrations/market/schools.py`, `core/integrations/market/supply.py` (new) |
| B1–B2 | `core/integrations/market/crime.py`. Keep the interface `get_crime_score(zip) -> (score, confidence, source)`. |
| B3 | Depends on open question 3 in intent.md. If Celery: `core/celery.py`, `core/tasks.py`, `docker-compose.yml` (Redis), `render.yaml` (worker). |
| C1–C2 | `settings.py`, `core/middleware/security_headers.py`, `templates/base.html`, `requirements.txt` (django-csp; needs dependency approval) |
| All | `docs/CHANGE_IMPACT_MAP.md`, `docs/KNOWN_LIMITATIONS.md` (resolve LIMIT-01, -02, -11, -15, -17, -23) |

## Order of work

1. In parallel: A1, A4 and B1 (spikes and scripts; no shared files).
2. A2 after A1. A3 any time, then fold it into A2's chain.
3. A5 after A4 shows which signals matter.
4. B2 only if B1 fails. B3 after the spec gate answers open question 3.
5. C1 and C2 in parallel, then C3.

A2, A3 and B3 all touch `core/services/screening.py`, so run them in sequence, not as parallel worktrees.

## Risks

- **Rentcast cost or coverage is too low.** A2 falls back to ATTOM and HUD FMR, and NFR-1 may slip.
- **The backtest fails R² ≥ 0.4.** Publish the result with confidence bands; don't tune until it passes.
- **No viable crime source.** Keep the placeholder, labelled low-confidence in the UI (VISION principle 7).
- **CSP breaks inline scripts.** Use report-only mode first.

## Proof

A release is done when its rows are closed and these hold:

| Gate | How verified |
|---|---|
| Tests, lint and types green | CI `ci-quality.yml` |
| Rent coverage ≥ 90% (Beta A) | Sample discovered properties on the live system |
| GACS backtest report published (Beta A) | `scripts/backtest_gacs.py` output committed |
| ZAP 0 FAIL / 0 WARN (Beta C) | CI `zap-authenticated-scan` |
| Release tagged and deployed | release-please PR merged; post-deployment pipeline green |
