# Intent: a functioning prei

**Author:** Phil Ruff · **Status:** proposed (approved by merging the PR that changes this file) · **Date:** 2026-10-29
**Next:** [spec.md](spec.md) (what we decided) · [plan.md](plan.md) (goals and proof) · Product context: [VISION.md](VISION.md)
**Supersedes:** "beta readiness, part 1" (approved in #452). Its requirements keep their spec IDs and move to plan.md "Later".

## Problem

prei has code for every step of the [investor journey](VISION.md#the-investor-journey), but nobody has shown that one investor can walk the journey end to end:

- Nothing is deployed. Render is not running, and no environment runs the journey on real data.
- Growth-area scores (GACS) exist only after someone runs `populate_growth_areas` by hand ([VISION.md](VISION.md) riskiest assumption).
- `docker compose up` fails on a clean machine: it needs the external `observability-lab` network.
- Tests check pages and endpoints one at a time. No test walks the journey from growth areas to the portfolio.
- Plans kept growing (beta readiness, the product strategy, audits, a current-state doc), and they aimed at data quality before the product worked.

## Proposed outcome

One investor, one seeded market, running locally in Docker:

- `docker compose up` starts prei with that market's data loaded.
- Acceptance tests walk journey steps 1–9 against the running container and pass.
- Rent coverage, and how good HUD FMR rent data is compared with Rentcast for its fee, are measured and written down.

## Affected users and systems

- **Users:** one buy-and-hold investor per account.
- **Systems:** `Dockerfile`, `docker-compose.yml`, `Makefile`, seed commands in `core/management/commands/`, screening and rent lookup (`core/services/screening.py`), the pipeline and portfolio, and the acceptance suites (`tests/acceptance/`, `tests_bdd/`).

## Constraints

- Decimal money. Service-layer boundaries. No Bootstrap ([AGENTS.md](AGENTS.md)).
- Single-user. SQLite in the container; Postgres only when a hosted deploy returns.
- Free data keys only on the critical path (Census, BLS, HUD). Paid APIs (Rentcast, ATTOM, Rentometer) need the measurement first.
- Django 6.0. Short-lived branches, squash-merged to `main` through PRs.

## Open questions

1. Which market is seeded first? Default: Dallas, TX (the Dallas County scraper exists).
2. Is HUD FMR rent good enough for screening, or is Rentcast worth its fee? G1 measures it.
3. When does a hosted deploy (Render or other) come back? After G3, or earlier if G0 proves easy.
