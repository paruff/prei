# Consolidated review: docs/designs/lease-and-keep-it-leased.md

Mode: consolidated report, all five stages, no edits made to the design. Context given to reviewers: concepts_brief.md, intent.md.
Stage reports: zoom_out_report.md (5), comprehension_report.md (6), critic_report.md (7), intermediate_zoom_out_report.md (8), implementation_readiness_report.md (9).
All requested reviewers completed. Code claims were checked by one reviewer in Stage 9 only (egm-codebase-details); Stage 5 ran limited code searches.

**Verdict: not ready to approve or implement.** The Fix, Price, Keep order and the diagnosis of the problem hold up. Three things block progress: one unresolved mechanism (where "current rent" lives), two plan claims that the code contradicts, and a plan that leaves decisions to the implementer.

## 🔴 Blockers (resolve before approval)

| # | Action | Where | Source |
|---|---|---|---|
| B1 | **Decide where current rent lives.** Signing writes both `Property.monthly_rent_gross` and a `RentalIncome` row. This needs save/restore state, a duplicate-income rule and a variance fix, and it still changes rent at signing rather than at `lease_start_date`. The zoom-out reviewer suggests a single "current rent" function (lease row in effect on a date, falling back to the pro-forma). Fold Open Questions 2 and 3 into the decision, then mark `property_service.py` and `portfolio.py` Modify or Skip with the exact change. | 41, 62-63, 106, 172-178, 293-296 | S5-1, S7-2/3/4, S8-1, S9-1 |
| B2 | **Remove the text-to-date conversion.** All six lease date fields are already `DateField` (`core/models/pipeline.py` 773-802). The real bug is unvalidated POST text. Reword the Problem section, drop the `AlterField` and the backfill's date conversion. | 26, 110, 220, 251, 266, 276 | S9-2 |
| B3 | **Respecify the `_get_monthly_rent` change.** It already has `cache_rent`; changing the return type breaks callers in `screening.py` (415, 475) and at least three test files; `beds` vs `bedrooms` mapping missing; the "silent except" sites already log warnings. Choose a wrapper or new entry point, list callers, and state the real gap (fall-through reason not returned, `hud_fmr_rent` returns `None` with no FIPS). | 112, 288-291 | S9-3/4, S5-9 |
| B4 | **Make the stop signals measurable, or cut them.** Goal line 46 is false for at least three rows ("Showing event" not stored, "none", "start date in plan.md"). Rentcast is not in the rent chain, so the 10% signal can only fire on Rentometer, and may never fire without a key. Direction of the 10% rule: reviewers disagreed; check concepts_brief.md line 29. | 46, 67, 129-138 | S5-2, S7-6, S8-4, S9-7 |
| B5 | **Define the backfill rules, or drop the backfill.** First confirm whether any non-seed leasing rows exist (nobody checked). If they do: rent field, bad-value rule, writes to `Property`, event field values, `vacancy_rate` source, detail-page fallback. If not, drop the backfill, the `approximate` column and the Postgres gate. | 115, 276 | S5-5, S6-7, S9-5 |

## 🟡 Major

**Scope and design**
- Event table vs existing date fields: the overrun cut drops `LeasingStageEvent` yet the goal "every stage reached has a stored date" needs it; `forced` and `approximate` are undefined or backfill-only. Use the existing date fields in the core. (40, 98, 110, 136; S5-6, S7-9, S8-2)
- Keep UI built before it can be exercised, with no formula or term for "net" or "break-even", and CUJ 3 vs line 114 input counts differ. Require the formula and a size estimate or make PR 5 service-only. (44, 88, 114; S5-4, S7-8, S8-5, S9-10)
- Price rests on an unproven source: no Rentometer key means HUD only; Rentcast quota 100 vs 50; no all-sources-fail UX. (66, 112, 138, 163; S7-7, S8-3)
- Reuse not examined: acquisition `pipeline.py` transitions, `RentalIncomeForm`, `Styled*` widgets, `OperatingExpense.monthly_amount()`, `effective_gross_income`, `calculate_vacancy_variance`. (S5-7, S9)
- Eight forms where fewer are needed; field specs missing; `leasing_add` has the same unguarded `Decimal` 500 bug. (298-301; S5-8, S9-12)
- Rollback and data loss: withdraw restore is wrong if rent was edited or never saved; renewal overwrites lease terms; no-op reverse migration. (106, 114, 115; S7-4)
- Risks section missing: no-op reverse makes the SQLite copy the only rollback; Postgres is a non-goal but a gate; failure UX. Scope it small (`transaction.atomic` plus the unique constraint covers a double-click). (S7-5, S8-6)
- GHCR goal has no PR, CUJ or failure modes. (45, 116, 239-244, 348-351; S5-10)

