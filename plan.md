# Plan: a functioning prei

**From:** [intent.md](intent.md) and [spec.md](spec.md), 2026-10-29 · **Status:** proposed (approved by merging the PR that changes this file)
**Status of work lives on the board, never here:** [Real Estate Investor project](https://github.com/users/paruff/projects/3) (how it works: [AGENTS.md](AGENTS.md) "Workflow"). Update this file in the same PR when implementation departs from it.

## How this plan works

- **One goal at a time.** Each goal is a GitHub milestone with the same name. A goal is done when its **Proof** passes. The next goal starts after that, not before.
- **The proof comes first.** Every goal's first row writes the failing test that is its proof. Further rows fix what that test shows is broken; add them to this file when the test finds them, not in advance.
- **Each row is one issue** in its goal's milestone. A row with no issue yet says `no issue yet`.
- **Anything not needed for a goal goes to [Later](#later-no-milestone).**

## G0: runs in Docker, tested end to end

**Outcome:** on a clean checkout, `docker compose up` and one seed command give a running prei with one market's data (default Dallas, TX).
**Proof:** `tests/acceptance/` passes with `BASE_URL` pointing at the container (AC-10, AC-11).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G0.1 | `make docker-accept`: build, up, seed, run `tests/acceptance/` against the container, down. Fails today. | FR-10, AC-11 | `Makefile` | [#466](https://github.com/paruff/prei/issues/466) |
| G0.2 | Compose starts without the external `observability-lab` network (make OTEL optional) | FR-10, AC-10 | `docker-compose.yml` | [#467](https://github.com/paruff/prei/issues/467) |
| G0.3 | One seed command for one market: `seed_markets` + `populate_growth_areas` + properties, inside the container; fix `make docker-dev` (`web` vs the `preiweb` service) | FR-11, AC-10 | `Makefile`, `core/management/commands/` | [#468](https://github.com/paruff/prei/issues/468) |

## G1: find and decide (journey steps 1–4)

**Outcome:** on the seeded market, the investor ranks growth areas, discovers properties, screens them with yield and price-to-rent, and underwrites the best one.
**Proof:** a journey scenario for steps 1–4 passes against the container (AC-12), and the rent report is committed (AC-13).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G1.1 | Journey scenario, steps 1–4, against the container. Fails until it passes. | FR-12, AC-12 | `tests_bdd/features/journey.feature` (new), `tests_bdd/steps/` | [#469](https://github.com/paruff/prei/issues/469) |
| G1.2 | Rent report: coverage by source (VRM, Rentometer, HUD FMR) on the seeded market; HUD FMR vs Rentcast quality for Rentcast's fee; recommendation on FR-1 | NFR-7, NFR-1, AC-13 | `docs/assessments/rent-coverage.md` (new), `scripts/` | [#470](https://github.com/paruff/prei/issues/470) |

Rows G1.3 onwards are whatever G1.1 finds broken. Async work (FR-7) joins here only if a step times out.

## G2: buy and own (journey steps 5–7)

**Outcome:** a screened property goes from offer through due diligence and closing to acquired, and appears in the portfolio with complete data and monthly actuals.
**Proof:** a journey scenario for steps 5–7 passes against the container (AC-14).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G2.1 | Journey scenario, steps 5–7, against the container | FR-13, AC-14 | `tests_bdd/features/journey.feature`, `tests_bdd/steps/` | [#471](https://github.com/paruff/prei/issues/471) |
| G2.2 | Acquired property is complete at creation (LIMIT-12) | FR-13 | `core/services/` pipeline acquisition | [#472](https://github.com/paruff/prei/issues/472) |

## G3: grow (journey steps 8–9)

**Outcome:** BRRRR and leasing work on a property acquired in G2.
**Proof:** scenarios for steps 8 and 9 pass against the container (AC-15).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G3.1 | Journey scenarios, steps 8–9, against the container | FR-14, AC-15 | `tests_bdd/features/journey.feature`, `tests_bdd/steps/` | [#473](https://github.com/paruff/prei/issues/473) |

## In flight (not a goal)

- **#457:** dependency security bumps (Django 6.0.8, Pillow 13, DRF 3.18.2, aiohttp 3.14.4). Main CI is red on the Trivy scan until it merges. Needs dependency approval.
- **#458:** CSP, Permissions-Policy and CORP headers (FR-9, AC-8). Merge after #457.

## Later (no milestone)

Kept from the superseded beta-readiness plan; spec IDs unchanged. None of these has an issue yet.

| Row | Work | Spec |
|---|---|---|
| L1 | Rentcast adapter, only if G1.2 recommends it | FR-1, AC-1, AC-2 |
| L2 | ATTOM rent probe | FR-2 |
| L3 | GACS backtest script and report | FR-3, AC-3, NFR-2 |
| L4 | GACS signal completion: schools, supply, county employment | FR-4 |
| L5 | Real crime data (FBI CDE, then fallback) | FR-5, AC-4, NFR-3 |
| L6 | SRI on external scripts; authenticated ZAP 0 FAIL / 0 WARN | FR-9, AC-9 |
| L7 | Hosted deploy (Render or other) with Postgres | NFR-6 |
| L8 | Design-system drift ([DESIGN.md](DESIGN.md) "Do's and Don'ts") | — |

Also later: portfolio analytics, saved searches, partner API. Deferred by decision: team sharing (#371, #372).

## Risks

- **Seeding needs free keys** (Census, BLS, HUD) in `.env`. If a key or API is unavailable, G0.3 commits a small fixture dataset for the market instead.
- **The journey scenario finds a lot broken.** That is the point: fix in journey order and keep each fix row small.
- **HUD FMR is too coarse for screening.** G1.2 says so with numbers, and L1 (Rentcast) moves into G1.

## Proof summary

| Goal | Proof | Command |
|---|---|---|
| G0 | Acceptance suite green against the container | `make docker-accept` |
| G1 | Steps 1–4 scenario green; rent report committed | `make docker-accept` (runs the journey feature too) |
| G2 | Steps 5–7 scenario green | same |
| G3 | Steps 8–9 scenarios green | same |
| Always | Tests, lint and types green | CI `ci-quality.yml` |
