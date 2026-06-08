# Copilot Instructions — prei (Lean Always-On)

Keep this file minimal to control token spend. Load details from `.agents/skills/*/SKILL.md` on demand.

## Required startup behavior
1. Read `AGENTS.md` first.
2. State scope in 2 sentences: files to read, files to change, expected output.
3. If request touches auth, workflows, migrations, or dependencies, ask for human approval before editing.

## Core project rules
- Django 4.2 LTS patterns only for framework-specific changes.
- Financial math lives in `investor_app/finance/utils.py` or `core/services/`, not views/models/templates.
- External API calls live in `core/integrations/` and are consumed via services.
- Persist currency as `Decimal`; avoid float persistence.
- Human review is mandatory before merge.

## Load on-demand skills
- Architecture: `.agents/skills/architecture/SKILL.md`
- PR contract: `.agents/skills/pr-contract/SKILL.md`
- Metrics: `.agents/skills/metrics/SKILL.md`
- Model routing: `.agents/skills/model-routing/SKILL.md`

## Validation baseline
Run: `make check`
