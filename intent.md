# Intent: lease and keep it leased

**Author:** Phil Ruff · **Status:** proposed (approved by merging the PR that changes this file) · **Date:** 2026-11-02
**Next:** [spec.md](spec.md) (what we decided) · [plan.md](plan.md) (goals and proof) · Product context: [VISION.md](VISION.md)
**Supersedes:** "a functioning prei" (G0–G7), archived in [features/functioning-prei/](features/functioning-prei/). Its decisions, including the app nav, still stand.

## Problem

G0–G7 proved that one investor can walk the journey from growth areas to leasing on a seeded market. Leasing (step 9) is the weakest step: the journey only proves that a property can be clicked through to "Stabilized". An audit on 2026-11-02 of the code, the running container and the live site found:

- **Leasing doesn't connect to the rest of prei.** A signed lease's rent, dates and deposit stay on the leasing record. The portfolio, cash flow and actuals-vs-pro-forma never see them, so the investor types the rent in a second time.
- **The record can't be trusted.** Any stage can be set from any other stage, including backwards (the stage URLs and the kanban). A lease can be "signed" with no rent or start date. A blank or comma-formatted rent returns a 500 error. Stage history on the detail page is made up: the dates are never stored.
- **One applicant per listing.** A second application overwrites the first applicant's name. Screening is a pass/fail box and a note: no written criteria, and no record of why an applicant was declined.
- **No numbers behind leasing decisions.** prei's strength, a number with its source behind every decision, stops at acquisition. Nothing suggests an asking rent, shows what a vacant day costs, or flags a listing that sits too long.
- **The process stops at move-in.** There is no lease end-date view, no renewal, and no turnover back to a listing. The leasing page says to "use Portfolio" for renewals, but Portfolio has none (LIMIT-14).
- **Units are ignored.** `Property.units` exists, and VISION covers up to 4 units, but leasing has one record per property.
- **Nothing is hosted.** The Render service returns 404; only the docs site is live. No real investor can use prei yet.

## Proposed outcome

On the seeded market (Docker first, then hosted), an investor takes an acquired property from vacant to leased to renewed or re-let. Every leasing decision has a number and its source behind it, and the portfolio reflects the lease without re-entry:

1. **Price:** listing a unit shows a suggested rent, where it came from, and what each vacant day costs.
2. **Fill:** the listing collects any number of applicants. Each applicant is screened against criteria the investor wrote down before seeing any application, the same way for everyone, and the reason for each decision is kept.
3. **Sign:** a signed lease is the property's (or unit's) rent from its start date. Portfolio cash flow and actuals-vs-pro-forma use it.
4. **Keep:** leases ending within 90 days are surfaced. A renewal-or-turnover comparison prices both options. Renewing starts the next lease; turnover reopens the listing pre-filled.
5. **Hosted:** prei runs on a hosted URL with Postgres and backups, so a real investor can use it (after step 2).
6. **Screened by a provider:** an applicant can be screened through a paid provider, and the result is checked against the written criteria (after hosting).
7. **Measure:** days vacant, days to lease, showing-to-application conversion, rent vs suggested rent, and economic occupancy are tracked per property and across the portfolio.

### What "best in its field" means here

Leasing-operations tools (listing syndication, online applications, paid screening, e-sign, rent collection) do the paperwork. prei does not compete there (VISION non-goal: property management). The bar is to be the best decision tool for a buy-and-hold investor's leasing:

- Every leasing decision (asking rent, price drop, applicant, renew vs turnover) is shown with a number, its source and its confidence.
- Nothing is typed twice: a lease feeds rent, cash flow and variance automatically.
- Screening is consistent and on record by design (criteria written before the first application, a reason for every decision, no protected-class data stored).
- Leasing performance is measured and visible on the same screens as the investment returns.

## Affected users and systems

- **Users:** the buy-and-hold investor after closing, including owners of 2–4 unit properties and BRRRR investors who need a lease in place before a refinance.
- **Systems:** `LeasingPipelineProperty` and new leasing models in `core/models/`; `core/services/leasing.py` and the rent chain in `core/services/screening.py`; `core/views/leasing.py` and `templates/leasing/`; portfolio services and dashboard; `RentalIncome` and `MonthlyActuals`; the journey suite (`tests_bdd/`).

## Constraints

- Decimal money. Finance math (vacancy cost, renewal vs turnover) in services only. No Bootstrap; DESIGN.md enforced ([AGENTS.md](AGENTS.md)).
- Single-user. SQLite in the container. New models and migrations need approval (`migration-safety` skill).
- Free data on the critical path, except tenant screening (decision 3). Rent suggestions reuse the existing rent chain (VRM, stored estimate, Rentometer, HUD FMR). Rentcast stays behind the G1 measurement ([rent-coverage.md](docs/assessments/rent-coverage.md)).
- Minimum applicant data: name, contact, stated income, the screening result summary, the result for each criterion, and the decision with its reason. No SSN, date of birth, credit report files, or protected-class attributes, even with paid screening.
- No legal advice (VISION non-goal). prei records the investor's criteria and decisions. It does not write leases or adverse-action notices.
- No payment processing, listing syndication or tenant portal (VISION non-goal: property management).
- Hosted: Postgres, secrets from the environment, HTTPS, and a tested database restore before real leasing data goes in.

## Decisions (2026-11-02)

1. **Units:** a unit label on the lease for 2–4 unit properties. A Unit model only if the rent roll needs per-unit expenses (plan.md L10).
2. **Hosted deploy:** comes right after G9 (G10), so the first hosted users get pricing and screening, and renewals land on a hosted app.
3. **Paid tenant screening:** in scope (G12), after hosting. The screening provider collects consent, SSN and date of birth directly from the applicant; prei stores only the result and checks it against the investor's written criteria. The choice of provider is a human decision.
4. **Renewal and turnover:** the renew-or-re-let *decision* is analytics and in scope. Maintenance and rent collection stay out (VISION non-goal). Confirmed for now; revisit if renewals pull in tenant communication.
