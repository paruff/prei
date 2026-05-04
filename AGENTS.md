# Agent Instructions — prei (Real Estate Investor Analytics)

> Universal agent instructions for all agents — GitHub Copilot, VS Code agent mode, Claude.
> **Do not modify this file without PM approval.**

-----

## 1. AI Policy

**Stance:** AI agents implement. Humans decide. No AI-generated code merges without human review.

AI is used for: code generation, test writing, documentation, code review assistance.
AI is NOT used for: architectural decisions, database migrations without human review, secrets management.

**Data policy:** No real user PII or production database contents in AI prompts. Source code and internal docs are fine.

-----

## 2. Project Identity

**Product:** prei — Django web app for passive residential real estate investment analytics
**Purpose:** Calculate and track investment KPIs: Cash-on-Cash, Cap Rate, NOI, IRR, DSCR
**Stack:** Python 3.11 · Django · PostgreSQL (psycopg2) · Django REST Framework · Celery · Redis · WebSockets
**Financial libs:** `numpy-financial` for IRR/NPV · `Decimal` for all currency storage
**Tests:** pytest + pytest-django · pytest-bdd · BDD feature files
**Docs:** MkDocs with Diataxis framework at https://paruff.github.io/prei/
**Repository:** github.com/paruff/prei

-----

## 3. Context Files — Read Before Generating Any Code

|Priority|File                       |What You Learn                                            |
|--------|---------------------------|----------------------------------------------------------|
|1       |`core/models.py`           |All Django models, field types, constraints, relationships|
|2       |`docs/ARCHITECTURE.md`     |App/layer boundaries, allowed dependencies                |
|3       |`docs/API_SURFACE.md`      |All public service and utility functions                  |
|4       |`docs/KNOWN_LIMITATIONS.md`|Known issues — do not make these worse                    |
|5       |`docs/CHANGE_IMPACT_MAP.md`|Which files change when models or services change         |

-----

## 4. Architecture Rules — Never Violate These

```
core/models.py       → Django ORM models only. No business logic. No API calls.
core/services/       → Financial calculations and business logic services.
                       (cma.py, portfolio.py, etc.)
core/api_views.py    → DRF views. Calls services. Never raw SQL or direct financial math.
core/serializers.py  → DRF serializers. Validation logic lives here.
core/integrations/   → All external API calls (ATTOM, HUD, market data).
                       Never called from views directly — always via services.
core/tasks.py        → Celery async tasks only. Calls services.
investor_app/finance/utils.py → Pure financial calculation functions (KPIs, projections).
                       No DB access. No Django imports.
templates/           → HTML only. No business logic in templates.
```

**Dependency direction:** `views → services → (models, integrations, finance/utils)`

**NEVER:**

1. Put financial math directly in views or models — it goes in `investor_app/finance/utils.py` or `core/services/`
1. Call external APIs (ATTOM, HUD) from views — always via `core/integrations/`
1. Use `float` for currency storage or DB operations — use `Decimal` always
1. Hardcode rates (tax, vacancy, capex) — use Django settings or environment vars
1. Use `any` type or skip type hints on new public functions

-----

## 5. The PM–Agent Contract

**Workflow:** PM writes issue → assigned to Copilot → agent implements + tests → draft PR → human reviews → human merges

### Agents MAY Do Without Asking

- Read any file, write to `core/`, `tests/`, `docs/`, `finance/`
- Run: `pytest -q`, `ruff check .`, `black --check .`, `mypy .`, `python manage.py check`
- Open draft PRs, add docstrings

### Agents MUST Ask Before

- Adding any new dependency to `requirements.txt`
- Creating or modifying database migrations
- Modifying `.github/workflows/`
- Changing authentication or permission logic
- Touching more than 5 files in one task

### Agents Must NEVER

- Commit secrets, API keys, `SECRET_KEY`, or database credentials
- Modify `AGENTS.md` or `.github/copilot-instructions.md`
- Delete tests without explicit PM instruction
- Push to `main` directly
- Merge their own PRs
- Apply `large-pr-approved` label (humans only)

-----

## 6. Coding Standards

