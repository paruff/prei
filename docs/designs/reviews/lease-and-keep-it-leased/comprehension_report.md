# Stage 6: Comprehension Test report

Target: docs/designs/lease-and-keep-it-leased.md. Reviewer: egm-comprehension, reading the document alone.

## What this proposes

The document proposes a three-step change to prei's leasing flow, in the order Fix, Price, Keep. Fix: put the leasing pipeline behind one stage machine (a single `transition()` function plus validated Django forms). Signing a lease then writes a `RentalIncome` row linked to the lease, and overwrites `Property.monthly_rent_gross` with the lease rent, so the portfolio picks it up with no retyping. Price: at listing time, fetch a suggested rent with its source, confidence and date, skipping the stored pro-forma estimate. Show days vacant and the cost so far. Keep: list leases ending within 90 days and compute a renew-vs-turnover comparison with a break-even rent. Applicant screening, hosting, paid tenant screening and a Unit model are deferred or dropped. Other investors run prei locally from a GHCR Docker image. The work ships as PRs 1 to 8 (tests, schema, stage machine, Price, Keep, then four docs PRs).

## How the existing system works, per this document

Leasing is a pipeline of eight stages. Any stage can be set from any other, backwards or forward, through per-stage URLs and the kanban, and the stage order is repeated in five places. Rent and dates are not validated. A blank rent or `1,800` causes a 500 error, the start date is stored as a raw string, and the detail page shows stage dates that were never stored. The leasing code never touches `RentalIncome`. The portfolio reads `Property.monthly_rent_gross` for cash flow, and only the monthly series reads `RentalIncome`, placing each row in the month of its `effective_date`. `property_service.py` sums all `RentalIncome` rows on a property. `_get_monthly_rent` returns the stored `PipelineProperty.estimated_rent` before trying any market source, so after purchase a "suggestion" would only echo the pro-forma. Nothing covers rent suggestion, vacancy cost or renewals.

## Findings

### 🔴 Blocker
- None. Every section could be paraphrased.

### 🟡 Major
1. **Lines 11, 19, 46, 64, 237, 361: undefined project documents and IDs.** `intent.md`, `plan.md`, `spec.md`, `VISION.md`, G7 (#578), G8 to G12, G8.6/G8.7, G9.2/9.3/9.6, FR-24 to FR-34, NFR-10/11, AC-20 to AC-29, Constraint 6, LIMIT-14 and "the brief" are used with no links or definitions. The glossary at line 361 is only a future edit. A fresh reader cannot check the scope narrowing (lines 19, 50-54).
2. **Lines 13-17 vs 140-216: Fill and the eight stages are never defined.** "Fill" first appears at line 50. The stage list, forward order, required data per stage, and the meaning of hold, resume and withdraw are never written down, so the transition rules and test table (line 326) cannot be checked.
3. **Lines 61-63, 105-106, 115: design depends on unresolved questions.** Duplicate income rows and the variance baseline are open (62, 63), yet "One RentalIncome row", "no duplicate rows" and restore-on-withdraw are stated as settled. Line 30 says a manual row next to a lease row doubles income and no decision is recorded; line 296 defers the fix. The goal at line 41 cannot be met when a manual row exists. Say what happens in the interim.
4. **Lines 41, 76, 106: lease dates in cash flow are unexplained.** The goal says the lease rent applies "from the lease start date", but overwriting `monthly_rent_gross` changes rent at signing, not at start. Future-dated start and lease end (rent stays at the old value) are not handled.
5. **Lines 44, 88, 114: renew/turnover under-specified.** "Net result over the next term" and "break-even rent increase" have no formula, term length or definition of "net". CUJ 3 lists three inputs, line 114 four. "Turnover closes the entry (status Filled)" conflicts with the new `WITHDRAWN` status and `mark_filled`; "Filled" is not defined.
6. **Lines 130-136: stop signals incomplete or contradictory.** "Showing events" are used, but line 67 says showings are not stored and no model exists. "The first real listing" has no date; line 67 says the 30-day signal needs a start point. The table does not say which of these it resolves.
7. **Lines 115, 276 vs 220: backfill inconsistent.** Line 115 writes one event per entry; line 276 limits it to entries with a rent and parseable start date, then skips failures. It is unclear whether a skipped entry still gets an event. Line 220 requires a Postgres run though Postgres is described only as the dropped hosted option (52, 151).

### 🟢 Nit
8. **Line 11:** expand GHCR once (GitHub Container Registry).
9. **Lines 57, 66, 163, 229:** Rentcast, Rentometer, HUD FMR and "the rent chain" are named but not described; the rent-coverage doc (line 163) is not linked.
10. **Lines 63, 106, 110:** `previous_monthly_rent_gross` lives on the entry but is restored onto `Property` on withdraw. Signing on a second entry later, with "only if not already saved", would keep a stale value. State the scope.
11. **Lines 98-99:** "option A" labels refer to options not shown; Alternatives A to K use a different scheme.
12. **Lines 112 vs 291:** "accepts a `Property`" vs "Property-shaped object"; returning source and confidence changes the return type for existing callers, which are not listed.
13. **Lines 101, 110, 251:** "other date fields that hold text" are not named (only `lease_start_date`). A Django field default cannot reference another field, so say whether `vacant_since` defaults in code or in the migration.
14. **Line 256:** `on_delete` value (CASCADE) is not named, and cascade is not needed for "withdraw deletes the linked row".
15. **Lines 263-273:** migration numbers 0056 to 0058 are provisional; say so.
16. **Lines 296, 315-316, 355:** references to `DESIGN.md`, `AGENTS.md Never Do #10` and "EGM contracts written earlier in this session" have no links; the last will not make sense later.
17. **Lines 237, 244:** "fails first" and "its own gate" are not explained, nor how failing PR 1 tests avoid breaking CI.
