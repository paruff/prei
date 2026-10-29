# TOKEN COST: This file loads on every Copilot/Claude Code/Cursor/opencode request.
# Every line is billed on every interaction. Keep it lean.
# Full details live in .agents/skills/ and .agents/roles/ — load on demand only.

# AGENTS — prei

## AI Policy
- AI writes; humans decide.
- Human review before merge.
- No secrets/PII.
- Follow repo docs/tests.
- Ask before risky changes.

## Project Identity
- prei: passive real estate investment analytics for buy-and-hold investors.
- Stack: Django 6.0, see requirements.txt/pyproject.toml. SQLite for local runs; Postgres in production (render.yaml). Single-user for now.
- Constraints: Decimal money; service-layer boundaries; no Bootstrap.
- Design: custom design system with CSS custom properties (tokens.css + base.css).

## Never Do
1. Finance math outside services/utils.
2. External API calls from views.
3. Float persistence for currency.
4. Auth/deps/migrations/workflows need approval — see `migration-safety` skill.
5. Direct push/merge to `main`.
6. Use Bootstrap classes or inline `style=` attributes on layout elements.
7. Hardcode hex colors in templates (exception: PDF export inline styles).
8. Use `!important` in CSS — if a responsive rule is broken, fix the template.
9. Use uppercase in PR title description — the first word after `type(scope):` must be lowercase (see `docs/PR_STANDARD.md`).
10. Swallow an exception in a check, validator, or test assertion without logging what broke — a silently-caught exception makes a check that never ran indistinguishable from one that ran and found nothing.

## Before You Start
- UI changes: read DESIGN.md first (tokens, components, do and don't)
- Reviewing a PR: apply REVIEW.md (what is Important, verification, validation, security)

## Workflow
"What's next for an agent?" and "what waits on a human?" are answered by the
[Real Estate Investor board](https://github.com/users/paruff/projects/3) only. Its **Status** field is the
only place status lives (no status labels, no status in docs). Goal = GitHub milestone (`G0: …`, `G1: …`);
work one goal at a time, in order. Outcome, proof and rows are in `plan.md`. AI-DLC (`.claude/`, `aidlc/`)
may run the stages inside one issue; the board decides what is next. If they disagree, the board wins.

| Status | Means |
|---|---|
| Backlog | Not ready, or its release isn't planned yet |
| Ready for agent | Has a plan row, spec IDs and an Exit criterion |
| In progress | Claimed. Move it here **before** starting |
| Needs human decision | Waiting on a person; the **Gate** field says which decision |
| Blocked | Waiting on something named in an issue comment |
| Done | Closed (set automatically) |

Gate (set only with Needs human decision): `intent` · `spec` · `plan` · `PR review` · `merge/release`.
Gates are approved by merging the PR that changes that file; a question only a human can answer is an
issue labelled `question` (template "Question for a human").

```bash
# 1. Next item for an agent (earliest goal, then lowest issue number)
gh project item-list 3 --owner paruff --limit 200 --query 'status:"Ready for agent" is:open' --format json \
  --jq '.items | sort_by(.milestone.title // "~", .content.number) | .[0] | "#\(.content.number) \(.title)"'

# 2. Waiting on a human, and which decision
gh project item-list 3 --owner paruff --limit 200 --query 'status:"Needs human decision" is:open' --format json \
  --jq '.items[] | "\(.gate // "-")\t#\(.content.number) \(.title)"'
gh pr list --state open --draft=false   # every open non-draft PR waits on a human merge decision

# Move an item
gh project item-edit 3 --owner paruff --url <issue-or-PR-url> --field Status --value "In progress"
```

Lifecycle: pick (command 1) → In progress → branch → PR with `Closes #n` → self-review with REVIEW.md →
post findings as one PR comment (`gh pr review <pr> --comment`, never `--approve`) → Needs human decision,
Gate `PR review` → human merges → Done. Changes requested → back to In progress. New issues: the
`.github/ISSUE_TEMPLATE/` headings, a milestone, and `--project "Real Estate Investor"`.

## GitOps Principles
See `gitops-principles` skill — load before touching workflows, deployment config, or the GitOps manifest repo.

## Context Files
| File | Why |
|---|---|
| `VISION.md` | users, investor journey, principles, non-goals |
| `core/models/` | model rules |
| `docs/ARCHITECTURE.md` | layer rules |
| `docs/CHANGE_IMPACT_MAP.md` | co-change map |
| `docs/KNOWN_LIMITATIONS.md` | active known issues |
| `docs/PR_STANDARD.md` | PR naming rules |
| `docs/FEATURE_SPEC_GUIDE.md` | how to write intent/spec/plan |
| `docs/DEPLOYMENT_STRATEGY.md` | canary + progressive delivery plan |

## Project File Structure

```
intent.md             ← ACTIVE intent: problem, outcome, constraints (gate: intent)
spec.md               ← ACTIVE spec: requirements + acceptance criteria (gate: spec)
plan.md               ← ACTIVE plan: goals (milestones), proof, rows, risks (gate: plan)
VISION.md             ← PRODUCT-LEVEL users, journey, principles, non-goals (permanent)
features/<slug>/      ← ARCHIVED intent/spec/plan (permanent record after release)
docs/                 ← LASTING documentation (architecture, API, standards)
docs/assessments/     ← one-off audit/assessment reports
docs/planning/        ← policy documents (AI_POLICY.md)
docs/archive/         ← superseded plans and strategy (read-only)
tests/                ← test suites
```