- Python 3.11+. PEP 8. Ruff + Black formatting.
- Type hints on all new functions and public APIs
- Google-style docstrings on all modules, classes, methods
- snake_case for functions and variables
- `Decimal` for all currency: persist as Decimal, convert to float only for numpy/numpy-financial, convert back to Decimal before returning
- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`
- Write failing test first. Commit it. Then implement.
- DORA CI logging on all workflows: log start time, commit SHA, finish time

-----

## 7. Financial Logic Rules

- **No hardcoded rates** — vacancy, tax, capex from settings or env vars
- **Boundary tests required** — every financial function must test: negative, zero, very large values
- **Division by zero** — guard all divides, return 0 or raise `ValueError` with clear message
- **IRR/NPV via numpy-financial** — wrap in try/except with safe fallback and logging
- Centralize in `investor_app/finance/utils.py` so every function is independently testable

-----

## 8. PR Requirements

Every PR must include the AI-Assisted Review Block:

- What this PR does (one sentence)
- Top 2–3 failure modes
- Tests covering this change
- Architecture check (no layer violations)
- Any judgment calls flagged for human review

-----

## 9. Instability Safeguards

- PR size: 400 lines → CI blocks. Override requires `large-pr-approved` from a human.
- Database migrations: every migration has a rollback path documented in the PR
- Rework rate > 10%: stop features, fix instructions first

-----

## 10. Model Selection Policy

prei is a Python 3.11 **Django 4.2 LTS** application with PostgreSQL, DRF, Celery,
and Redis. All agents must specify `Django 4.2 LTS` in any prompt involving
framework-specific code to prevent version drift in generated output.

> **Budget context:** Shared Copilot Pro budget (300 premium requests/month across all
> repos). GPT-4.1 multiplier is 0 — completely free — and is the default for all tasks.
> The coding agent uses exactly 1 premium request per session × the model multiplier.

### Model Ladder

| Level | Model | Multiplier | Rule |
|---|---|---|---|
| L0 — Free default | GPT-4.1 | 0 | Use for ALL tasks unless explicitly listed otherwise below |
| L0 — Free lightweight | GPT-5 mini | 0 | Single-file mechanical edits: requirements.txt, one-line config changes, Markdown |
| L1 — IDE chat upgrade | Claude Haiku 4.5 | 0.33 | Interactive IDE chat sessions only — NOT for coding agent tasks |
| L2 — Justified premium (code) | GPT-5.1-Codex | 1 | Complex queryset optimisation only — see N+1 note below |
| L2 — Justified premium (design) | Claude Sonnet 4.6 | 1 | Domain modelling chat only — see note below |
| PROHIBITED | Claude Opus 4.6 fast | 30 | Never — 30× multiplier. Blocked without explicit written budget approval |
| AVOID | Claude Opus 4.5 / 4.6 | 3 | No prei task type justifies 3× cost |

### Task → Model Routing Table

| Task type | Model | Cost | Notes |
|---|---|---|---|
| Django model change | GPT-4.1 | 0 | Always specify Django 4.2 LTS in issue body |
| DRF serialiser | GPT-4.1 | 0 | |
| DRF ViewSet / APIView | GPT-4.1 | 0 | |
| Celery task definition | GPT-4.1 | 0 | |
| Celery beat schedule | GPT-4.1 | 0 | |
| Django migration (simple) | GPT-4.1 | 0 | Run migration safety checklist before merge — see below |
| Django migration (complex) | GPT-4.1 | 0 | Complex = multi-step or data migration; always run safety checklist |
| DRF unit tests (APITestCase) | GPT-4.1 | 0 | Specify APITestCase pattern in issue; do not use mocking except for external services |
| Celery task tests | GPT-4.1 | 0 | Use CELERY_TASK_ALWAYS_EAGER=True in test settings |
| PostgreSQL query optimisation (simple) | GPT-4.1 | 0 | Simple = single model, no joins across more than 2 tables |
| requirements.txt / pyproject.toml update | GPT-5 mini | 0 | |
| Django settings change | GPT-5 mini | 0 | Single-file, low-risk |
| README or docs update | GPT-5 mini | 0 | |
| Complex queryset optimisation | GPT-5.1-Codex | 1 | See N+1 note below — multi-join annotate/aggregate queries |
| Domain modelling decisions (chat) | Claude Sonnet 4.6 | 1 | Design chat only — not for writing code |
| Django migration safety review (chat) | GPT-4.1 | 0 | Ask: reversible? table lock? zero-downtime path? GPT-4.1 sufficient |
| Interactive IDE chat (VS Code) | Claude Haiku 4.5 | 0.33 | Chat only — do not assign agent tasks to Haiku |
| Manual PR comment invocation | GPT-4.1 | 0 | Use `@copilot` with no `+model` suffix |

### N+1 note — when to use GPT-5.1-Codex for querysets

GPT-4.1 reliably handles single-model queries and simple foreign key traversals.
It produces N+1 bugs on queries that combine three or more of the following:

- Multiple `select_related()` or `prefetch_related()` across 3+ models
- `annotate()` with `Count()`, `Sum()`, or `Avg()` on related sets
- `filter()` on annotated values
- Conditional expressions (`Case`/`When`) inside annotations
- Subqueries (`OuterRef`, `Subquery`)

If the queryset in the issue involves three or more of the above patterns,
use GPT-5.1-Codex and add `model:gpt-5.1-codex` label to the issue.
For all other queryset work, GPT-4.1 is sufficient.

### Domain modelling note — when to use Claude Sonnet 4.6

Use Claude Sonnet 4.6 in **chat mode only** (not agent mode) when making decisions about:

- Adding new Django models to the real estate domain
- Changing relationships between existing models (OneToOne vs ForeignKey vs M2M)
- Designing API surface for a new feature before writing any code
- Evaluating whether a feature belongs in prei vs a separate service

Claude Sonnet produces better natural language reasoning about domain trade-offs than
GPT-4.1. Once the design decision is made, switch back to GPT-4.1 to implement it.

### Migration safety checklist

Every agent PR that includes a migration file must have this checklist in the PR description
before it is reviewed. Copilot must include it; human reviewer must verify it.

```
**Migration safety check:**
- [ ] Migration is reversible: `./manage.py migrate [app] [previous_migration]` succeeds
- [ ] No NOT NULL column added to a large table without a database-level default
- [ ] No table renamed or dropped without a multi-step migration plan
- [ ] Tested against a copy of staging data volume (not just empty test DB)
- [ ] `./manage.py migrate --run-syncdb` passes on a clean database
```

If any checkbox cannot be checked, the PR must not be merged until the migration is
restructured. GPT-4.1 can suggest a zero-downtime alternative if asked.

### Required issue body format

Every issue assigned to the Copilot coding agent must include this block:

```
**Suggested model:** [GPT-4.1 / GPT-5 mini / GPT-5.1-Codex / Claude Sonnet 4.6]
**Django version:** Django 4.2 LTS
**Task type:** [model change / serialiser / viewset / migration / test / queryset / docs]
**Files to edit:** [explicit list — agent must not create new files unless listed here]
**Reference file:** [path to existing similar implementation in the codebase]
**Do not:** [specific anti-patterns, files to avoid, or migration pitfalls]
**Acceptance criteria:**
- [ ] [measurable criterion 1]
- [ ] [measurable criterion 2]
```

### Escalation rule

If rework rate for a task type exceeds 20% after 5 completed PRs with the recommended model:

1. First improve the issue body — add file targets, reference implementations, Django version
2. If rework rate is still above 20% after improving the issue body, escalate to the next model tier
3. Document the decision in this section with the date and evidence

### Budget guardrails

- Never use `@copilot +modelname` in PR comments unless GPT-4.1 has already failed on the same task
- Claude Sonnet 4.6 for domain modelling is chat-only — it must never be assigned to a coding agent task
- The expected premium spend for prei is ~5 requests/month at normal velocity:
  - Complex queryset issues: ~3 sessions at 1x = 3 requests
  - Domain modelling chat: ~2 sessions at 1x = 2 requests
- Django migrations are the highest-risk output type in this repo — always require human review before merge regardless of model used

----
## 11. See Also

- `.github/copilot-instructions.md` — Copilot-specific subset
- `.github/agents/` — `@docs-agent`, `@test-agent`, `@review-agent`, `@security-agent`
- `docs/GOLDEN_PATH.md` — standard feature development workflow
- `docs/PROMPT_LIBRARY.md` — tested prompt templates
- `docs/AI_POLICY.md` — AI policy and psychological safety norms
