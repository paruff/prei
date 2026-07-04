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
- Stack: Python 3.12, Django 5.2, DRF, SQLite (default/alpha), Postgres (reserved for post-MVP production — see docker-compose.yml).
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

## Token Budget Protocol
Agent Mode: read files, write files, 2-sentence plan.
If scope >5 files or high risk, ask.

## On-Demand Skills
| Skill | Use |
|---|---|
| `architecture` | boundaries |
| `data-collection` | scrapers, freshness, failures |
| `evaluation` | agent accuracy scoring |
| `finance-review` | financial math review |
| `metrics` | DORA + credits |
| `migration-safety` | schema/data migration review |
| `model-routing` | mode routing |
| `pr-contract` | PR gates |

## Context Files
| File | Why |
|---|---|
| `core/models.py` | model rules |
| `docs/ARCHITECTURE.md` | layer rules |
| `docs/CHANGE_IMPACT_MAP.md` | co-change map |
| `docs/KNOWN_LIMITATIONS.md` | active known issues — read before touching a listed area |

## Agent Roles
Roles live in `.agents/roles/`. Load on demand.
| Role | Use |
|---|---|
| `planner` | Task decomposition |
| `coder` | Implementation |
| `reviewer` | Pre-merge gates |
| `security` | Security audit |
| `test-writer` | Test coverage |

<!--
KNOWN GAP (unresolved, flagging rather than guessing): opencode.json only loads
skills/roles from .agents/skills and .agents/roles. A "docs" role was previously
listed here pointing at .agents/agents/docs-agent.md, but that folder is not on
opencode.json's load path and nothing else in the repo references it — so that
role was likely never actually reachable by opencode. Two options, your call:
  (a) move .agents/agents/docs-agent.md -> .agents/roles/docs.md and add it
      back to the table above and to opencode.json's agent list, or
  (b) delete .agents/agents/ entirely (also covers security-agent.md,
      review-agent.md, test-agent.md, which duplicate .agents/roles/*.md
      under different names and are equally unreferenced).
Not resolved in this edit — I didn't want to silently delete or move files
without you confirming which agent definitions are the ones you're actually
using day to day.
-->

## See Also
- `.agents/README.md`
- `docs/COPILOT_COST_GUIDE.md`
- `docs/MODEL_ROUTING_GUIDE.md`
- `docs/GOLDEN_PATH.md`
