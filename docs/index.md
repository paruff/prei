# Real Estate Investor — Property Analytics

Welcome to the documentation for the Real Estate Investor application, a Django-based web platform designed to analyze and track residential real estate investments.

## What is Real Estate Investor?

Real Estate Investor is a comprehensive property analytics tool that helps passive residential real estate investors make informed decisions by computing key performance indicators (KPIs) such as:

- **Cash-on-Cash Return** — Annual pre-tax cash flow divided by total cash invested
- **Capitalization Rate (Cap Rate)** — Net Operating Income divided by property value
- **Net Operating Income (NOI)** — Total income minus operating expenses
- **Internal Rate of Return (IRR)** — Time-weighted return on investment
- **Debt Service Coverage Ratio (DSCR)** — NOI divided by annual debt service

## Documentation Structure

This documentation follows the [Diátaxis framework](https://diataxis.fr/), organizing content into four distinct categories:

### 📚 [Tutorials](tutorials/getting-started.md)
Step-by-step lessons to help you get started with the application. Perfect for new users who want to learn by doing.

### 🛠️ [How-to Guides](how-to-guides/index.md)
Practical guides for accomplishing specific tasks. Use these when you know what you want to achieve.

### 📖 [Reference](reference/index.md)
Technical descriptions of the application's machinery. Consult this when you need detailed information about APIs, models, or configuration options.

### 💡 [Explanation](explanation/index.md)
Background material explaining design decisions, architecture, and the rationale behind key features.

## Quick Links

- [Getting Started Tutorial](tutorials/getting-started.md) — Set up and run your first analysis
- [Financial KPIs Reference](reference/financial-kpis.md) — Understanding the financial calculations
- [Architecture Overview](explanation/architecture.md) — System design and technology choices
- [GitHub Repository](https://github.com/paruff/prei) — Source code and issue tracking

## Technology Stack

- **Backend:** Django 4.2+ with Python 3.11+
- **Database:** PostgreSQL (with SQLite fallback for local development)
- **Financial Libraries:** NumPy, NumPy-Financial
- **Testing:** pytest, pytest-django, pytest-bdd
- **Code Quality:** ruff, black, mypy

## Getting Help

- Check the [How-to Guides](how-to-guides/index.md) for common tasks
- Review the [Reference documentation](reference/index.md) for detailed API information
- Visit the [GitHub Issues](https://github.com/paruff/prei/issues) page to report bugs or request features
