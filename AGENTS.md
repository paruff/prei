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

## 10. See Also

- `.github/copilot-instructions.md` — Copilot-specific subset
- `.github/agents/` — `@docs-agent`, `@test-agent`, `@review-agent`, `@security-agent`
- `docs/GOLDEN_PATH.md` — standard feature development workflow
- `docs/PROMPT_LIBRARY.md` — tested prompt templates
- `docs/AI_POLICY.md` — AI policy and psychological safety norms
