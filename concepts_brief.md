# Re-scope "lease and keep it leased": fix the lease record first

* **Author:** Phil Ruff
* **Date:** 2026-11-05

## Overview

prei's investor journey works up to closing. Leasing is the missing step. The user plans to buy a property to lease soon, and prei should let them lease it and keep it leased without retyping numbers. Other investors should be able to use it too, by pulling a Docker image from GHCR and running it locally.

This brief proposes narrowing `intent.md` (goals G8 to G12) to three things, in this order:

1. **Fix** the lease record (G8): one stage order, validated input, dated stage changes, and a signed lease that becomes the property's rent in the portfolio.
2. **Price** (part of G9): a suggested rent with its source, and the cost of each vacant day.
3. **Keep** (G11): leases ending soon, and a renew-or-turnover comparison.

Deferred: applicant screening against written criteria (Fill), and hosting (G10, replaced by a published Docker image). Dropped: paid tenant-screening provider (G12).

The repo today matches the "before" state in `intent.md`. No stage-event, applicant, vacancy-cost or renewal code exists. The newest migration is 0055. Leasing code never touches `RentalIncome`. Issues #589 to #595 (G8) are open.

## Analysis

**Blockers**

1. **G8.5 as written will not make the portfolio use the lease.** `core/services/portfolio.py` (around lines 123 and 772) reads `Property.monthly_rent_gross` for cash flow and variance, as do `scoring.py`, `projections.py` and `financing_comparison.py`. Only the monthly series reads `RentalIncome`, and it puts each row in the one month of its `effective_date`. `property_service.py` (lines 38 to 41) sums every `RentalIncome` row on a property, so a lease row plus a manual row doubles income. The plan must first decide how "current rent" is chosen: either the latest row with `effective_date` on or before the month wins (change both readers), or the lease also writes `Property.monthly_rent_gross`. It must also say where `vacancy_rate` is set, once. AC-20 should assert rent, start date and end date, or "no retyping" stays untestable. Not traced: how variance reads `MonthlyActuals`.
2. **Signing twice would create duplicate income rows.** `RentalIncome` has no link to a lease and no unique constraint. Re-posting the form, hold then resume, or re-signing all create rows. Fix: a nullable lease link on `RentalIncome` with a unique constraint, written with `update_or_create` inside a transaction. Editing a signed lease updates that row, and withdrawing voids it. This is a migration the plan doesn't list.
3. **The planning docs contradict the re-scope.** `spec.md` (FR-34, NFR-11, AC-29, Constraint 6), `intent.md` open questions 2 and 3 (resolved 2026-11-02), `VISION.md` journey step 9, and `plan.md` ("one goal at a time, in order", G9 before G11) all assume the old scope. Edit them in place in separate PRs (intent, then spec, then plan). Do not renumber goals; IDs are never reused.
4. **"Price, Fill, Keep" are undefined.** `intent.md` uses them as labels, but spec and plan use only G-numbers. Add one glossary line: Price = FR-24, 25, 28; Fill = FR-26, 27; Keep = FR-29 to 32; G8 is "Fix".
5. **The stop signals cannot be measured as written.** "Sits more than 30 days" has no start point (listing entered, vacancy start, move-out). "No showings" is not a stored field. ">10% from suggestion" needs the suggestion saved at listing time, and the test direction is unstated (signed rent above the suggestion is not a failure). Each signal needs a stored field, a threshold, a check date and a decider.
6. **One lease cannot test the 30-day and 10% signals.** Each is a single observation. HUD FMR sat 10.5% to 28% below the Rentcast ZIP median in `docs/assessments/rent-coverage.md` (2 ZIPs), so if the rent chain falls through to HUD, signed rent will look more than 10% above the suggestion almost every time. That trips on the data source, not on the investor. Store the source with every suggestion, and judge the signal only against Rentometer or Rentcast results. Run a retrospective rent check on 10 or more single-family listings before buying a data plan.

**Major**

