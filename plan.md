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

## G4: trust the numbers

**Outcome:** every page loads, and the figures an investor acts on are right: an acquired property's equity, cash flow, purchase price and verdict, formatted one way everywhere.
**Proof:** a route smoke test and journey assertions on the portfolio and dashboard pass against the container (AC-16). Findings: [UX audit](docs/assessments/ux-ui-audit-2026-10-30.md) §1.

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G4.1 | Proof: smoke-test every named GET route for the demo user; journey asserts equity, cash flow, purchase price and verdict of the acquired property. Fails today. | FR-15, AC-16 | `tests/acceptance/test_routes.py` (new), `tests_bdd/` | [#503](https://github.com/paruff/prei/issues/503) |
| G4.2 | Financing comparison page 500 (`sub` filter not loaded); rent cushion computed in the service, not the template | FR-15 | `templates/properties/financing_comparison.html`, `core/services/` | [#504](https://github.com/paruff/prei/issues/504) |
| G4.3 | Portfolio: equity = value − loan, cash flow net of expenses and debt service, closing price not list price, GACS from the property's market | FR-15 | `core/services/` portfolio, `core/views/`, `templates/portfolio_dashboard.html` | [#505](https://github.com/paruff/prei/issues/505) |
| G4.4 | Dashboard: verdict and score consistent with CoC and cap rate for acquired properties; property count matches `/properties/` | FR-15 | `core/services/scoring.py`, dashboard view | [#506](https://github.com/paruff/prei/issues/506) |
| G4.5 | One `money`, `pct`, `score` filter set, used by every template | FR-15 | `core/templatetags/`, `templates/` | [#507](https://github.com/paruff/prei/issues/507) |
| G4.6 | Remove the shadowed second `markets/` route | FR-15 | `core/urls.py` | [#508](https://github.com/paruff/prei/issues/508) |

## G5: DESIGN.md enforced

**Outcome:** DESIGN.md is the source of the UI because a check enforces it, and the palette meets WCAG AA.
**Proof:** `design-lint` pre-commit hook passes with no token, colour or `<style>` allow-list entries (AC-17). Findings: audit §2–3.

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G5.1 | Proof: `design-lint` hook (undefined `var(--x)`, hex/`rgb(` outside `tokens.css`, template `<style>` outside `exports/`, Bootstrap classes), with today's violations in an allow-list | FR-16, AC-17 | `scripts/check_design.py` (new), `.pre-commit-config.yaml` | [#509](https://github.com/paruff/prei/issues/509) |
| G5.2 | Map the 17 undefined tokens; replace off-palette blue and Tailwind colours; fix the invisible logo; delete `theme.css`; move template `<style>` blocks into `base.css` | FR-16 | `static/css/`, 5 templates | [#510](https://github.com/paruff/prei/issues/510) |
| G5.3 | WCAG AA: primary fill reaches 4.5:1 with white text, no `neutral-200` text, `:focus-visible` outline restored; DESIGN.md updated | FR-16 | `static/css/tokens.css`, `static/css/base.css`, `static/css/pipeline.css`, `DESIGN.md` | [#511](https://github.com/paruff/prei/issues/511) |
| G5.4 | Links in tables and cards use the palette, not browser blue; REVIEW.md asks for screenshots on UI PRs | FR-16 | `static/css/base.css`, `static/css/pipeline.css`, `REVIEW.md` | [#512](https://github.com/paruff/prei/issues/512) |

## G6: every screen on the design system

**Outcome:** no screen renders browser-default controls or Bootstrap leftovers, and every screen works at phone width.
**Proof:** `make ui-check` passes against the container and the design-lint allow-list is empty (AC-18). Findings: audit §2–4.

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G6.1 | Proof: `make ui-check` crawls named routes at 1280 and 390px and fails on non-200, horizontal scroll, unlabelled inputs and AA contrast. Fails today. | FR-17, AC-18 | `Makefile`, `scripts/ui_check.py` (new) | [#513](https://github.com/paruff/prei/issues/513) |
| G6.2 | Investment Targets and Screening Settings forms; percentage fields take percentages | FR-17 | `templates/investment_targets/`, `templates/pipeline/`, `core/forms.py` | [#514](https://github.com/paruff/prei/issues/514) |
| G6.3 | Properties list, edit and compare | FR-17 | `templates/properties/`, `core/forms.py` | [#515](https://github.com/paruff/prei/issues/515) |
| G6.4 | VRM, HUD and USDA lists and details | FR-17 | `templates/vrm_properties/`, `templates/hud_properties/`, `templates/usda_properties/` | [#516](https://github.com/paruff/prei/issues/516) |
| G6.5 | Sign-in, onboard and system pages | FR-17 | `templates/registration/`, `templates/onboard.html`, `templates/system.html` | [#517](https://github.com/paruff/prei/issues/517) |
| G6.6 | Pipeline screens: screener filters, kanban discover panel and scroll affordance, Growth Areas table clipping, `pipeline.css` form and verdict classes onto base classes | FR-17 | `templates/pipeline/`, `templates/growth_areas.html`, `static/css/pipeline.css` | [#518](https://github.com/paruff/prei/issues/518) |

## G7: one journey through the nav

**Outcome:** the nav follows the investor journey, and every step leads to the next without typing a URL.
**Proof:** the journey scenario walks steps 1–9 through links only, against the container (AC-19). Needs a human decision on the nav before G7.2 (Gate: `intent`). Findings: audit §5.

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G7.1 | Proof: journey steps follow nav and page links only. Fails today. | FR-18, AC-19 | `tests_bdd/steps/journey_steps.py` | [#519](https://github.com/paruff/prei/issues/519) |
| G7.2 | Nav = Markets · Pipeline · Portfolio · Leasing, settings under the avatar; `/growth/` is the Markets landing; fold the dashboard screener and `/properties/` into Pipeline and Portfolio; hide the app nav from anonymous users | FR-18 | `templates/base.html`, `core/urls.py`, views | [#520](https://github.com/paruff/prei/issues/520) |
| G7.3 | Acquired property next-step bar: enter actuals, start leasing, model BRRRR pre-filled from the property | FR-18 | `templates/pipeline/pipeline_detail.html`, `core/views/` | [#521](https://github.com/paruff/prei/issues/521) |
| G7.4 | Plain language: no raw enums, "Remove" not "Kill", GACS explained, empty states via the partial, forms blank instead of `0` | FR-18 | `templates/`, `core/forms.py` | [#522](https://github.com/paruff/prei/issues/522) |

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
| L8 | Design-system drift: moved to G5 and G6 | FR-16, FR-17 |

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
| G4 | Route smoke test and portfolio/dashboard assertions green | same |
| G5 | Design lint green, no token/colour allow-list | `pre-commit run design-lint --all-files` |
| G6 | UI check green, design-lint allow-list empty | `make ui-check` |
| G7 | Journey walks by links only | `make docker-accept` |
| Always | Tests, lint and types green | CI `ci-quality.yml` |
