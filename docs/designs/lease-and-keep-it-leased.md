# Lease and keep it leased: fix the lease record, then price and renew

*   **Author:** Phil Ruff
*   **Status:** Draft
*   **Date:** 2026-11-06

--------------------------------------------------------------------------------

## Overview

prei walks one investor from growth areas to closing on a seeded market. Leasing, the last step, is the weak one. The investor plans to buy a property and lease it soon, and other investors should be able to run prei themselves by pulling a Docker image from GHCR.

This design covers three pieces of work, in this order:

1.  **Fix:** make the lease record trustworthy, and make a signed lease the property's rent in the portfolio without retyping.
2.  **Price:** show a suggested rent with its source, and what each vacant day costs.
3.  **Keep:** show leases that end soon, and compare renewing with re-letting.

It narrows the goals in `intent.md` (G8 to G12). Applicant screening against written criteria, hosting, and paid tenant-screening are out of scope here.

## Terms

*   **Fix** = goal G8 (one lease, one record). **Price** = FR-24, 25, 28. **Keep** = FR-29 to 32. **Fill** = FR-26, 27 (deferred). Goals and IDs are in [plan.md](../../plan.md), [spec.md](../../spec.md) and [intent.md](../../intent.md).
*   **The brief** = [concepts_brief.md](reviews/lease-and-keep-it-leased/concepts_brief.md). **Option A** = the first variant in each Alternatives entry.
*   Work items are the rows of `plan.md` (see "Detailed Implementation Plan"); "PR" in this design means the PR that closes one row.

## The Problem

The audit behind `intent.md` and a re-check of the code on 2026-11-05 show these problems in today's leasing:

*   **A signed lease never reaches the portfolio.** The leasing code never touches `RentalIncome`. The investor types the rent in a second time.
*   **The record cannot be trusted.** Any stage can be set from any other stage, backwards or forward, from the per-stage URLs and the kanban. Stage order is repeated in several places. A lease can be signed with no rent or start date. A blank rent or `1,800` raises a 500 error (`leasing_lease` and `leasing_add` pass raw POST text to `Decimal`), and the start date is assigned from raw POST text with no validation. The stage history on the detail page shows dates that were never stored.
*   **No numbers behind leasing decisions.** Nothing suggests an asking rent, shows what a vacant day costs, or flags a listing that sits too long.
*   **The process stops at move-in.** There is no list of ending leases, no renewal, and no turnover.

Fixing the first problem is harder than the plan assumes. The portfolio does not read `RentalIncome` for cash flow. `core/services/portfolio.py`, `scoring.py`, `projections.py` and `financing_comparison.py` read `Property.monthly_rent_gross`. Only the monthly series reads `RentalIncome`, and it places each row in the one month of its `effective_date`. `property_service.py` sums every `RentalIncome` row on a property, so adding a lease row next to a manual row would double the income. Variance was not traced end to end; the rule chosen below needs its own test. `RentalIncome` has no link to a lease and no unique constraint, so signing twice would add a second row.

Suggested rent has a similar trap. `_get_monthly_rent` in `core/services/screening.py` returns the stored `PipelineProperty.estimated_rent` before trying any market source. After purchase, that stored value is the rent used to justify buying, so a "suggestion" built on it only repeats the pro-forma.

The proposed solution is to do the work in the order Fix, Price, Keep. Each part has a test that fails today and a written rule for how "current rent" is chosen, so the portfolio, the suggestion and the renewal comparison all read the same number. The technical choices are in the sections that follow.

## Goals

*   **Fix: one stage order.** There is one definition of the stages and of the allowed moves. Every view and the kanban call the same transition function. Illegal moves are refused with a clear message, never a 500.
*   **Fix: valid input.** Rent, dates and deposit go through a Django form. Blank, `1,800`, negative, and end-before-start values give a field error on the page.
*   **Fix: dates are stored.** Every stage reached has a stored date, shown on the detail page.
*   **Fix: a signed lease is the rent.** After signing at a given rent, the portfolio's cash flow and variance use that rent from signing (the monthly series places the row at the lease start date), with no duplicate rows, and signing or editing twice leaves one income row. The test asserts rent, start date and end date. Lease end does not reset rent (LIMIT-14).
*   **Price: suggested rent.** Listing a unit shows a suggested rent with its source, a confidence level, and the date it was fetched. The suggestion is saved at listing time so later checks compare against what was shown.
*   **Price: vacancy cost.** The listing shows the days vacant and the cost so far (lost rent plus carrying costs), computed in the service layer with `Decimal`.
*   **Keep: ending leases.** Leases ending within 90 days are listed, and the investor sees a renew-or-turnover comparison for each (service and pages are built together in the G11 rows; the brief proposed pages later, and the author chose to build them now).
*   **Run it locally.** The app runs from a published GHCR Docker image, with an upgrade path that keeps the user's existing SQLite data.
*   **Stop signals are measurable.** Each signal names a stored field, a threshold, a check date and who decides (see Stop signals).

