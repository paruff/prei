# Copilot Instructions — Real Estate Investor App

This repository is a Django-based web application focused on passive residential real estate investing analytics. These instructions guide GitHub Copilot-style agents when generating code, tests, and CI changes for this project.

1) Project Overview & Context
- Purpose: Analyze and track investment properties and compute financial KPIs (Cash-on-Cash, Cap Rate, NOI, IRR, DSCR).
- Primary models to implement: User (Django auth), Property, InvestmentAnalysis, Transaction, RentalIncome, OperatingExpense.
- Keep financial logic centralized and well-tested.

2) Tech stack & tools
- Python 3.11+
- Django (default)
- Database: PostgreSQL (psycopg2-binary)
- Financial libs: numpy and numpy-financial for IRR/NPV where appropriate; use Decimal for currency precision in DB interactions.
- CI: GitHub Actions — all CI templates should include DORA-friendly logging.
 - Local dev: Allow SQLite fallback when `DATABASE_URL` is absent to ease local testing.
 - Containerization: Dockerfile + docker-compose with services `web` and `db`; inside Compose use `DATABASE_URL=postgres://...@db:5432/...`; on host use `localhost`.

3) DORA metrics & CI behavior
- Favor small, focused commits/PRs (Deployment Frequency).
- Add unit tests for new logic (Lead Time for Changes).
- Add robust error handling and clear logs for financial calculations and DB transactions (reduce CFR, improve MTTR).
- CI workflows must log start/finish timestamps and the commit SHA:
  - echo "job-start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  - echo "sha: ${{ github.sha }}"
  - echo "job-finish: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
 - Include test stages for unit, integration, and BDD; run `pytest -q` with clear failure summaries.
 - Lint/type/format stages: `ruff`, `black --check`, `mypy`.

4) Coding standards
- Follow PEP 8. Use ruff + black for formatting.
- Use snake_case for functions and variables.
- Prefer absolute imports.
- Add type hints to new functions/methods and public APIs.
- Document modules/classes/methods with Google-style docstrings.
 - Keep Django settings environment-driven. Use `django-environ` and parse numeric config explicitly (e.g., `Decimal(env("VACANCY_RATE", default="0.05"))`).

5) Financial logic practices
- Do NOT hardcode rates (tax, vacancy, capex). Use Django settings or environment configuration.
- Use Decimal (from decimal import Decimal) for currency math when storing/reading values from DB. Convert to float only for non-persistent numeric libraries if needed.
- Centralize financial helpers (e.g., investor_app/finance/utils.py) so tests can target them easily.
 - Provide clear conversion boundaries: persist `Decimal`, convert to `float` only when passing to numpy/numpy-financial; convert results back to `Decimal` as needed.

6) Validation & data integrity
- Validate all user input related to property financials at both form/serializer and model levels.
- Provide boundary tests for negative, zero, and very large values in financial calculations.
 - Add model-level validation for required fields (e.g., addresses, purchase_price >= 0) and helper methods (e.g., monthly amount normalization).

7) Tests & fixtures
- Unit tests for financial calculations are mandatory.
- Use pytest + pytest-django. Keep tests deterministic; avoid network calls in unit tests.
- Integration tests that require external services should be gated behind specific CI workflows or run manually.
 - Provide three layers of tests:
   - Unit: finance utils and model helpers.
   - Integration: views, URL routing, templates, DB interactions (e.g., dashboard computes KPIs).
   - BDD: scenario-based tests (optionally via `pytest-bdd`) with feature files describing investor workflows.
 - Add common fixtures in `core/tests/conftest.py` (e.g., `user`).

8) Security & operations
- Secrets must be stored in environment variables / GitHub Secrets.
- Keep DEBUG=False in production.
- Add logging and monitoring hooks in critical paths to enable quick incident response.
 - Clarify env differences:
   - Local host runs: `.env` may omit `DATABASE_URL` to use SQLite; otherwise set `localhost` for Postgres.
   - Compose runs: `.env` should use `db` hostname for Postgres.

9) When modifying CI workflows
- Ensure the workflow prints timestamps and commit SHAs (see section 3).
- Workflows should be split so scraper tasks (if any) do not run under webapp CI by default.
- Keep networked sample scrapes or heavy integration tests gated by workflow_dispatch or a cron schedule.
 - Provide a matrix for Python versions when applicable; default to Python 3.11.
 - Cache pip dependencies to speed up CI.

10) Migration note
- If you are porting components from the legacy scraper, do so on a dedicated migration branch

11) Developer experience & runbooks
- Provide `.env.example` with sensible defaults for local and Compose runs.
- Add `README.md` sections for:
  - Local run (venv, SQLite fallback, migrations, superuser, runserver)
  - Docker Compose run (build, migrate via `docker compose exec web`, preview at `localhost:8000`)
- Add `scripts/` helpers for common tasks (e.g., `init_django.sh`, import CSV management command usage).

12) Data import & seed
- Implement a management command `import_csv` to load properties, rents, and expenses.
- Document CSV schemas; ensure validation and informative error messages.
- Provide small sample CSVs in `data/` for quick demos (optional).

13) App architecture guidance
- Project: `investor_app` (settings, urls, wsgi/asgi).
- Apps:
  - `core`: models (`Property`, `RentalIncome`, `OperatingExpense`, `Transaction`, `InvestmentAnalysis`), admin, views (dashboard), urls.
  - `finance`: utilities (`utils.py`) for KPI computations.
- Templates: place core views under `templates/` (e.g., `dashboard.html`).

14) Error handling & resilience
- Guard divide-by-zero and invalid inputs in finance utils (return 0 or raise explicit `ValueError` where appropriate).
- Use try/except around third-party computations (e.g., `numpy_financial.irr`), with safe fallbacks and logs.

15) Static files
- Create `static/` to avoid warnings; keep `STATICFILES_DIRS` pointing to it.
- For production, collect static to `staticfiles/`.
