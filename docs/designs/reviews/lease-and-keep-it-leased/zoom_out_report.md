# Stage 5: Zoom Out report

Target: docs/designs/lease-and-keep-it-leased.md (full file). Reviewer: egm-zoom-out.
Verdict: do not approve yet. The Fix, Price, Keep order is sound and the root problem is well diagnosed. The central mechanism is unresolved, and the plan has drifted into detail and unneeded scope.

## 🔴 Blockers

1. **Rent source of truth is contradictory (lines 41, 62-63, 76, 106, 172-178, 293-296).**
   - Signing writes `Property.monthly_rent_gross` (decision A) and also creates `RentalIncome(lease=entry)`. That is two stores of the same rent.
   - Alternative F (line 178) rejects other options because "no reader changes" are needed, but item 10 (line 296) says `property_service.py` must change because it sums every `RentalIncome` row.
   - The goal and CUJ 1 promise "no duplicate rows", "cash flow uses 1,800" and a variance result. These depend on Open Questions 2 and 3, still open.
   - Overwriting `monthly_rent_gross` destroys the underwriting baseline the variance feature uses.
   - Decide one: (a) `RentalIncome` is the source and one "current rent" function serves all readers, or (b) the Property field is the source and no `RentalIncome` link, unique constraint or migration is added.

2. **Stop signals contradict themselves (lines 67, 133, 136, 138).**
   - "No Showing event" is used as a signal, but line 67 says showings are not stored and no PR adds them.
   - "G8 overruns" cites a start date in `plan.md` that does not exist yet.
   - Four formal signals with a named decider is heavy for one user with zero tenants (line 138 admits one lease proves nothing).
   - Add the showing field or drop that signal. Cut the table to what is measurable.

## 🟡 Majors

3. **Context for a fresh reader (lines 11-19, 34, 94-101, 341, 361).** Undefined terms: G8-G12, Fill/Price/Keep, "option A" (options not listed), AC-20 to AC-22, FR-24, `plan.md` #578. The glossary is deferred to PR 8. Add a short glossary and a one-line statement of each option.
4. **Keep is built before it can be exercised (lines 44, 231).** The brief says a 12-month lease cannot exercise renew-vs-turnover on real data, so keep it a tested service and defer the UI. The design adds two templates, three views, three routes, and `renew_lease`/`turn_over`, which change state against a guessed workflow. Keep PR 5 to the service and tests.
5. **Backfill built for data that may not exist (lines 115, 220, 276, 333-336, 369).** Backfill migration, `approximate` flag, migration test, and Postgres runs, when there may be no non-seed leasing rows. Postgres is a non-goal (line 52) yet is a verification gate. Confirm whether such rows exist; if not, drop the backfill, the `approximate` column and the Postgres gate.
6. **`LeasingStageEvent` is heavier than needed (lines 98, 109, 192, 251).** The audit trail and days-per-stage are not current goals. `forced` is never defined (`transition` has no force path). `approximate` exists only for the backfill. Alternative: use existing date fields (`listed_date`, `application_date`, `lease_start_date`, `move_in_date`, `stabilized_date`). Author to confirm the table is wanted now.
7. **Reuse not examined (lines 105-114, 299-301).** Existing: `advance_stage` in `core/services/leasing.py:24` and `core/services/pipeline.py:63`, `LEASING_STAGE_ORDER` at `leasing.py:12`, `RentalIncomeForm` at `core/forms.py:189`, `effective_gross_income` at `underwriting.py:57`, `calculate_vacancy_variance` at `portfolio.py:478`. The design does not say whether these are reused, or why not.
8. **Eight forms where three are needed (line 301).** Required data is specified for Application, Lease Signed and Move-In only. Build `LeaseForm` and the shared rent field first, and a form per stage only where data is required.
9. **Rent-chain signature change spreads (lines 112, 291).** `_get_monthly_rent` gains `skip_stored`, accepts a "Property-shaped object" and returns source and confidence. This changes the return type for every existing caller, so "today's behavior by default" cannot hold. Use a wrapper or a separate entry point and grep the callers.
10. **GHCR/Docker work has no home in the plan (lines 45, 116, 239-244, 348-351).** It is a stated goal but absent from the PR order and hidden in a catch-all row. Give it a PR or move it out.

## 🟢 Nits

11. **Altitude drops (lines 246-361).** Private helper names, migration filenames, current line counts, full field lists and test-case enumerations belong in PRs.
12. **Data loss and duplicate sources (lines 106, 256).** "Withdraw deletes the linked row", cascade delete of income, and "vacancy_rate copied from the property (one source)" contradict each other. State intent, or read vacancy rate from `Property` at the point of use.
13. **Scope and structure (lines 11-13, 59-68, 94-101).** "Three pieces of work" ignores the Docker goal and the four doc PRs. The decisions table sits beside open questions that undermine several decisions. Resolve the questions before listing decisions as final.
14. **Alternatives A-K read as a log (lines 140-216).** A, B and E are scope cuts already in Non-Goals. Fold them in.

## Not checked

Whether any non-seed `LeasingPipelineProperty` rows exist, and the current call sites of `_get_monthly_rent`.