## Non-Goals

*   **Applicant screening against written criteria (Fill).** No `Applicant` model and no criteria versioning. Deferred until a real lease has run through the app. The single `applicant_name` field stays.
*   **Paid tenant-screening provider (G12).** Dropped. prei stores no SSN, date of birth, credit report or protected-class data.
*   **Hosted deployment with Postgres (G10).** Replaced by the GHCR Docker image. Users run prei locally.
*   **Unit model and unit labels (G8.6).** Deferred. One active listing per property for now.
*   **Seeded leased property (G8.7).** Deferred until after the signed-lease rent rule is built.
*   **Property management.** No rent collection, maintenance, tenant communication, listing syndication, e-signature, or legal advice.
*   **Multi-user design.** Single user, as today. Every new model and query still carries the `user` filter.
*   **Buying a paid rent source now.** A paid source (Rentcast) is considered only after a measurement on real listings shows the free sources are too coarse.

## Open Questions

*   **Stage machine details (resolved):** resume restores the stage the entry was held at; withdraw is terminal. Blocks approval: no.
*   **Duplicate income (resolved):** `property_service.py` counts only the `RentalIncome` row with the latest `effective_date` on or before today, so a manual row and a lease row are never both summed. Blocks approval: no, once row G8.5 carries the change and its test.
*   **Variance baseline (resolved):** variance compares actuals with `previous_monthly_rent_gross` when it is set, so the underwritten pro-forma stays the baseline (`calculate_vacancy_variance` in `portfolio.py`). Blocks approval: no, once row G8.5 carries the change and a test.
*   **G8 size (resolved 2026-11-06):** appetite 14 days from the day the first G8 issue moves to In progress, with a checkpoint on day 7. On overrun cut Price and Keep, never the stage machine, forms, events or lease-to-income. G8 starts after #578 (one test tree) finishes, as `plan.md` requires.
*   **Existing data (resolved 2026-11-06):** no real leasing rows exist, so there is no backfill and no `approximate` flag.
*   **Rent measurement (open):** which 10 or more single-family listings are used, and what is the pass threshold (the doc proposes 15% and leaves it for a human). Rentometer has no key locally, so the chain is HUD FMR only until one is set. Rentcast is not in the rent chain. Fix `RENTCAST_DAILY_BUDGET = 100` against the 50 requests a month free tier before using it. Blocks approval: no (Price ships with HUD FMR at low confidence).
*   **Stop signals (resolved):** see the Stop signals table; each row has a stored field, threshold, check date and decider.
*   **Docs:** `intent.md`, `spec.md`, `plan.md` and `VISION.md` contradict this scope (FR-34, NFR-11, AC-29, Constraint 6, open questions 2 and 3). They are edited in place in separate PRs, without renumbering goals.

## Critical User Journeys (CUJs)

### CUJ 1: Sign a lease and see it in the portfolio

*   **Given**: A property in the leasing pipeline at stage Approved, with `monthly_rent_gross` of 1,650 from underwriting.
*   **When**: The investor enters rent `1,800`, a start date and an end date on the lease form and submits.
*   **Then**: The form accepts `1,800` (or shows a field error for an invalid value, never a 500). The entry moves to Lease Signed with a stored event. `Property.monthly_rent_gross` is 1,800. One `RentalIncome` row linked to the lease exists. Portfolio cash flow uses 1,800. Submitting the same form again leaves one row. Moving the entry backwards or skipping a stage is refused with a message.

### CUJ 2: List a unit at a suggested rent

*   **Given**: A property with no active listing, and rent sources configured.
*   **When**: The investor adds a listing.
*   **Then**: The form shows a suggested rent with source, confidence and fetched date, and the asking rent beside it. If every source fails it shows "no market suggestion" and the pro-forma labelled as the pro-forma. The suggestion is stored on the entry. The detail page shows days vacant and the vacancy cost so far.

