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

## Investor Workflow

Follow the four-stage workflow from market selection to deal analysis:

1. [Analyzing Growth Areas](how-to-guides/analyze-growth-areas.md) — find high-growth markets
2. [Discovering Properties](how-to-guides/discover-properties.md) — source distressed properties
3. [Screening Properties](how-to-guides/screen-properties.md) — filter against your criteria
4. [Underwriting Deals](how-to-guides/underwrite-deals.md) — analyze deals financially

Start with the [Investor Workflow Overview](explanation/investor-workflow.md) to see how
the stages connect.

## Quick Links

- [Getting Started Tutorial](tutorials/getting-started.md)
- [Investor Workflow Overview](explanation/investor-workflow.md)
- [GACS — Growth Area Composite Score](explanation/GACS_GUIDE.md)
- [Local Docker Setup](how-to-guides/local-dev.md)
- [Dev Container / Codespaces](how-to-guides/devcontainer.md)
- [Deploy to Render](how-to-guides/render-deploy.md)
- [API Keys Reference](reference/api-keys.md)
- [Data Sources Reference](reference/data-sources.md)
- [Financial KPIs](reference/financial-kpis.md)
- [UI Patterns](reference/ui-patterns.md)
- [GitHub Repository](https://github.com/paruff/prei)

## Technology Stack

- **Backend:** Django 6.0 with Python 3.14
- **Database:** SQLite (dev), PostgreSQL (Render prod)
- **Financial Libraries:** NumPy, pandas
- **Testing:** pytest, pytest-django
- **Code Quality:** ruff, mypy

## Repository

Source: [https://github.com/paruff/prei](https://github.com/paruff/prei)
