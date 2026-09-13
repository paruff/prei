# Discovery Draft — Investor Workflow Documentation

**Product**: prei
**JTBD**: As a buy-and-hold SFR investor, I want to understand how to use prei's 4-stage workflow (Growth Areas → Discovery → Screening → Underwriting) so I can move from market selection to deal analysis without switching between separate tools.

---

## Riskiest Assumption

**Investors will trust prei's composite scores and screening criteria enough to rely on them for deal decisions.** If the data confidence is too low or the scoring logic feels opaque, investors will default to spreadsheets and manual research, making the entire workflow irrelevant.

---

## Acceptance Criterion

**One measurable acceptance criterion:**

> An investor who has never used prei can complete the full workflow (Growth Areas → Discovery → Screening → Underwriting) by following the documented guides without external help.

**Test type**: live-system — must verify the actual UI, templates, and service behavior match the documentation.

---

## Test-Type Reasoning

| Test type | Why chosen |
|---|---|
| **unit** (file exists) | Structural completeness — ensures all required guide files were created |
| **live-system** (UI verification) | End-to-end user flow — must verify templates, forms, tables, and navigation match what the docs describe |

The primary risk is documentation divergence from implementation. Unit tests can check file existence and section presence, but only live-system tests can verify that the documented UI elements (buttons, tables, chips, forms) actually exist and behave as described. This is why most acceptance criteria are tagged `live-system`.

---

## Related Docs

| Doc | Purpose |
|---|---|
| `specification.md` | Active feature spec (#335) |
| `design.md` | Component design and implementation plan |
| `tasks.json` | Task dependencies and acceptance criteria |
| `docs/product/spec.md` | Numbered functional requirements |