### CUJ 3: Decide at the end of a lease

*   **Given**: A lease ending in 60 days.
*   **When**: The investor opens the ending-leases list and enters a proposed renewal rent, a make-ready cost, a leasing cost and expected vacant days.
*   **Then**: The service shows the net result of renewing and of turnover over the next term, and the rent increase at which the two are equal. Renewing updates the end date and rent on the same entry and its income row. Turnover closes the entry and creates a pre-filled listing with `vacant_since` set to the move-out date.

## Technical Plan (Architecture)

### Decisions made by the author

| Question | Decision |
|---|---|
| How the portfolio picks current rent | Signing writes `Property.monthly_rent_gross` (option A), keeps the old value in `previous_monthly_rent_gross`, and a rule keeps income and variance correct (see Open Questions: duplicate income, variance baseline). Reversible: the saved value and an additive schema allow a later move to a single current-rent function (Alternative F) |
| Idempotency of lease to income | Nullable `RentalIncome.lease` link with a unique constraint (option A) |
| Stage dates | `LeasingStageEvent` table (option A) |
| Stage machine | All eight stages, forward one step, required data per stage, plus hold, resume, withdraw (option A) |
| Suggested rent | Fresh-fetch path in the existing rent chain (option A) |
| Vacancy start | Stored `vacant_since`, set by the service when a listing is created (`listed_date`, else today) (option A) |

### Components

*   **Stage machine (`core/services/leasing.py`).** One `transition(entry, to_stage, user, data)` function. It validates the move against `LEASING_STAGE_ORDER` (the only definition of the order) and the required data for the target stage (see Stage table), then in one transaction sets the stage, writes a `LeasingStageEvent` and, for Lease Signed, applies the lease. Illegal moves raise `LeasingTransitionError`. `hold`, `resume` and `withdraw` change `status`, not `stage`. Views, the kanban and the per-stage URLs call only this function; the old `advance_stage`, `mark_filled` and `put_on_hold` are replaced and their callers updated in the same PR.
*   **Applying a lease.** In the same transaction: `update_or_create` a `RentalIncome` row keyed on `lease=entry` with the lease rent, `effective_date` = lease start and `vacancy_rate` copied from the property; save the current `monthly_rent_gross` in `previous_monthly_rent_gross` (only if not already saved); set `Property.monthly_rent_gross` to the lease rent. Withdrawing a signed lease deletes the linked row and restores `previous_monthly_rent_gross` only if `monthly_rent_gross` still equals the lease rent; otherwise it leaves the value and logs a warning.
*   **Forms (`core/forms.py`).** One `LeasingStageForm` (a ModelForm with a field list per stage, see the Stage table) and a `RenewalForm`. The rent field strips thousands separators and rejects blank, zero, negative and non-numeric values; the lease form rejects an end date before the start date. `leasing_add` uses the same form path. Every POST returns a form error or a redirect, never a 5xx.
*   **Models (`core/models/pipeline.py`, `core/models/property.py`).**
    *   New `LeasingStageEvent`: entry, from stage, to stage, date, user, and a nullable `note` (used by renewals).
    *   `LeasingPipelineProperty` gains `vacant_since` (date), `suggested_rent` (Decimal, null), `suggested_rent_source` and `suggested_rent_confidence` (short text), `suggested_rent_fetched_at` (datetime, null), `previous_monthly_rent_gross` (Decimal, null), and a `WITHDRAWN` status. All lease date fields are already `DateField`; no date conversion is needed.
    *   `RentalIncome` gains a nullable `lease` link to `LeasingPipelineProperty` with a unique constraint.