7. **The suggested rent mostly echoes your own pro-forma.** `_get_monthly_rent` (`core/services/screening.py`, line 535) returns the stored `PipelineProperty.estimated_rent` before trying any market source. After acquisition that is the number used to buy. A real suggestion needs a "skip the stored value, fetch fresh" path, and the chain takes a `PipelineProperty` while a leasing entry points to `Property`.
8. **Paid rent data: measure first, with a number.** The doc proposes a 15% threshold and leaves it for a human to confirm. `RENTCAST_DAILY_BUDGET = 100` is wrong against a free tier of 50 requests a month; fix or cap it before measuring. Check that a Rentometer key exists. Put the measurement in `plan.md` as a pass/fail row.
9. **G8 is too big for "a few weeks".** Seven rows and three migrations. Suggested core: G8.1 (proof), G8.2 (stage machine), G8.4 (forms), G8.5 (RentalIncome link). Cut G8.6 (unit label) and defer G8.7 (seed) for a single-property buyer. Open disagreement: replace `LeasingStageEvent` (G8.3) with plain date fields (the model already has `listed_date`, `application_date`, `lease_start_date`, `move_in_date`, `stabilized_date`), or keep the events table for days-per-stage and an audit trail.
10. **The stage machine is under-specified.** Required data is written only for Application, Lease Signed and Move-In. `advance_stage` can reach APPROVED from a failed screening. Stage order is duplicated five times (`LEASING_STAGE_ORDER` and four lists in `core/views/leasing.py`). Per-stage views set `stage` directly with no check. `leasing_lease` crashes on a blank rent and on `1,800`, and stores a raw string as `lease_start_date`. Hold, resume and withdraw are not defined (`Status` has no WITHDRAWN).
11. **Existing data and backfill.** Rows already past LEASE_SIGNED have no `RentalIncome` and no stage events. Some may break the new rules, so validation must not 500 the detail page on old data. Keep schema migrations additive, put backfills in a separate data migration, and test on Postgres. G8.2 to G8.7 have no per-row exit criteria.
12. **Vacancy cost needs no new model**, only a pure Decimal service. The missing definition is "vacant since": `listed_date` is not enough.
13. **Keep: build it small.** A lease-end list is a date-sorted query on `lease_end_date`. Renew vs turnover is arithmetic with user-entered make-ready costs. A 12-month lease cannot exercise it on real data in time, so build it as a tested service and defer the UI. Renewal should edit the end date and rent on the same record, not create a "next lease" (that pulls in the deferred Applicant work).
14. **Pre-purchase vs post-closing.** You are about to buy, but the docs write for investors after closing. Only Price helps before closing, and the docs don't say how it differs from the rent chain already used in underwriting.
15. **"Tool others use" vs single-user.** With hosting replaced by a GHCR image, write G8's exit criterion as "a real lease runs through the app". Keep the `user` filter on every leasing query and new model, and avoid multi-user, Unit-model and provider hooks.
16. **Observability.** Store source, confidence, fall-through reason and cache age with each suggestion (today Rentometer and HUD failures are swallowed with `logger.warning`, against AGENTS.md Never Do #10). Log the `RentalIncome` row id on sign. Count Rentcast requests against the free tier.

**Costs of distributing as a Docker image from GHCR**

- Each user needs Docker and a working `.env` (secret key, API keys); the README Quick Start becomes the install guide.
- An image upgrade runs migrations against the user's existing SQLite volume, so G8's migrations touch real user data.
- A local volume has no backup unless documented; G10.4's restore drill becomes a "copy this file" runbook.
- Each user supplies their own Rentcast key, or you carry the cost.

**Not checked by the reviewers:** issues #589 to #595 in full, the leasing templates, `tests/test_leasing_views.py` and `tests/test_pipeline_flow.py`, admin and serializers touching the model, and spec rows FR-24 to FR-32.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  * A trustworthy lease record: one stage order, input errors shown as field errors, a stored date for every stage reached.
  * A signed lease becomes the property's rent in the portfolio and variance, once, with no duplicates and no retyping.
  * A suggested rent with source and confidence, and the cost of each vacant day.
  * Lease-end visibility and a renew-or-turnover comparison.
  * A published GHCR Docker image others can run locally.
* **Out-of-Scope Non-Goals:**
  * Applicant screening against written criteria (Fill) and the Applicant model. Deferred until a real lease runs through the app.
  * Paid tenant-screening provider (G12). Dropped.
  * Hosted deployment with Postgres (G10). Replaced by the GHCR image.
  * Unit model and unit labels (G8.6). Deferred.
  * Property management: rent collection, maintenance, tenant communication, listing syndication, e-sign.

## Alternatives Weighed

* **Keep the full G8 to G12 scope.** Rejected by author: too much for one investor with no tenants yet; hosting and paid screening are not needed to lease the first property.
* **Hosted app instead of a Docker image.** Rejected by author: others can download and run the image from GHCR.
* **Do Price (suggested rent) before the G8 fix.** Open: it needs no migration and helps before closing, but the suggestion currently echoes the stored pro-forma rent, and fixing the record comes first.
* **Replace `LeasingStageEvent` with plain date fields.** Open: one migration instead of a new table, but no days-per-stage or audit trail.
* **Buy a paid rent source now.** Rejected for now: measure against 10 or more listings first, with a 15% threshold the author must confirm.

## Key Decisions & Staging for Next Steps

Decisions made:
* Order: Fix (G8), then Price, then Keep. Fill, hosting and paid screening are out of this scope.
* Single user is acceptable. Distribution is a GHCR Docker image.
* Applicant screening is a nice future item. Paid provider screening is unlikely.
* A paid rent source is wanted only if measurement shows the free chain is too coarse.

To decide before drafting:
* How "current rent" is chosen in the portfolio (latest row wins, or write `Property.monthly_rent_gross`), and where `vacancy_rate` is set.
* The idempotency key for lease-to-`RentalIncome`.
* Events table or plain date fields for stage dates.
* Which G8 rows to cut, and the start date and overrun rule for the time box.
* For each stop signal: stored field, threshold, check date and decider.

Staging: edit `intent.md`, then `spec.md`, then `plan.md` in place as separate PRs, without renumbering goals. Move G9.2, G9.3 and G9.6 to "Later" with their issue links, mark FR-26/27 and FR-33 deferred and FR-34 dropped, and add the glossary line. Issue and milestone status changes on the board are a human step.
