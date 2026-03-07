# Copilot Instructions — prei (Real Estate Investor Analytics)

> This file extends the existing `.github/copilot-instructions.md`.
> Loaded automatically for every Copilot session. Full rules in `AGENTS.md`.

## Context Files — Read These First

1. `core/models.py` — all Django models and field constraints
2. `docs/ARCHITECTURE.md` — app/layer boundaries
3. `docs/API_SURFACE.md` — all public service and utility functions
4. `docs/KNOWN_LIMITATIONS.md` — do not make these worse
5. `finance/utils.py` — existing KPI calculation functions (check before adding new ones)

## Architecture Rules — Never Violate

1. **Financial math in `finance/utils.py`** — never in views, models, or templates
2. **External API calls in `core/integrations/`** — never called from views directly
3. **Views call services** — `core/api_views.py` calls `core/services/`, not models directly
4. **`Decimal` for currency** — persist as Decimal, convert to float only for numpy, convert back before returning
5. **No hardcoded rates** — vacancy, tax, capex from Django settings or env vars

## Stack

- Python 3.11 · Django · PostgreSQL · DRF · Celery · Redis
- numpy-financial for IRR/NPV · Decimal for currency precision
- pytest + pytest-django + pytest-bdd

## Coding Standards

- Type hints on all new functions and public APIs
- Google-style docstrings on modules, classes, methods
- Ruff + Black formatting (enforced by CI)
- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- Failing test committed before implementation

## Financial Logic Requirements

- Guard all divides against zero — return 0 or raise `ValueError` with a clear message
- Boundary tests mandatory: every financial function tests negative, zero, and very large values
- IRR/NPV: wrap numpy-financial calls in try/except with safe fallback and log

## What Requires Human Approval

- New `requirements.txt` dependencies
- Database migrations (always need rollback path in PR)
- `.github/workflows/` changes
- Authentication or permission logic changes
- > 5 files in one task

## Golden Path

See `docs/GOLDEN_PATH.md`. In brief:
```
Spec → Branch → Failing test (commit) → Implement → preflight → Draft PR
```

Run before every push: `ruff check . && black --check . && pytest -q`

## PR Requirement

Every PR needs the AI-Assisted Review Block: what it does, how tested, architecture check, failure modes, judgment calls.

## DORA CI Logging

All CI workflows must log:
```bash
echo "job-start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "sha: ${{ github.sha }}"
echo "job-finish: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
