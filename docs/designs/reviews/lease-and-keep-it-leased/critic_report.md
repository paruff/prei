# Stage 7: Critic Review report

Target: docs/designs/lease-and-keep-it-leased.md, lines 1-234. Reviewers: egm-design, egm-structural, egm-style (all completed). Findings are deduplicated; the source reviewer is in brackets (D design, S structural, T style).

No Blockers from this stage. Stage 5 raised two Blockers (rent source of truth; stop signals) that this stage's findings reinforce.

## 🟡 Major

1. **Alternatives rejected "by author" with no link or technical trade-off (lines 146-216).** [D, S] Every Reason for Rejection starts "Rejected by author:" with no linked issue, discussion or PR, which the standard forbids. A and B are weakest ("too much scope"; "others can pull the image" does not say why hosting loses). Lead with the Cons as the trade-off, link the decision record, and drop the repeated prefix (T nit 13).
2. **Rent baseline and variance (lines 41, 62-63, 106, 178).** [D, T] Overwriting `monthly_rent_gross` makes actual-vs-pro-forma compare the lease with itself. `previous_monthly_rent_gross` has no named reader. The design is "Decided" while this is open. Style adds that the concepts brief says "not traced: how variance reads `MonthlyActuals`" and the design drops that caveat. Decide it, or state that variance is meaningless after signing.
3. **Duplicate income rows (lines 30, 41, 62, 106, 177).** [D] Idempotency covers lease rows only; a lease row plus an earlier manual row still doubles income. Pick a rule (lease supersedes manual rows from its start date, or change the readers) and add it to Components and the CUJ 1 assertions.
4. **Rollback and data loss (lines 106, 114, 115).** [D] Withdraw restores `previous_monthly_rent_gross`, which is wrong if the rent was edited in between, and is empty if never saved. Renewal edits the same entry and income row, losing original lease terms. The backfill reverse is a no-op and leaves converted columns and rows. State the edited-in-between behavior and whether date conversion is reversible.
5. **Missing Risks and Mitigations section (whole document; lines 107, 112, 116, 220-224).** [S, D] Risks are scattered. Not covered: concurrency/double-click on `transition` (no row lock; the unique constraint stops a duplicate row but not a duplicate event), SQLite versus Postgres as the target engine, the manual SQLite copy before upgrade with no rollback for a no-op-reverse migration, Rentcast quota, and what the user sees when all rent sources fail (blank, or the pro-forma echo line 32 calls a trap).
6. **Stop signals are inconsistent (lines 46, 67, 129-138).** [D, S, T] Goal line 46 says every signal names a field, threshold, check date and decider, which is false for at least three rows ("Showing event" not stored, "none" for retyping, "start date in plan.md" not a date). Line 67 still lists defects the table appears to resolve; the Goal points at Open Questions instead of the table. The 10% direction also appears inverted against the concepts brief (line 29: HUD would make signed rent look more than 10% *above* the suggestion); confirm the direction. State n=2 for the HUD comparison.
7. **Suggested-rent source unproven (lines 66, 112, 138, 163, 229).** [D] If no Rentometer key exists, nearly every suggestion is a HUD number the design says not to judge. The Rentcast budget conflict (100 vs 50 per month) is deferred but the fresh-fetch path may call Rentcast now. Add a quota safeguard or restrict the sources.
8. **Keep scope contradicts the brief and is unsized (lines 44, 114, 231, 64).** [D, T] The brief advised a tested service with UI deferred; the design builds pages "because the author chose". Add a reason or an estimate. The G8 time box and start date are unresolved, so the overrun rule has no baseline.
9. **Overrun cut contradicts a goal (lines 40, 110, 136).** [D] The cut keeps "stage machine, forms, lease-to-income" and so drops `LeasingStageEvent`, but the goal "every stage reached has a stored date" depends on it. Migration scope (new model, seven fields, status, FK, data migration) is not sized.
10. **"Option A" labels do not map to Alternatives A-K (lines 94-101, 142-216).** [D, S, T] Add a column linking each decision row to its alternative (rent to F, idempotency to G, and so on).
11. **Undefined terms and unlinked references (lines 11, 19, 41, 44, 46, 61-68, 163).** [S, T] G8-G12, Fill, G8.6/8.7, FR/NFR/AC IDs, "the brief", "PR 5", "the rent-coverage doc" and the planning docs have no links or definitions. Convert to relative links; add a glossary in this doc.
12. **Code claims need calibrating (lines 30, 32, 63, 112).** [T] Exact line numbers will drift; cite function names or the commit checked. Carry over the "not traced" caveat at line 63.
13. **Line 34 promises tests that fail today for Price and Keep.** [T] Those are new features. Restrict "fails today" to Fix and cut the filler "The technical choices are in the sections that follow."
14. **Line 30 evaluative framing.** [T] "Harder than the plan assumes" and "a similar trap" are judgments; state the finding directly.
15. **Goal line 44 carries history.** [T, D, S] The parenthetical about the brief and author belongs in a Decisions row or Alternatives.

## 🟢 Nits

16. Open Questions are not marked as blocking approval or not (variance baseline, duplicate rows, backfill block). [D]
17. Intent/spec/plan still conflict with this scope until PRs 6 to 8 land; link those PRs. [D]
18. "Future Improvements" (line 226) is an H3 under Non-Functional Requirements; promote to H2. [S]
19. Open Questions precede the CUJs and plan; consider moving them later. [S]
20. The GHCR goal has no CUJ, data flow or failure modes. [S]
21. Alternatives F-K put variants (1)/(2) in prose; split into F1/F2 sub-bullets. [S]
22. Line 11 narrative ("the last step, is the weak one"); line 26 "never stored" wording; line 38 "clear message"; line 106 "(one source)"; "never a 5xx" repeated at 38, 76, 221; line 158 repeats the Overview; line 138 "prove anything" wording; "paid rent source" used inconsistently (57, 163, 229). [T]