*   **Suggested rent (`core/services/screening.py`).** `_get_monthly_rent` is not changed (two callers in `screening.py` and tests in three files depend on its signature). A new `fresh_market_rent(property)` returns `(rent, source, confidence)` by calling the Rentometer and then the HUD FMR step without the stored estimate and without writing back. Real gaps it closes: the fall-through reason is not returned, and HUD FMR returns `None` without a FIPS code. Property fields are mapped to adapter arguments explicitly. The leasing service stores the result with source, confidence and fetched date. Existing failure paths already log; the new function logs the source name and error too.
*   **Vacancy cost (`core/services/leasing.py`).** `Decimal` function: days since `vacant_since` times monthly rent over 30, plus the property's monthly carrying costs (operating expenses, tax, insurance, HOA) for the same days.
*   **Reuse.** Use `effective_gross_income` (`core/services/underwriting.py`), `OperatingExpense.monthly_amount` (`core/models/property.py`) and `calculate_vacancy_variance` (`core/services/portfolio.py`). Check at implementation: `RentalIncomeForm`, the `Styled*` widgets and the acquisition transitions in `core/models/pipeline.py`.
*   **Keep (`core/services/leasing.py`).** `leases_ending(user, within_days=90)` is a query on `lease_end_date`. `renew_vs_turnover(...)` takes the renewal rent `R_new`, concession, make-ready cost, leasing cost and expected vacant days `V`, over a next term of `T` months. Renew net = `R_new × T − concession`. Turnover net = `R_market × (T − V/30) − make_ready − leasing_cost − carrying_cost_per_day × V`. Break-even `R_new` solves renew net = turnover net. Renewal updates the end date and rent on the same entry and its income row and appends an event whose `note` records the old rent and end date. Turnover closes the entry (status Filled) and creates a new entry with `vacant_since` = move-out date.
*   **Migrations (need approval, `migration-safety` skill).** Additive schema migrations only: the new model, the new fields and the `RentalIncome` link (0057 depends on 0056). There is no data migration. The reverse is the Django default for additive changes; the pre-upgrade SQLite copy is the rollback. Run `makemigrations --check`.
*   **Distribution.** The existing publish workflow pushes the image to GHCR. The container entrypoint already runs migrations on start; the upgrade note tells users to copy their SQLite volume before pulling a new image. Failure modes: the pull fails (check the tag and network), a migration fails on start (restore the copied volume), the tag is unknown (the runbook names the tag).

```text
 lease form ──► LeaseForm (validate) ──► transition(entry, LEASE_SIGNED)
                                              │  one transaction
                     ┌────────────────────────┼─────────────────────────┐
                     ▼                        ▼                         ▼
           LeasingStageEvent       RentalIncome(lease=entry)   Property.monthly_rent_gross
                                              │                (previous value saved)
                                              ▼
                       portfolio cash flow / variance / scoring / projections
```

### Stage table

| Stage | Required data to enter | Next |
|---|---|---|
| LISTING | asking rent | SHOWING |
| SHOWING | none | APPLICATION |
| APPLICATION | `applicant_name`, `application_date` | SCREENING |
| SCREENING | none | APPROVED |
| APPROVED | `screening_passed` true | LEASE_SIGNED |
| LEASE_SIGNED | rent, start date, end date after start | MOVE_IN |
| MOVE_IN | move-in date | STABILIZED |
| STABILIZED | `stabilized_date` | none |

Status is separate: ACTIVE, ON_HOLD (resume returns to the held stage), FILLED (turnover close) and WITHDRAWN (terminal). A kanban drag to a stage that needs data opens that stage's form instead of moving.

### Stop signals

| Signal | Stored field | Threshold | Check | Decider |
|---|---|---|---|---|
| Listing sits without an application | `listed_date`, `application_date` | no `application_date` 30 days after `listed_date` | day 30 of the first real listing | Phil Ruff |
| Signed rent far below suggestion | `suggested_rent`, `suggested_rent_source`, lease rent | signed rent more than 10% below the suggestion, judged only when the source is Rentometer | at signing | Phil Ruff |
| Retyping remains | none (manual check) | any rent or date typed twice after G8 | after G8 ships | Phil Ruff |
| G8 overruns | date the first G8 issue moved to In progress (board) | 14 days; checkpoint on day 7; on overrun cut Price and Keep | day 7 and day 14 | Phil Ruff |

Rentcast is not in the rent chain, so it is not a source for this signal. A single lease is one observation, so these signals prompt a review and do not prove anything. Because HUD FMR sat 10.5% to 28% below the Rentcast median in two ZIPs, a HUD-sourced suggestion is not judged against signed rent.

## Alternatives Considered

Background and earlier reasoning: [the brief](reviews/lease-and-keep-it-leased/concepts_brief.md).

### Alternative A: keep the full G8 to G12 scope

Deferred or replaced: see Non-Goals.

### Alternative B: hosted app instead of a Docker image

Deferred or replaced: see Non-Goals.

### Alternative C: do Price before the Fix

