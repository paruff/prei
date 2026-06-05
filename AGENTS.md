# TOKEN COST: This file loads on every Copilot/Claude Code/Cursor request.
# Every line is billed on every interaction. Keep it lean.
# Full details live in .github/skills/ — load them on demand only.

# AGENTS — prei

## AI Policy
- AI writes; humans decide.
- Human review before merge.
- No secrets/PII.
- Follow repo docs/tests.
- Ask before risky changes.

## Project Identity
- prei: real-estate analytics.
- Stack: Py3.11, Django 4.2, DRF, Postgres.
- Constraints: Decimal money; service-layer boundaries.

## Never Do
1. Finance math outside services/utils.
2. External API calls from views.
3. Float persistence for currency.
4. Auth/deps/migrations/workflows need approval.
5. Direct push/merge to `main`.

## Token Budget Protocol
Agent Mode: read files, write files, 2-sentence plan.
If scope >5 files or high risk, ask.

## On-Demand Skills
| Skill | Use |
|---|---|
| `architecture` | boundaries |
| `pr-contract` | PR gates |
| `metrics` | DORA + credits |
| `model-routing` | mode routing |

## Context Files
| File | Why |
|---|---|
| `core/models.py` | model rules |
| `docs/ARCHITECTURE.md` | layer rules |
| `docs/CHANGE_IMPACT_MAP.md` | co-change map |

## See Also
- `docs/COPILOT_COST_GUIDE.md`
- `docs/MODEL_ROUTING_GUIDE.md`
- `docs/GOLDEN_PATH.md`
