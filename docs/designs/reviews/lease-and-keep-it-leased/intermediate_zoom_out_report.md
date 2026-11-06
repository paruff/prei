# Stage 8: Intermediate Zoom Out report

Target: docs/designs/lease-and-keep-it-leased.md (full file, unedited since Stage 5). Reviewer: egm-zoom-out, re-ranking against comprehension_report.md and critic_report.md. No code searches were re-run.

**Verdict:** still do not approve. One Blocker remains, and later stages show its mechanism costs more than the design admits.

## 🔴 Blocker

1. **Rent source of truth (lines 41, 62-63, 106, 172-178, 293-296). Unchanged, reinforced.**
   - Signing overwrites `Property.monthly_rent_gross` and also writes a linked `RentalIncome` row. Keeping the two consistent needs: `previous_monthly_rent_gross` saved "only if not already saved" (106); restore on withdraw (wrong if rent was edited in between, empty if never saved, stale on a second entry); a duplicate-income rule that does not exist yet; a variance baseline that is destroyed; and a `property_service.py` change that Alternative F's "no reader changes" rationale denies (296).
   - New (comprehension 4): the overwrite changes rent at signing, not at `lease_start_date`, which contradicts line 41. A future-dated lease lifts cash flow early, and lease end leaves rent at the old value.
   - Alternative F variant 1 is rejected for touching three readers, but option A needs five extra mechanisms and still misses the goal. A single "current rent" function (the lease row in effect on a date, falling back to the pro-forma) removes the save/restore state, the stale-value risk, the variance loss and the start-date contradiction. Decide this before the design is called Decided, and fold Open Questions 2 and 3 into the decision.

## 🟡 Major (new or re-ranked)

2. **Overrun cut contradicts the goals; the event table looks non-core (lines 40, 98, 110, 136).** The overrun cut list (stage machine, forms, lease-to-income) drops `LeasingStageEvent`, but "every stage reached has a stored date" depends on it. Using the existing date fields (`listed_date`, `application_date`, `lease_start_date`, `move_in_date`, `stabilized_date`) in the core removes the contradiction, the `forced` and `approximate` columns and a migration. Settle this first after Blocker 1.
3. **Price rests on an unproven source (lines 66, 112, 138, 163).** Without a Rentometer key most suggestions fall to HUD, which the design says is not judged against signed rent. The fresh-fetch path may hit Rentcast's 50-per-month free tier while the budget constant says 100. Order the measurement ahead of PR 4, or ship a HUD-only suggestion labelled low confidence.
4. **Stop signals, re-ranked from Blocker to Major (lines 46, 67, 129-138).** Line 46 overclaims, but nothing downstream depends on it. Cut the table to what is measurable and drop the "no showings" and "start date in plan.md" rows. On the 10% direction: this reviewer reads line 134 as consistent (HUD makes signed rent look higher, and HUD is excluded at 138), contrary to the Stage 7 style reviewer's suspicion that it is inverted. The real issue is that without a Rentometer or Rentcast source the signal never fires, which is a reason to drop it. (Open point: the concepts brief line 29 should be checked by the author.)
5. **Keep UI is unjustified (lines 44, 88, 114).** "Net result", "next term" and "break-even" have no formula or term; CUJ 3 lists three inputs, line 114 four; "Filled" conflicts with `WITHDRAWN`. Require the formula and a size estimate, or make PR 5 service-only.
6. **Risks, scoped down.** For one user on SQLite, `transaction.atomic` plus the unique constraint covers a double-click; a duplicate stage event is cosmetic. A short risks note is enough: the no-op reverse migration makes the manual SQLite copy the only rollback; what the user sees when all rent sources fail; and Postgres is a non-goal yet still a verification gate (line 220).

## Prior findings, re-ranked

- Context and glossary (prior 3): stays Major; add a decisions-to-alternatives column.
- Backfill and Postgres (prior 5): stays Major; whether a skipped entry still gets an event is unclear.
- GHCR has no PR home (prior 10): stays Major; also has no CUJ or failure modes.
- Rent-chain signature change (prior 9): stays Major; callers are unlisted and the return type changes.
- Data loss on withdraw/cascade (prior 12): folds into Blocker 1.

## 🟢 Nits

- "Rejected by author" with no link, plus prior nit 14: fold A, B and E into Non-Goals; lead each remaining alternative with its trade-off.
- "Fails today" should apply to Fix only; tone items are style.
- Mark which Open Questions block approval.

## Not checked

Call sites of `_get_monthly_rent`, whether non-seed leasing rows exist, and whether a Rentometer key is configured.
