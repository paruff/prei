# Intent: beta readiness, part 1 (trustworthy screening data)

**Author:** Phil Ruff · **Status:** draft · **Date:** 2026-10-24
**Next:** [spec.md](spec.md) (what we decided) · [plan.md](plan.md) (how and in what order) · Product context: [VISION.md](VISION.md), [discovery-brief.md](discovery-brief.md)

## Problem

A buy-and-hold investor can't yet trust prei's screening enough to act on it:

- Only VRM listings carry a rent figure, so yield and price-to-rent screening is skipped for HUD, USDA, ATTOM and county sources.
- Growth Area Composite Score (GACS) weights are experimental. Nothing shows they predict appreciation.
- Crime scores are state-level placeholders (TX 2.5, CA 3.5, others 3.0).
- Changing screening criteria re-screens synchronously and can hit the 30s Gunicorn timeout.
- The authenticated ZAP scan still reports 8 WARN findings (LIMIT-23).

## Proposed outcome

At beta, for a single investor:

- At least 90% of discovered properties have a rent estimate, so yield and price-to-rent screening runs.
- GACS weights are backed by a published backtest.
- Crime data is real and at ZIP or census-tract level.
- Re-screening never blocks a page.
- Production responses pass an authenticated ZAP scan with 0 FAIL and 0 WARN.

## Affected users and systems

- **Users:** one buy-and-hold SFR investor per account. No teams or sharing.
- **Systems:** screening and discovery services, market scoring (GACS), data-source adapters in `core/integrations/`, background work, security middleware and `templates/base.html`, and the production deploy (Render, Postgres).

## Constraints

- Decimal money. Service-layer boundaries. No Bootstrap. GitOps deploys ([AGENTS.md](AGENTS.md)).
- Single-user for now.
- SQLite for local runs and Postgres in production. No local Postgres.
- Django 6.0.
- Paid APIs (Rentcast, ATTOM) stay within budget. Each new source gets a spike before commitment.

## Open questions

1. Rentcast: cost and coverage for TX, FL and TN. The spike answers this.
2. Crime: is any ZIP-level source viable (FBI CDE retry, then alternatives)?
3. Background work: Celery and Redis (spec FR-7), or something lighter now that local runs stay on SQLite? Decide at the spec gate.
4. Is backtest R² ≥ 0.4 achievable? If not, what do we publish?
5. Zero-downtime deploy (spec NFR-6) relies on canary, which is a VISION non-goal. Drop it from beta?
