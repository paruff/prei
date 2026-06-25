# prei Agent Infrastructure Plan

## Project

prei — real-estate analytics platform
Stack: Py3.11, Django 4.2, DRF, Postgres
Core domain: financial calculations (IRR, DSCR, cap rate, BRRRR), property data collection (VRM, HUD, ATTOM)

## Completed work

### Phase 1: Consolidation (bc2fb2c)
- Created `.agents/` as single source of truth
- Migrated all agent/skill/role definitions from `.github/agents/`, `.github/skills/`, `uar/`
- Deleted `uar/` entirely (dead runtime scripts, thin stubs, duplicate workflow)
- Updated all path references in AGENTS.md, copilot-instructions.md, docs/METRICS.md, scripts/token-audit.sh

### Phase 2: Sprint 2 (eeb3cea)
- Expanded `security.md` from 46 → 119 lines (Django/DRF checks, OWASP mapping, data-at-rest)
- Added planner↔coder escalation protocol (coder emits `### Escalation`, planner replans)
- Rewrote `feature.yml` as annotated reference checklist with gates and escalation loop

### Phase 3: Ship blockers (02dcf4e)
- Consolidated `test-agent.md` and `test-writer.md` (absorbed BDD, coverage workflow, instability safeguard)
- Removed `core/tasks.py` from architecture skill (file doesn't exist)
- Fixed `npm run token-audit:save` → `scripts/token-audit.sh` in metrics skill
- Added `docs` agent to AGENTS.md Agent Roles table
- Aligned validation commands to `make check` in copilot-instructions.md

### Phase 4: Domain skills + opencode config (0f2ad02)
- Created `finance-review` skill (Decimal safety, division guards, edge cases, quantization, tax/depreciation)
- Created `data-collection` skill (VRM/HUD/ATTOM scrapers, freshness, failures, costs)
- Created `bugfix.yml` workflow (expedited path skipping planner)
- Created `opencode.json` with skill paths, agent definitions, AGENTS.md instruction

## Review and security scan results

| Phase | Review | Security |
|-------|--------|----------|
| Consolidation | PASS (1 stale reference fixed) | N/A |
| Sprint 2 | PASS (1 blocker + 2 recommended fixed) | N/A |
| Ship blockers | PASS (5/5 resolved) | N/A |
| Domain skills | PASS (3 items fixed) | LOW risk, SECURE |

## Current state

### .agents/ structure (22 files)

```
.agents/
├── README.md
├── memory/
│   ├── plan.md                        ← this file
│   └── agent_scores.jsonl             ← append-only evaluation log
├── roles/
│   ├── planner.md                     (task decomposition + replanning protocol)
│   ├── coder.md                       (implementation + escalation protocol)
│   ├── reviewer.md                    (architecture/security/test gates)
│   ├── security.md                    (Django/DRF checks, OWASP, data-at-rest)
│   └── test-writer.md                 (test-first, BDD, coverage, instability safeguard)
├── agents/
│   ├── docs-agent.md                  (standalone — no role equivalent)
│   ├── test-agent.md                  (thin dispatcher → roles/test-writer.md)
│   ├── review-agent.md                (thin dispatcher → roles/reviewer.md)
│   └── security-agent.md              (thin dispatcher → roles/security.md)
├── skills/
│   ├── architecture/SKILL.md          (layer boundaries, dependency rules)
│   ├── data-collection/SKILL.md       (VRM/HUD/ATTOM scrapers)
│   ├── evaluation/SKILL.md            (agent accuracy scoring)
│   ├── finance-review/SKILL.md        (financial math review)
│   ├── metrics/SKILL.md               (DORA + AI credit tracking)
│   ├── model-routing/SKILL.md         (mode/model decision tables)
│   └── pr-contract/SKILL.md           (PR size, AI-assisted review block)
└── workflows/
    ├── bugfix.yml                     (triage → fix → review → verify → PR → evaluate)
    ├── evaluate.yml                   (score agent accuracy after each feature/bugfix)
    └── feature.yml                    (plan → implement → review → security → approve → verify → PR → evaluate)
```

### Root config

| File | Purpose |
|------|---------|
| `AGENTS.md` | Lean entry point (loaded on every AI request, token-cost-aware) |
| `opencode.json` | opencode config (skill paths, agent definitions, AGENTS.md instruction) |
| `.github/copilot-instructions.md` | Copilot-specific (references .agents/skills/) |
| `scripts/agent_report.py` | Monthly agent accuracy aggregation script |

### Git history (this session)

```
0f2ad02 feat: add domain skills, bugfix workflow, and opencode config
02dcf4e fix: resolve 5 ship blockers from .agents/ review
eeb3cea feat: expand security agent, add escalation protocol, rewrite workflow
bc2fb2c refactor: consolidate agent infrastructure into .agents/
```

## Backlog

### P2 — Evaluation loop (effort: L) ✅ DONE
- ✅ Created `evaluation` skill (scoring protocol, dimensions per agent, 1-5 scale)
- ✅ Created `evaluate.yml` workflow (per-feature scoring)
- ✅ Created `scripts/agent_report.py` (monthly aggregation, correction patterns)
- ✅ Integrated into `feature.yml` (step 8) and `bugfix.yml` (step 7)
- ✅ Updated `metrics` skill with monthly agent review ritual

### P3 — Nice to have ✅ DONE
- ✅ Created `hotfix.yml` workflow (expedited with mandatory security review)
- ✅ Integrated `health_monitor.py` into reviewer role (data collection health checks)
- ✅ Created `migration-safety` skill (reversible migrations, Decimal safety, anti-patterns)
- ✅ Deduplicated `pr-contract` ↔ `coder.md` (coder.md now references pr-contract for permissions)

## Key design decisions

1. **Single source of truth:** `.agents/` is canonical. `.github/agents/` deleted. No copies.
2. **Lean always-on:** `AGENTS.md` is the only always-on file (~60 lines). Skills loaded on demand.
3. **Human gates non-negotiable:** Migrations, auth changes, new deps always require human approval.
4. **Roles vs agents:** `roles/` = full definitions. `agents/` = thin dispatchers for Copilot @agent.
5. **Workflows are checklists:** Not machine-executed. Agents and humans follow them as protocols.
