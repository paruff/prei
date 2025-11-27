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

3) DORA metrics & CI behavior
- Favor small, focused commits/PRs (Deployment Frequency).
- Add unit tests for new logic (Lead Time for Changes).
- Add robust error handling and clear logs for financial calculations and DB transactions (reduce CFR, improve MTTR).
- CI workflows must log start/finish timestamps and the commit SHA:
  - echo "job-start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  - echo "sha: ${{ github.sha }}"
  - echo "job-finish: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

4) Coding standards
- Follow PEP 8. Use ruff + black for formatting.
- Use snake_case for functions and variables.
- Prefer absolute imports.
- Add type hints to new functions/methods and public APIs.
- Document modules/classes/methods with Google-style docstrings.

5) Financial logic practices
- Do NOT hardcode rates (tax, vacancy, capex). Use Django settings or environment configuration.
- Use Decimal (from decimal import Decimal) for currency math when storing/reading values from DB. Convert to float only for non-persistent numeric libraries if needed.
- Centralize financial helpers (e.g., investor_app/finance/utils.py) so tests can target them easily.

6) Validation & data integrity
- Validate all user input related to property financials at both form/serializer and model levels.
- Provide boundary tests for negative, zero, and very large values in financial calculations.

7) Tests & fixtures
- Unit tests for financial calculations are mandatory.
- Use pytest + pytest-django. Keep tests deterministic; avoid network calls in unit tests.
- Integration tests that require external services should be gated behind specific CI workflows or run manually.

8) Security & operations
- Secrets must be stored in environment variables / GitHub Secrets.
- Keep DEBUG=False in production.
- Add logging and monitoring hooks in critical paths to enable quick incident response.

9) When modifying CI workflows
- Ensure the workflow prints timestamps and commit SHAs (see section 3).
- Workflows should be split so scraper tasks (if any) do not run under webapp CI by default.
- Keep networked sample scrapes or heavy integration tests gated by workflow_dispatch or a cron schedule.

10) Migration note
- If you are porting components from the legacy scraper, do so on a dedicated migration branch