*   **Pros**: The suggested rent needs no migration and helps before closing.
*   **Cons**: The suggestion currently repeats the stored pro-forma rent, and a priced listing still feeds a record that accepts illegal moves and bad input.
*   **Reason for Rejection**: fix the record first, then price. Price is built in this design after the Fix.

### Alternative D: buy a paid rent source now

*   **Pros**: Better rent numbers sooner.
*   **Cons**: The rent-coverage doc compares HUD FMR with Rentcast in only two ZIPs; the free tier is 50 requests a month and `RENTCAST_DAILY_BUDGET` is set to 100.
*   **Reason for Rejection**: For now: measure on 10 or more single-family listings against a threshold first.

### Alternative E: a Unit model and unit labels

Deferred or replaced: see Non-Goals.

### Alternative F: the lease does not change `Property.monthly_rent_gross`

Two variants were weighed: (1) the portfolio picks the latest `RentalIncome` row by date through one function, keeping the pro-forma as a fallback; (2) a new nullable `Property.current_monthly_rent` field read first, with the pro-forma as fallback.

*   **Pros**: The underwriting pro-forma stays intact for variance (actual vs pro-forma).
*   **Cons**: Variant 1 changes three portfolio readers and `property_service.py`, and manual and lease rows compete by date. Variant 2 adds a migration and a value that can go stale when a lease ends.
*   **Reason for Rejection**: writing `monthly_rent_gross` makes every existing reader see the lease with no reader changes. The cost, a lost variance baseline, is handled by keeping the original value in `previous_monthly_rent_gross`.

### Alternative G: other ways to make signing idempotent

(1) `update_or_create` keyed on property and start date; (2) a one-to-one link from the leasing entry to its income row.

*   **Pros**: Variant 1 needs no schema change. Variant 2 touches only the leasing table.
*   **Cons**: Variant 1 creates a second row when the start date is edited and can overwrite a manual row. Variant 2 leaves income rows unaware of leases and dangles if a row is deleted by hand.
*   **Reason for Rejection**: a lease link on `RentalIncome` with a unique constraint.

### Alternative H: plain date fields for stage dates

*   **Pros**: One simple migration; no new table; matches how `PipelineProperty` records `screening_at`.
*   **Cons**: Keeps only the latest date per stage, and records no actor.
*   **Reason for Rejection**: a `LeasingStageEvent` table gives days per stage and an audit trail.

### Alternative I: collapse the stage machine

(1) Three stages: Listed, Lease Signed, Moved In; (2) keep eight stages but enforce data at only three.

*   **Pros**: Variant 1 matches what the portfolio uses today. Variant 2 needs no data migration.
*   **Cons**: Variant 1 remaps existing rows and templates and has to re-add stages when Fill is built. Variant 2 still allows Approved after a failed screening.
*   **Reason for Rejection**: keep all eight stages with required data per stage.

### Alternative J: other sources for the suggested rent

(1) A leasing-specific function calling the adapters directly; (2) show the stored estimate and one market number side by side.

*   **Pros**: Variant 1 leaves the shared chain alone. Variant 2 needs no fresh-fetch change.
*   **Cons**: Variant 1 duplicates the source order. Variant 2 gives two numbers and falls back to the pro-forma echo if the adapters fail.
*   **Reason for Rejection**: one fresh-fetch path in the existing chain.

### Alternative K: other vacancy start dates

(1) The closing or renovation-complete date; (2) `listed_date` only.

*   **Pros**: Variant 1 needs no new field. Variant 2 needs no lookup.
*   **Cons**: Variant 1 fails for properties added by hand and when renovation ends after listing. Variant 2 ignores time before listing and has no turnover start.
*   **Reason for Rejection**: a stored `vacant_since`, defaulting to `listed_date`.

## Non-Functional Requirements

