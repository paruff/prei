# .agents/ — prei agent definitions

Single source of truth for all AI-assisted development in prei.

## Structure

```
.agents/
├── roles/          # Internal role definitions (canonical)
│   ├── planner.md
│   ├── coder.md
│   ├── reviewer.md
│   ├── security.md
│   └── test-writer.md
├── agents/         # External entry points (Copilot @agent, etc.)
│   ├── docs-agent.md
│   ├── test-agent.md
│   ├── review-agent.md    (dispatcher → roles/reviewer.md)
│   └── security-agent.md  (dispatcher → roles/security.md)
├── skills/         # On-demand skill packs (load selectively)
│   ├── architecture/SKILL.md
│   ├── metrics/SKILL.md
│   ├── model-routing/SKILL.md
│   └── pr-contract/SKILL.md
├── workflows/      # Multi-agent pipelines
│   └── feature.yml
└── README.md       # This file
```

## Roles

| Role | Purpose | When to use |
|---|---|---|
| `planner` | Task decomposition + risk flags | Before any implementation |
| `coder` | Minimal-diff implementation | After planner defines tasks |
| `reviewer` | Architecture/security/test gates | Before human review |
| `security` | Deep security audit | Security-sensitive changes |
| `test-writer` | Test-first coverage | Coverage gaps or new features |

## Agents

Thin dispatchers for external tools (GitHub Copilot `@agent` invocation).
Each references the canonical role definition in `roles/`.

## Skills

On-demand context loaded selectively to control token cost.
Referenced from `AGENTS.md` — never loaded by default.

## Workflows

- **feature.yml**: planner → coder → reviewer → human approve → verify → PR

## Design Principles

- **Single source of truth.** All agent/skill/role definitions live here. No copies in `.github/`.
- **Human gates are non-negotiable.** Migrations, auth changes, and new deps always require human approval.
- **Load on demand.** Skills and roles are loaded selectively — `AGENTS.md` is the only always-on file.
- **Separate concerns.** `roles/` = who does what. `agents/` = external entry points. `skills/` = context packs. `workflows/` = coordination.
