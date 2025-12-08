# Real Estate Investor — Property Analytics

A Django-based web application to analyze and track residential real estate investments (KPIs such as Cash-on-Cash, Cap Rate, NOI, IRR, DSCR, etc.). This repository contains the initial scaffold and CI for building the investment analytics web app.

## 📚 Documentation

Comprehensive documentation is available at **[https://paruff.github.io/prei/](https://paruff.github.io/prei/)**

The documentation follows the [Diátaxis framework](https://diataxis.fr/) with four sections:
- **[Tutorials](https://paruff.github.io/prei/tutorials/getting-started/)** — Step-by-step learning guides
- **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** — Practical solutions for specific tasks
- **[Reference](https://paruff.github.io/prei/reference/)** — Technical specifications and API docs
- **[Explanation](https://paruff.github.io/prei/explanation/)** — Architecture and design rationale

To build documentation locally:
```bash
pip install -r docs-requirements.txt
mkdocs serve  # View at http://127.0.0.1:8000
```

## Quick start (local)

For detailed setup instructions, see the **[Getting Started Tutorial](https://paruff.github.io/prei/tutorials/getting-started/)**.

1. Clone the repo:
   - `git clone git@github.com:paruff/prei.git`
   - `cd prei`

2. Create a virtual environment and install deps:
   - `python3.11 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`

3. Create .env from .env.example and update values:
   - `cp .env.example .env`
   - Edit `.env` (set SECRET_KEY, DATABASE_URL)

4. Run migrations and start dev server:
   - `python manage.py migrate`
   - `python manage.py runserver`

## CI & tooling

- **Linting & formatting:** ruff + black
- **Type checking:** mypy (encouraged for new modules)
- **Tests:** pytest + Django testing tools
- **Documentation:** MkDocs with Material theme
- **CI:** GitHub Actions (see `.github/workflows/`) — workflows include DORA-friendly logging of deploy/test start/finish timestamps and commit SHA.

See the **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** for detailed instructions on running tests, linters, and other development tasks.

## Repository purpose

- Host the web application and all related code, tests, infra config, and documentation for the investment/analysis product.
- Keep the old scraper (if useful) in a standalone archival repo or in a `legacy-scraper/` directory only after explicit migration.

## Contributing

Please refer to our documentation for information on how to contribute to this project. See **[How-to Guides](https://paruff.github.io/prei/how-to-guides/)** and **[Explanation](https://paruff.github.io/prei/explanation/)** sections.

## License

This project is licensed under the terms specified in the repository.