**Plan completeness (Stage 9)**
- Model and migration specs: types, defaults, `vacant_since` default cannot reference `listed_date`, `RentalIncome.lease` shape and string reference, migration dependencies, `makemigrations --check`.
- Stage table and service signatures; `forced`; hold/resume change `status`, not `stage`; STABILIZED vs FILLED; kanban cannot carry required data; unnecessary `advance_stage` wrapper.
- Vacancy cost and renew-vs-turnover formulas.
- Route and view table; template specifics; test assertions and edge cases; file-to-PR table (PR 1 tests must be `xfail`; PR 3 too big).
- README contracts are untracked files; docs items lack content and owners; planning-doc edits bundled.

**Document quality**
- Undefined terms (G8-G12, Fill, FR/AC IDs, "option A", "the brief", PR 5) and unlinked references. Add a glossary and a decisions-to-alternatives column. (S5-3, S6-1/2, S7-10/11)
- Every alternative says "Rejected by author" with no link; lead with the trade-off; fold A, B, E into Non-Goals. (140-216; S7-1)
- Code claims by line number drift; cite functions and carry the brief's "variance not traced" caveat. (30, 32, 63; S7-12)
- Lease start/end semantics: rent changes at signing, not start date; lease end leaves rent unchanged. (41, 76, 106; S6-4)

## 🟢 Nits

Mark which Open Questions block approval; promote "Future Improvements" to H2; move Open Questions later; split F-K variants; tone items (line 11, 26, 34, 38, 106, 158); drop `core/models/__init__.py` (item 3); admin note; add acceptance and BDD tests to per-PR checks; drop stale line counts; "Drafted with EGM" footer; `render-deploy.md` still describes the rejected hosted path.

## Conflicts between reviewers

- **10% rule direction:** the Stage 7 style reviewer suspects it is inverted against concepts_brief.md; the Stage 8 zoom-out reviewer reads it as consistent. Unresolved; the author should check the brief.
- **Stop signals severity:** Blocker in Stage 5, Major in Stage 8. Listed as B4 here because the Rentcast finding (S9-7) makes the 10% signal unfireable.
- **Postgres:** Stage 5 and 8 say drop the gate; Stage 7 wants the engine stated. Both agree it must not remain an unexplained gate.

## Traceability

| Stage report | Findings | Consolidated into |
|---|---|---|
| zoom_out_report.md | 14 | B1, B3, B4, B5; Major scope, reuse, forms, GHCR, glossary |
| comprehension_report.md | 17 | B4, B5; Major glossary, lease dates, renew formula |
| critic_report.md | 22 | B1, B4; Major rollback, risks, alternatives, references |
| intermediate_zoom_out_report.md | 6 plus re-ranks | B1, B4; Major event table, Price, Keep |
| implementation_readiness_report.md | 5 Blockers, 15 Majors, nits | B1, B2, B3, B4, B5; Major plan completeness |

## Suggested order of work

1. Decide B1 (current-rent mechanism) and the event-table question. These change most of the plan.
2. Check the facts nobody checked: non-seed leasing rows, `_get_monthly_rent` callers, Rentometer key, 10% direction.
3. Fix B2 and B3 against the code.
4. Cut or fix the stop signals; scope Keep and Price.
5. Add the glossary, links, risks note, file-to-PR table, signatures and formulas.

Nothing was edited. Next step is the author's call: edit the design, or run `/egm:egm-resolve` on the ranges to work through findings.
