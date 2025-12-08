# Reference Documentation

This section provides technical reference material for the Real Estate Investor application, including data models, API specifications, configuration options, and financial calculations.

## Data Models

- [Property Model](models/property.md) — Property entity and attributes
- [Rental Income Model](models/rental-income.md) — Rental income tracking
- [Operating Expense Model](models/operating-expense.md) — Property expense management
- [Transaction Model](models/transaction.md) — Financial transaction records
- [Investment Analysis Model](models/investment-analysis.md) — Calculated KPI storage

## Financial Calculations

- [Financial KPIs Reference](financial-kpis.md) — Detailed explanation of all financial metrics
- [NOI Calculation](financial-kpis.md#net-operating-income-noi) — Net Operating Income
- [Cap Rate Calculation](financial-kpis.md#capitalization-rate-cap-rate) — Capitalization Rate
- [Cash-on-Cash Return](financial-kpis.md#cash-on-cash-return) — Annual cash return
- [IRR Calculation](financial-kpis.md#internal-rate-of-return-irr) — Internal Rate of Return
- [DSCR Calculation](financial-kpis.md#debt-service-coverage-ratio-dscr) — Debt Service Coverage Ratio

## API Reference

- [Django Admin Interface](api/admin.md) — Using the built-in admin
- [REST API Endpoints](api/endpoints.md) — HTTP API reference (if implemented)
- [Management Commands](api/management-commands.md) — CLI commands

## Configuration

- [Environment Variables](configuration/environment-variables.md) — Configuration options
- [Database Settings](configuration/database.md) — Database configuration
- [Financial Defaults](configuration/financial-defaults.md) — Default rates and assumptions
- [Static Files](configuration/static-files.md) — Static asset management

## Testing

- [Test Structure](testing/test-structure.md) — Test organization and conventions
- [Test Fixtures](testing/fixtures.md) — Shared test data and utilities
- [Test Configuration](testing/configuration.md) — pytest and Django test settings

## CI/CD

- [CI Configuration](ci-configuration.md) — GitHub Actions workflows
- [DORA Metrics](dora-metrics.md) — Deployment and quality metrics logging

## Dependencies

- [Python Dependencies](dependencies/python.md) — Required Python packages
- [Database Requirements](dependencies/database.md) — PostgreSQL and SQLite support
- [Development Tools](dependencies/development.md) — Linting, formatting, and type checking tools
