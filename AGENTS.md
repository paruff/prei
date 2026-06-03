# TOKEN COST: This file loads on every Copilot/Claude Code/Cursor request.
# Every line is billed on every interaction. Keep it lean.
# Full details live in .github/skills/ — load them on demand only.

# AGENTS — prei

## AI Policy
- AI implements; humans decide architecture, risk acceptance, and merge approvals.
- No AI-generated change merges without human review of code, tests, and PR notes.
- Never include production secrets, credentials, or real user PII in prompts.
- Use repo docs and tests as primary truth; uncertain behavior must be escalated.
- Security-sensitive changes (auth, permissions, workflows, dependencies) require explicit human approval.
- AI output must be validated with project checks before review handoff.

## Project Identity
- Product: prei — residential real estate investment analytics platform.
- Stack: Python 3.11, Django 4.2 LTS, DRF, PostgreSQL, Celery, Redis, MkDocs.
- Key constraints: Decimal currency math, layered architecture, service-first business logic.

## Never Do (Hard Rules)
1. Do not put financial math in views/models/templates (use `investor_app/finance/utils.py` or `core/services/`).
2. Do not call external APIs from views (integrations must flow through `core/integrations/` + services).
3. Do not use float for persisted currency values; use Decimal end-to-end.
4. Do not modify migrations, dependencies, auth/permissions, or workflows without human approval.
5. Do not merge or push directly to `main`, and never bypass required human review.

## Token Budget Protocol (Agent Mode)
Before implementation, post a 2-sentence scope check: files to read, files to change, and expected output.
If scope exceeds 5 files or touches high-risk surfaces (auth, migrations, workflows, dependencies), stop and request approval.
Load only relevant on-demand skill files; do not preload all skills.

## On-Demand Skills (.github/skills)
| Skill | Purpose |
|---|---|
| `architecture/SKILL.md` | Layer boundaries, dependency rules, architecture checklist |
| `pr-contract/SKILL.md` | PM-agent contract, PR requirements, coding/testing/merge guardrails |
| `metrics/SKILL.md` | DORA + rework + AI credit burn targets and measurement ritual |
| `model-routing/SKILL.md` | Ask/Edit/Agent mode and model selection rules |

## Context Files (Read Before Code Changes)
| File | Why |
|---|---|
| `core/models.py` | Model constraints and domain entities |
| `docs/ARCHITECTURE.md` | Layer boundaries and allowed dependencies |
| `docs/API_SURFACE.md` | Public service and utility contracts |
| `docs/KNOWN_LIMITATIONS.md` | Existing constraints to preserve |
| `docs/CHANGE_IMPACT_MAP.md` | Required co-changes for model/service updates |

## See Also
- `docs/COPILOT_COST_GUIDE.md`
- `docs/MODEL_ROUTING_GUIDE.md`
- `docs/GOLDEN_PATH.md`
