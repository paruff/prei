# Resolution: lease-and-keep-it-leased

Findings from [consolidated_review_report.md](consolidated_review_report.md), resolved on 2026-11-06 with `egm-resolve` (annotated report kept in scratch). The human decided each row.

| # | Finding | Decision | Reason |
|---|---|---|---|
| B1 | Where current rent lives | Accepted: Option A with rules | Income counts the latest row by date; variance uses `previous_monthly_rent_gross`; withdraw restores only if rent is unchanged. A two-way door: additive schema, old value saved, no real data. |
| B2 | Text-to-date conversion | Accepted | All lease date fields are already `DateField`; the bug is unvalidated POST text. |
| B3 | `_get_monthly_rent` change | Accepted | New `fresh_market_rent`; existing function and its callers unchanged. |
| B4 | Stop signals | Accepted, appetite 14 days | Signals use stored fields; the 10% rule is judged on Rentometer only. |
| B5 | Backfill | Accepted: dropped | No real leasing rows exist (confirmed by Phil Ruff). |
| Majors | Event table, Keep formulas, Price failure UX, reuse, forms, rollback, GHCR PR, Risks, model specs, stage table, routes, plan rows, glossary, code-claim citations, lease-date semantics | Accepted (auto accept) | Applied to the design. |
| Conflict | 10% rule direction | Contested | The design and the brief agree: only signed rent below the suggestion is flagged. |
| Contest | README contracts untracked; planning edits bundled | Contested | READMEs are tracked since #632; planning edits are already separate PRs. Only the stale wording in item 22 was fixed. |
| Nits | Tone, ordering, footer, admin note, `__init__` | Declined | Nits; two folded into other fixes. |
