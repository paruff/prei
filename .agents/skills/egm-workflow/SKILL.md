# EGM Workflow Skill — prei

## When to load
- Before changing `intent.md`, `spec.md`, `plan.md` or a `docs/designs/` doc.
- Before a doc-vs-code drift check.
- Not for: small clear bug fixes, code-only PRs (use `REVIEW.md`), UI tweaks.

## Roles
Elephant = you: deep context, drafts. Goldfish = fresh zero-context reviewers: judge only the
document and what it references. Human = decides. A Goldfish review never replaces a gate.

## Harness
Goldfish review runs in Claude Code only (plugin `egm@egm`). EGM skills cannot be called through the
`Skill` tool: ask the user to type `/egm:egm-review <abs path>` or `/egm:egm-review-loop`, or read the
skill's `SKILL.md` and follow it in this thread. Elsewhere (OpenCode, Copilot): stop and say review
cannot run. Never simulate Goldfish reviewers in your own context.

## Steps for a spec, plan or design PR
1. Move the issue to **In progress** (AGENTS.md "Workflow").
2. Load the `prei-elephant` skill. Draft the change. Design needed? See "Design" below.
3. Run the Goldfish review before opening the PR: `egm-review` for a design, `egm-review-loop` for
   spec/plan. Pass `intent.md` and any concepts brief as context.
4. Run `egm-resolve`. Write `docs/designs/reviews/<slug>/resolution.md`: each finding accepted or
   rejected, with a reason. The human decides; do not decide for them.
5. Commit `consolidated_review_report.md` beside it. Stage reports stay in `.dev/egm/`.
6. Open the PR (`docs/PR_STANDARD.md`). Post one PR comment: top findings, link to the report.
7. Move to **Needs human decision**, Gate `spec` or `plan`. The human merges.

## Design (optional step between spec and plan)
Only if the work adds a model/migration, a cross-service mechanism, or the spec leaves an open "how".
Brainstorm if needed (`egm-brainstorm`), then `egm-draft`. Output `docs/designs/<slug>.md`, added to
`docs/designs/SITEMAP.md`. Approved by merging, under Gate `plan`. Never call it DESIGN.md (UI).

## Findings and severity
Goldfish gives a lot by design: take what matters, ignore the rest. In `REVIEW.md` terms a blocker, or
a major with a concrete failure, is **Important**; everything else is **Minor**.

## Drift
At each goal's close: `/egm:egm-drift-report docs/designs`. The report stays in `.dev/egm/`. Each real
divergence becomes a board issue (`.github/ISSUE_TEMPLATE/work.md`, Plan row `n/a: drift`); the human
picks doc or code. This is not `scripts/drift-check.sh` (deployment drift).

## Rules
- Status lives on the board, never in docs.
- Link, don't copy, between docs.
- Do not change the board, labels or issues yourself; give the user the `gh` command.
