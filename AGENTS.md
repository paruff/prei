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
- Stack: Python 3.14, Django 5.2, DRF, SQLite (default/alpha), Postgres (reserved for post-MVP production — see docker-compose.yml).
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
1. **Git is the source of truth.** Config, workflows, deployment state — all in git. Never modify running infrastructure directly.
2. **Immutable artifacts.** The Docker image is the deployable unit. Test the artifact, not the source. Never rebuild for deployment.
3. **PR gates are deploy gates.** Every merge to `main` is a deploy candidate. Broken `main` blocks all PRs — fix main CI before merging anything else.
4. **Declarative pipelines.** Workflows describe DESIRED STATE: what artifacts, what gates, what triggers. Not imperative scripts.
5. **Artifact verification.** Every PR that touches workflows or deployment config must be verified against the live container via `post-deployment.yml`.
6. **Rollback is `git revert`.** Rollback to a previous commit on the GitOps manifest repo. The rollback job in `post-deployment.yml` is a safety net, not the primary mechanism.
7. **Observability built-in.** Every workflow step logs `job-start` / `job-finish` timestamps. Build times, test results, deploy status are traceable.
8. **Progressive delivery.** Canary → staging → production (see `docs/DEPLOYMENT_STRATEGY.md`). Never ship to 100% in one step.
9. **Naming is infrastructure.** PR titles follow Conventional Commits. Commit messages describe intent. Tags trigger deployments.
10. **Branch discipline.** All work happens on feature branches off `main` (trunk-based development, short-lived). Never commit directly to `main`. Branch naming: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`. Every branch opens a PR through CI gates before merge.

## Context Files
| File | Why |
|---|---|
| `core/models/` | model rules |
| `docs/ARCHITECTURE.md` | layer rules |
| `docs/CHANGE_IMPACT_MAP.md` | co-change map |
| `docs/KNOWN_LIMITATIONS.md` | active known issues |
| `docs/PR_STANDARD.md` | PR naming rules |
| `docs/DEPLOYMENT_STRATEGY.md` | canary + progressive delivery plan |
| `docs/TEST_PYRAMID_PLAN.md` | testing gates and phases |
| `docs/TOP_01_PLAN.md` | top 0.1% quality roadmap |
