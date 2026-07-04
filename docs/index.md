# prei — Passive Real Estate Investment Analytics

Welcome to the documentation for prei, a Django-based web application designed to analyze residential real estate investments for buy-and-hold investors.

## What is prei?

prei computes key performance indicators (KPIs) such as:

- **Cash-on-Cash Return** — Annual pre-tax cash flow divided by total cash invested
- **Capitalization Rate (Cap Rate)** — Net Operating Income divided by property value
- **Net Operating Income (NOI)** — Total income minus operating expenses
- **Internal Rate of Return (IRR)** — Time-weighted return on investment
- **Debt Service Coverage Ratio (DSCR)** — NOI divided by annual debt service

## Documentation Structure

This documentation follows the [Diátaxis framework](https://diataxis.fr/):

### 📚 [Tutorials](tutorials/getting-started.md)
Step-by-step lessons — start here if you're new.

### 🛠️ [How-to Guides](how-to-guides/index.md)
Practical guides for local dev, Codespaces, Render deployment, and daily tasks.

### 📖 [Reference](reference/index.md)
Financial KPIs, data sources, API keys — detailed technical info.

### 💡 [Explanation](explanation/index.md)
Architecture, design decisions, and the design system.

## Quick Links

- [Getting Started Tutorial](tutorials/getting-started.md)
- [Local Docker Setup](how-to-guides/local-dev.md)
- [Dev Container / Codespaces](how-to-guides/devcontainer.md)
- [Deploy to Render](how-to-guides/render-deploy.md)
- [API Keys Reference](reference/api-keys.md)
- [Financial KPIs](reference/financial-kpis.md)
- [GitHub Repository](https://github.com/paruff/prei)

## Technology Stack

- **Backend:** Django 5.2 with Python 3.12
- **Database:** SQLite (dev), PostgreSQL (Render prod)
- **Financial Libraries:** NumPy, pandas
- **Testing:** pytest, pytest-django
- **Code Quality:** ruff, mypy

## Repository

Source: [https://github.com/paruff/prei](https://github.com/paruff/prei)
