# plan-for-the-day.md (today) — prei

**Horizon**: Today | **Owner**: Dev lead (Phil) | **Review**: End of session

---

## Single Primary Goal

Complete the investor workflow documentation for issue #335: create all 4 how-to guides, the workflow overview, and UI patterns reference.

---

## Target Issues

| Issue | Title | Priority | Status |
|---|---|---|---|
| #335 | Comprehensive Documentation Review & Revision | P1 | In progress |

### Tasks for today

1. **Create workflow overview** — `docs/explanation/investor-workflow.md` (TASK-001)
2. **Create Growth Areas how-to** — `docs/how-to-guides/analyze-growth-areas.md` (TASK-003)
3. **Create Discovery how-to** — `docs/how-to-guides/discover-properties.md` (TASK-004)
4. **Create Screening how-to** — `docs/how-to-guides/screen-properties.md` (TASK-005)
5. **Create Underwriting how-to** — `docs/how-to-guides/underwrite-deals.md` (TASK-006)
6. **Create UI Patterns reference** — `docs/reference/ui-patterns.md` (TASK-007)

---

## TDD Execution Protocol

For each task:

1. **Red** — Write a failing test that checks the doc file exists and contains expected sections
2. **Green** — Create the doc file with the required content
3. **Refactor** — Review against `design.md`, fix cross-references, ensure accuracy

### Test checklist (per doc)

- [ ] File exists at expected path
- [ ] Contains required sections per `design.md`
- [ ] All cross-references resolve
- [ ] No broken links
- [ ] Tone is investor-appropriate (not developer-focused)
- [ ] Data confidence/warnings included where relevant

---

## Retrospective

### What went well
- All 6 doc files already existed and matched design.md — no content gaps found
- 85 TDD tests written and passing: investor-workflow, analyze-growth-areas, discover-properties, screen-properties, underwrite-deals, ui-patterns, plus all planning cascade docs
- Cross-references between guides are consistent and resolve correctly

### What could improve
- Test initially failed on case-sensitive "HOA" vs "hoa" — always compare lowercase to lowercase
- Could add live-system verification tests (UI element matching) in a future session

### Backlog deltas
- New items discovered: live-system verification tests (templates vs docs accuracy)
- Items to move to P2: N/A
- Items to reject (scope drift): N/A

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `EXECUTION_QUEUE.md` | What are the weekly priorities? | ↗ links up |
| `VISION.md` | Why are we building this? | ↗ links up |
| `tasks.json` | What are the detailed task dependencies? | parallel |
