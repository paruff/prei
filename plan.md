# Plan: lease and keep it leased

**From:** [intent.md](intent.md) and [spec.md](spec.md), 2026-11-02 · **Status:** proposed (approved by merging the PR that changes this file)
**Status of work lives on the board, never here:** [Real Estate Investor project](https://github.com/users/paruff/projects/3) (how it works: [AGENTS.md](AGENTS.md) "Workflow"). Update this file in the same PR when implementation departs from it.
**Previous plan:** G0–G7, archived in [features/functioning-prei/plan.md](features/functioning-prei/plan.md). Its last open row, #578 (one test tree), finishes in G7 before G8 starts.

## How this plan works

- **One goal at a time.** Each goal is a GitHub milestone with the same name. A goal is done when its **Proof** passes. The next goal starts after that, not before.
- **The proof comes first.** Every goal's first row writes the failing test that is its proof. Further rows fix what that test shows is broken; add them to this file when the test finds them.
- **Each row is one issue** in its goal's milestone. A row with no issue yet says `no issue yet`.
- **Anything not needed for a goal goes to [Later](#later-no-milestone).**

## G8: one lease, one record

**Tracking:** [#617](https://github.com/paruff/prei/issues/617)

**Outcome:** the leasing record can be trusted, and a signed lease is the property's rent in the portfolio without re-entry.
**Proof:** the journey's leasing step signs at 1800 and the portfolio uses 1800 (AC-20); bad and out-of-order input is refused cleanly (AC-21); every stage reached has a stored date (AC-22).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G8.1 | Proof: journey asserts portfolio rent and cash flow from the signed lease, rejected backward/skip moves, a field error on `1,800` rent, and stage dates on the detail page. Fails today. | FR-19–22, AC-20–22 | `tests_bdd/features/journey.feature`, `tests_bdd/steps/journey_steps.py` | [#589](https://github.com/paruff/prei/issues/589) |
| G8.2 | One stage machine in the service: forward one step, required data per stage, hold/resume/withdraw; the `Stage` enum is the only order; views and kanban call it | FR-19 | `core/services/leasing.py`, `core/views/leasing.py`, `templates/leasing/` | [#590](https://github.com/paruff/prei/issues/590) |
| G8.3 | Stage events: a `LeasingStageEvent` row (stage, date) per change; detail page shows dates and days per stage | FR-20 | `core/models/pipeline.py` (migration, needs approval), `core/services/leasing.py`, `templates/leasing/leasing_detail.html` | [#591](https://github.com/paruff/prei/issues/591) |
| G8.4 | Leasing forms: add, application, screening, lease, move-in, stabilize through Django forms with field errors | FR-22, NFR-10 | `core/forms.py`, `core/views/leasing.py`, `templates/leasing/stage_form.html` | [#592](https://github.com/paruff/prei/issues/592) |
| G8.5 | Signing creates `RentalIncome` effective at lease start; portfolio and actuals variance read it; fix the leasing banner that points to Portfolio for renewals | FR-21 | `core/services/leasing.py`, portfolio services, `templates/leasing/leasing_list.html` | [#593](https://github.com/paruff/prei/issues/593) |
| G8.6 | Unit label on leasing records for `units > 1`; one active listing and one current lease per unit | FR-23 | `core/models/pipeline.py` (migration), `core/services/leasing.py` | [#594](https://github.com/paruff/prei/issues/594) |
| G8.7 | Seed one leased property for the demo user so Leasing isn't empty on a fresh container | FR-21 | `core/management/commands/seed_market.py` | [#595](https://github.com/paruff/prei/issues/595) |

## G9: price and fill

**Tracking:** [#618](https://github.com/paruff/prei/issues/618)

**Outcome:** every listing shows a suggested rent and what vacancy costs, and every applicant is screened against written criteria, the same way, on record.
**Proof:** the journey's two-applicant scenario (AC-23), the suggested rent and vacancy cost on the listing (AC-24), and the restricted-field check (AC-25).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G9.1 | Proof: journey lists at a suggested rent, adds two applicants, declines one on the income criterion with its reason, approves the other; restricted-field unit test. Fails today. | FR-24–27, AC-23–25, NFR-8 | `tests_bdd/`, `core/tests/` | [#596](https://github.com/paruff/prei/issues/596) |
| G9.2 | `Applicant` model (many per listing, minimal fields, status, reason); approving one closes the others; migrate the single-applicant fields | FR-26, NFR-8 | `core/models/pipeline.py` (migration), `core/services/leasing.py`, `templates/leasing/` | [#597](https://github.com/paruff/prei/issues/597) |
| G9.3 | Leasing criteria (versioned like `ScreeningCriteria`); score each applicant per criterion; store the version with the decision | FR-27 | `core/models/pipeline.py`, `core/services/leasing.py`, settings screen | [#598](https://github.com/paruff/prei/issues/598) |
| G9.4 | Suggested rent from the existing rent chain with source and confidence, shown on add and detail; asking vs suggested | FR-24 | `core/services/screening.py` (reuse `_get_monthly_rent` logic), `core/services/leasing.py` | [#599](https://github.com/paruff/prei/issues/599) |
| G9.5 | Vacancy clock (vacancy start → move-in) and cost so far: daily rent + daily carrying costs; on list, kanban and detail; Decimal unit tests | FR-25, NFR-9 | `core/services/leasing.py`, `templates/leasing/` | [#600](https://github.com/paruff/prei/issues/600) |
| G9.6 | Listing health prompt after N days or showings without an application | FR-28 | `core/services/leasing.py`, `templates/leasing/` | [#601](https://github.com/paruff/prei/issues/601) |

## G10: hosted

**Tracking:** [#619](https://github.com/paruff/prei/issues/619)

**Outcome:** a real investor can use prei on a hosted URL, and their leasing data is backed up and can be restored.
**Proof:** the acceptance suite and journey pass against the hosted URL, and a backup restore succeeds (AC-28).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G10.1 | Proof: a workflow runs `tests/acceptance/` and the journey with `BASE_URL` set to the hosted URL. Fails today (404). | FR-33, AC-28 | `.github/workflows/`, `Makefile` | [#602](https://github.com/paruff/prei/issues/602) |
| G10.2 | Hosted service and Postgres up from `render.yaml` (or another host): account, plan and secrets are a human step | FR-33 | `render.yaml`, `docs/how-to-guides/render-deploy.md` | [#603](https://github.com/paruff/prei/issues/603) |
| G10.3 | Journey runs on Postgres in Docker before the hosted cut-over, so no SQLite-only behaviour reaches production | FR-33 | `docker-compose.yml`, `Makefile` | [#604](https://github.com/paruff/prei/issues/604) |
| G10.4 | Scheduled backups and a restore drill (script and runbook) | FR-33, AC-28 | `scripts/`, `docs/how-to-guides/` | [#605](https://github.com/paruff/prei/issues/605) |
| G10.5 | Clear the WARN-level ZAP findings on the hosted URL (LIMIT-23) | FR-33, FR-9 | `config/settings.py`, middleware | [#606](https://github.com/paruff/prei/issues/606) |
| G10.6 | Migrations run before the new release takes traffic | NFR-6 | `render.yaml`, start command | [#607](https://github.com/paruff/prei/issues/607) |

## G11: keep it leased

**Tracking:** [#620](https://github.com/paruff/prei/issues/620)

**Outcome:** expiring leases are surfaced early, the investor renews or re-lets based on a priced comparison, and leasing KPIs sit next to the returns.
**Proof:** the journey renews a lease and the portfolio shows the new rent (AC-26); a turnover reopens a pre-filled listing and the KPIs show the vacancy (AC-27).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G11.1 | Proof: journey sees the lease in the 90-day list, compares renew vs turnover, renews; then a turnover reopens a listing. Fails today. | FR-29–32, AC-26–27 | `tests_bdd/` | [#608](https://github.com/paruff/prei/issues/608) |
| G11.2 | Lease end view (90/60/30 days) on Leasing; flag on the portfolio dashboard | FR-29 | `core/services/leasing.py`, `core/views/leasing.py`, `templates/portfolio_dashboard.html` | [#609](https://github.com/paruff/prei/issues/609) |
| G11.3 | Renew-vs-turnover service and page: both options over the next term, break-even increase; Decimal unit tests | FR-30, NFR-9 | `core/services/leasing.py`, `templates/leasing/` | [#610](https://github.com/paruff/prei/issues/610) |
| G11.4 | Renew (next lease + `RentalIncome`) and turnover (pre-filled listing, vacancy clock from move-out) actions | FR-31 | `core/services/leasing.py`, `core/views/leasing.py` | [#611](https://github.com/paruff/prei/issues/611) |
| G11.5 | Leasing KPIs per property and portfolio-wide, on Leasing and the portfolio dashboard; LIMIT-14 updated | FR-32, NFR-9 | `core/services/leasing.py`, portfolio services, `docs/KNOWN_LIMITATIONS.md` | [#612](https://github.com/paruff/prei/issues/612) |

## G12: screened by a provider

**Tracking:** [#621](https://github.com/paruff/prei/issues/621)

**Outcome:** an investor screens an applicant through a paid provider without prei ever holding the report or the applicant's SSN, and the result is checked against their written criteria.
**Proof:** a screening request against the provider sandbox (or a recorded fake in CI) is stored as a summary and checked against the criteria (AC-29).

| Row | Work | Spec | Files | Issue |
|---|---|---|---|---|
| G12.1 | Proof: acceptance test requests screening for an applicant against a recorded fake and asserts the stored summary, criteria result and no restricted field. Fails today. | FR-34, AC-29, NFR-11 | `tests/`, `tests_bdd/` | [#613](https://github.com/paruff/prei/issues/613) |
| G12.2 | Choose the provider (API access, fee per report, applicant-paid option, onboarding for the investor): human decision | FR-34 | `docs/assessments/` | [#614](https://github.com/paruff/prei/issues/614) |
| G12.3 | Provider adapter: request, verified callback, result summary; key from the environment | FR-34, NFR-11 | `core/integrations/screening/` (new), `core/views/leasing.py` | [#615](https://github.com/paruff/prei/issues/615) |
| G12.4 | Check the provider result against the written criteria; fee recorded as a leasing cost | FR-34, FR-27 | `core/services/leasing.py`, `templates/leasing/` | [#616](https://github.com/paruff/prei/issues/616) |

## Later (no milestone)

Rows L1–L9 from the [archived plan](features/functioning-prei/plan.md#later-no-milestone) are unchanged (Rentcast, ATTOM, GACS backtest and signals, crime data, SRI/ZAP, hygiene L9), except L7 (hosted deploy), which is now G10. Added:

| Row | Work | Spec |
|---|---|---|
| L10 | Unit model with per-unit expenses, only if the unit label (G8.6) is not enough | FR-23 |
| L12 | Market days-on-market and rent comps per ZIP to benchmark a listing, once a free or measured source exists | FR-28, FR-32 |

## Risks

- **Migrations on live leasing data.** G8.3, G8.6 and G9.2 change models; each is additive with a data migration and needs approval first.
- **Suggested rent is only as good as the rent chain.** HUD FMR is coarse ([rent-coverage.md](docs/assessments/rent-coverage.md)); show source and confidence and never present it as a comp.
- **Screening records carry legal weight.** prei stores the investor's criteria and decisions; wording stays factual, with no advice and no protected-class data (NFR-8).
- **Scope pull toward property management.** Anything about collecting rent, maintenance or tenant communication goes to the VISION non-goal list, not a row.

## Proof summary

| Goal | Proof | Command |
|---|---|---|
| G8 | Lease reaches the portfolio; bad input refused; stage dates stored | `make docker-accept` |
| G9 | Two-applicant screening, suggested rent, vacancy cost; restricted-field check | `make docker-accept`, `.venv/bin/python -m pytest core/tests` |
| G10 | Acceptance and journey green on the hosted URL; restore drill passes | hosted workflow |
| G11 | Renewal and turnover through the journey | `make docker-accept` |
| G12 | Provider screening stored as a summary and checked against criteria | `make docker-accept` |
| Always | Tests, lint, types, design lint, UI check green | CI pr gate, `make ui-check` |