*   **Data safety.** Every schema change is additive. There is no data migration. Run the migrations once against a copy of a populated SQLite file before release. New migrations need human approval (`migration-safety` skill).
*   **No 5xx on leasing (NFR-10).** Every leasing POST returns a form error, a message plus redirect, or a 400 for the kanban's JSON call.
*   **Money.** `Decimal` only; finance math stays in `core/services/`.
*   **User scoping.** Every new query filters by `user`; `LeasingStageEvent` is reached only through an entry the user owns.
*   **Logging.** A failing rent source logs its name and error (AGENTS.md Never Do #10); signing logs the income row id and the previous and new rent.

## Risks

*   **Rollback:** the reverse of an additive migration does not undo data; the SQLite copy taken before an upgrade is the rollback.
*   **Double submit:** `transaction.atomic` plus the unique constraint on `RentalIncome.lease` leave one row after a double click.
*   **Failure UX:** bad input shows a field error; a refused move shows a message; no leasing POST returns a 5xx.

## Future Improvements

*   **Fill:** an `Applicant` model and written screening criteria, once a real lease has run through the app.
*   **Paid rent source:** run the measurement on 10 or more single-family listings; fix `RENTCAST_DAILY_BUDGET = 100` against the 50 requests a month free tier first.
*   **Unit model** for 2 to 4 unit properties.
*   **Ending-leases flag** on the portfolio dashboard and leasing KPIs, once a real lease is about nine months old.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

Work ships as the rows of `plan.md`; each row is one GitHub issue and one PR that closes it. Migrations wait for approval. Start after #578 (one test tree) finishes. Rows marked new are added to `plan.md` through the plan gate; changing the plan is a human decision.

| Work | plan.md row | Issue |
|---|---|---|
| Proof (fails first, marked `xfail(strict=True)` until the fix lands) | G8.1 | [#589](https://github.com/paruff/prei/issues/589) |
| Stage machine, `hold`/`resume`/`withdraw` | G8.2 | [#590](https://github.com/paruff/prei/issues/590) |
| Schema, stage events | G8.3 | [#591](https://github.com/paruff/prei/issues/591) |
| Forms and views | G8.4 | [#592](https://github.com/paruff/prei/issues/592) |
| Lease to income, income-count and variance rules | G8.5 | [#593](https://github.com/paruff/prei/issues/593) |
| Suggested rent | G9.4 | [#599](https://github.com/paruff/prei/issues/599) |
| Vacancy cost | G9.5 | [#600](https://github.com/paruff/prei/issues/600) |
| Ending leases, renew-vs-turnover, actions | G11.2 to G11.4 | see `plan.md` |
| GHCR run and upgrade runbook (docs only) | new row | no issue yet |
| `intent.md`, `spec.md`, `plan.md`, `VISION.md` edits | one PR each, own gate | n/a |

Deferred rows (G8.6 unit label, G8.7 seed) stay in `plan.md` "Later". The file-to-row mapping is in the item list below.

### Target Files to Create/Modify

#### 1. `core/models/pipeline.py` (Modify)

*   **Type / Scope**: Django models.
*   **Proposed Changes**: Add `LeasingStageEvent` (entry FK, `from_stage`, `to_stage`, `occurred_on`, `user`, `note`). Add to `LeasingPipelineProperty`: `vacant_since` (date, null; set by the service), `suggested_rent` (Decimal 10,2, null), `suggested_rent_source` (CharField 32, blank), `suggested_rent_confidence` (CharField 16, blank), `suggested_rent_fetched_at` (DateTime, null), `previous_monthly_rent_gross` (Decimal 10,2, null), and `WITHDRAWN` in `Status`. Keep `Stage` as the only order definition.

#### 2. `core/models/property.py` (Modify)

*   **Type / Scope**: Django model.
*   **Proposed Changes**: `RentalIncome.lease = ForeignKey("core.LeasingPipelineProperty", null=True, blank=True, on_delete=CASCADE, related_name="income_rows")` with `UniqueConstraint(fields=["lease"], condition=Q(lease__isnull=False))`, so deleting an entry removes its income row.

#### 3. `core/models/__init__.py` (Modify)

*   **Type / Scope**: Re-export module.
*   **Proposed Changes**: Export `LeasingStageEvent`, keeping the existing import order.

#### 4. `core/migrations/0056_leasing_stage_events_and_fields.py` (Create)

*   **Type / Scope**: Schema migration.
*   **Proposed Changes**: Create `LeasingStageEvent`; add the new `LeasingPipelineProperty` fields; alter status choices. Additive only.

#### 5. `core/migrations/0057_rentalincome_lease_link.py` (Create)

*   **Type / Scope**: Schema migration.
*   **Proposed Changes**: Add `RentalIncome.lease` and its unique constraint.

#### 6. (removed)

*   No backfill migration: no real leasing rows exist (confirmed 2026-11-06).

#### 7. `core/admin.py` (Modify)

*   **Type / Scope**: Admin registration.
*   **Proposed Changes**: Register `LeasingStageEvent` read-only so events can be inspected.

#### 8. `core/services/leasing.py` (Modify)

*   **Type / Scope**: Service layer.
*   **Proposed Changes**: Keep `LEASING_STAGE_ORDER` as the single order. Add `LeasingTransitionError`, `transition(entry, to_stage, user, data)`, `hold`, `resume`, `withdraw`, replacing `advance_stage`, `mark_filled` and `put_on_hold` (update their callers in the same PR). Add the private `_apply_lease` and `_unapply_lease` used inside the transaction. Add `suggest_rent(entry)` (calls `fresh_market_rent`), `vacancy_cost(entry, as_of)`, `leases_ending(user, within_days)`, `renew_vs_turnover(...)`, `renew_lease(entry, new_rent, new_end)` and `turn_over(entry, move_out)`. All `Decimal`; all filter by user.

#### 9. `core/services/screening.py` (Modify)

*   **Type / Scope**: Service layer.
*   **Proposed Changes**: Add `fresh_market_rent(property)` returning `(rent, source, confidence)`; never write back to a pipeline row. Leave `_get_monthly_rent` and its callers (`screening.py` and the tests in `core/tests/test_screening_hud_usda.py`, `core/tests/test_screening_hud_rent.py`, `tests/e2e/test_rentometer_e2e.py`) unchanged.

#### 10. `core/services/portfolio.py`, `core/services/property_service.py` (Modify)

*   **Type / Scope**: Service layer.
*   **Proposed Changes**: `property_service.py` counts only the `RentalIncome` row with the latest `effective_date` on or before today. `portfolio.py` `calculate_vacancy_variance` uses `previous_monthly_rent_gross` as the baseline when set. Each change has a unit test (manual row plus lease row; variance before and after signing).

#### 11. `core/forms.py` (Modify)

*   **Type / Scope**: Django forms.
*   **Proposed Changes**: Add `LeasingStageForm` (a ModelForm; fields per stage: LISTING `asking_rent`, `listed_date`; APPLICATION `applicant_name`, `application_date`; SCREENING `screening_passed`, `screening_notes`; LEASE_SIGNED `monthly_rent`, `lease_start_date`, `lease_end_date`, `security_deposit`; MOVE_IN `move_in_date`; STABILIZED `stabilized_date`) and `RenewalForm`. A shared rent field strips thousands separators and rejects blank, zero, negative and non-numeric values. The lease form rejects an end date before the start date. `leasing_add` uses the same path.

#### 12. `core/views/leasing.py` (Modify)

*   **Type / Scope**: Views.
*   **Proposed Changes**: Replace the five duplicated stage lists and every direct `stage =` assignment with calls to `transition`. Use the forms above. Kanban move returns 400 JSON for a refused move. Add `leasing_hold`, `leasing_resume`, `leasing_withdraw`, `leasing_ending`, `leasing_renew`, `leasing_turnover`. All views filter by user and return non-5xx for bad input.

#### 13. `core/urls.py` (Modify)

*   **Type / Scope**: URL routes.
*   **Proposed Changes**: Add routes next to the existing `leasing/...` routes:

    | Name | Path | Method | Form | On success |
    |---|---|---|---|---|
    | `leasing_hold` / `leasing_resume` / `leasing_withdraw` | `leasing/<pk>/hold/` etc. | POST | none | detail |
    | `leasing_ending` | `leasing/ending/` | GET | none | list of leases ending |
    | `leasing_renew` | `leasing/<pk>/renew/` | GET, POST | `RenewalForm` | detail |
    | `leasing_turnover` | `leasing/<pk>/turnover/` | POST | none | new listing detail |

#### 14. `templates/leasing/leasing_detail.html`, `leasing_list.html`, `leasing_kanban.html`, `leasing_add.html`, `stage_form.html` (Modify)

*   **Type / Scope**: Templates. Tokens and base components only; no inline `style=`, no hex colours, no Bootstrap (DESIGN.md).
*   **Proposed Changes**: Detail shows the stored event dates and days per stage, the suggested versus asking rent with its source, and days vacant and cost so far. List replaces the "use Portfolio for renewals" banner with the ending-leases link. Forms render field errors. Add and detail show the suggestion.

#### 15. `templates/leasing/leasing_ending.html`, `templates/leasing/leasing_renewal.html` (Create)

*   **Type / Scope**: Templates.
*   **Proposed Changes**: The 90/60/30-day list, and the renew-or-turnover inputs and result. Build in the G11 rows after the service passes its unit tests.

#### 16. `tests/test_leasing_service.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**: Transition table (allowed, backward, skip, hold/resume/withdraw); required data per stage; sign twice leaves one `RentalIncome`; sign then withdraw restores `monthly_rent_gross`; event written with the stage in one transaction; vacancy cost and renew-vs-turnover with `Decimal` cases; user scoping.

#### 17. `tests/test_leasing_forms.py`, `tests/test_leasing_views.py` (Create / Modify)

*   **Type / Scope**: Unit and view tests.
*   **Proposed Changes**: Forms reject blank, `1,800` accepted, negative, bad date, end before start. Every leasing POST returns a non-5xx for those inputs and for out-of-order moves. Update existing tests that set stages directly. Edge cases: zero rent, a lease shorter than a month, end before start, double submit, and `1,800` on `leasing_add`.

#### 18. `tests/test_leasing_migration.py` (Create)

*   **Type / Scope**: Migration test.
*   **Proposed Changes**: Apply 0056 and 0057 to a populated copy of the SQLite file; assert existing rows are unchanged and the detail page renders.

#### 19. `tests/acceptance/test_leasing.py`, `tests_bdd/features/journey.feature`, `tests_bdd/test_journey.py`, `tests_bdd/steps/` (Modify)

*   **Type / Scope**: Acceptance and journey.
*   **Proposed Changes**: Journey signs at 1,800 and asserts the portfolio rent, start and end date, refused backward and skip moves, a field error on a bad rent, stored dates for every stage reached (AC-20 to AC-22). A later step lists at a suggested rent and shows vacancy cost (Price). Renewal and turnover steps are added with the G11 rows.

#### 20. `docs/KNOWN_LIMITATIONS.md` (Modify)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**: Update LIMIT-14 (leasing now connects to the portfolio; renewals exist as a service). Record that the rent changes at signing, not at the lease start date, that a lease end does not reset rent, and the variance baseline rule.

#### 21. `README.md`, `docs/how-to-guides/upgrade-local-image.md` (Modify / Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**: Also correct `render-deploy.md`, which still describes the rejected hosted path. Add the run-from-GHCR steps and an upgrade runbook: copy the SQLite volume, pull the new image, start (migrations run in the entrypoint), and how to restore the copy. `.github/workflows/docker-publish.yml` already pushes to GHCR and is not changed; confirm the tag a user pulls.

#### 22. `core/models/README.md`, `core/services/README.md`, `core/views/README.md`, `core/migrations/README.md` (Modify)

*   **Type / Scope**: EGM directory READMEs (tracked since #632).
*   **Proposed Changes**: Add the new symbols, invariants (one stage order, one income row per lease) and side effects.

#### 23. `intent.md`, `spec.md`, `plan.md`, `VISION.md` (Modify, separate PRs)

*   **Type / Scope**: Planning documents; each is a human-approval gate.
*   **Proposed Changes**: Edit in place without renumbering goals. Add a one-line glossary (Fix = G8, Price = FR-24, 25, 28, Keep = FR-29 to 32, Fill = FR-26, 27). Mark FR-26, 27, FR-33 as deferred and FR-34, NFR-11, AC-29 as dropped, with the date and reason. Narrow G9 to price, promote G11 ahead of Fill, replace G10 with the GHCR image, drop G12, move G9.2, G9.3, G9.6 to "Later" with their issue links, and update the Proof summary, the spec header, the intent open questions 2 and 3, and VISION journey step 9. Issue and milestone status changes on the board are a human step.

### Verification Plan

*   **Compilation/Build**: `make build` (Docker image builds with the new migrations); `python manage.py makemigrations --check`.
*   **Unit Tests**: `.venv/bin/python -m pytest tests/test_leasing_service.py tests/test_leasing_forms.py tests/test_leasing_views.py tests/test_leasing_migration.py`; then the full suite in the background (about 10 minutes).
*   **Static Analysis & Linting**: `pre-commit run --all-files`; `python scripts/check_design.py`; `make ui-check` for the changed templates.
*   **Test Coverage Requirement**: 80% or better on `core/services/leasing.py` and the new forms.
*   **E2E/Integration**: `make docker-accept` (acceptance suite and journey against the container). Run the migrations once against a copy of a populated SQLite file.
*   **Stop signals**: checked as set out in the Technical Plan, after the first real listing.

--------------------------------------------------------------------------------

*Drafted with EGM*
