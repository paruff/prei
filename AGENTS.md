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
- Stack: see requirements.txt/pyproject.toml. Postgres is reserved for post-MVP production — see docker-compose.yml.
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

## GitOps Principles
See `gitops-principles` skill — load before touching workflows, deployment config, or the GitOps manifest repo.

## Context Files
| File | Why |
|---|---|
| `discovery-brief.md` | product vision, users, core journeys |
| `core/models/` | model rules |
| `docs/ARCHITECTURE.md` | layer rules |
| `docs/CHANGE_IMPACT_MAP.md` | co-change map |
| `docs/KNOWN_LIMITATIONS.md` | active known issues |
| `docs/PR_STANDARD.md` | PR naming rules |
| `docs/FEATURE_SPEC_GUIDE.md` | how to write spec/design/tasks |
| `docs/DEPLOYMENT_STRATEGY.md` | canary + progressive delivery plan |
| `docs/TEST_PYRAMID_PLAN.md` | testing gates and phases |
| `docs/TOP_01_PLAN.md` | top 0.1% quality roadmap |
| `docs/DOCS_AUDIT.md` | documentation audit and alignment |

## Project File Structure

```
specification.md      ← ACTIVE feature spec (ephemeral, overwritten per feature)
design.md             ← ACTIVE feature design
tasks.json            ← ACTIVE feature tasks
discovery-brief.md    ← PRODUCT-LEVEL vision, users, journeys (permanent)
features/<slug>/      ← ARCHIVED feature specs (permanent record after merge)
docs/                 ← LASTING documentation (architecture, API, standards)
docs/assessments/     ← one-off audit/assessment reports
docs/planning/        ← roadmap, strategy, policy documents
tests/                ← test suites
```
