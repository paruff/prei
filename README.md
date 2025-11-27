# Real Estate Investor — Property Analytics

A Django-based web application to analyze and track residential real estate investments (KPIs such as Cash-on-Cash, Cap Rate, NOI, IRR, DSCR, etc.). This repository contains the initial scaffold and CI for building the investment analytics web app.

Quick start (local)
1. Clone the repo:
   - git clone git@github.com:<your-org-or-user>/<repo-name>.git
   - cd <repo-name>

2. Create a virtual environment and install deps:
   - python3.11 -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt

3. Initialize Django project (if not already created):
   - ./scripts/init_django.sh investor_app

4. Create .env from .env.example and update values:
   - cp .env.example .env
   - edit .env (set SECRET_KEY, DATABASE_URL)

5. Run migrations and start dev server:
   - python manage.py migrate
   - python manage.py runserver

CI & tooling
- Linting & formatting: ruff + black
- Type checking: mypy (encouraged for new modules)
- Tests: pytest + Django testing tools
- CI: GitHub Actions (see .github/workflows/ci.yml) — workflows include DORA-friendly logging of deploy/test start/finish timestamps and commit SHA.

Repository purpose
- Host the web application and all related code, tests, infra config, and documentation for the investment/analysis product.
- Keep the old scraper (if useful) in a standalone archival repo or in a `legacy-scraper/` directory only after explicit migration.

If you want me to push this scaffold to a new repo for you, tell me the repository name and visibility and I’ll produce the exact commands or do the creation for you.
