## Phase 2.5 — Monthly Trend Time-Series & Portfolio Summaries

### User Story
As an investor, I want to see how my portfolio's income and expenses have trended over the past 12 months so that I can spot problems and opportunities early.

### Background
- `Property`, `RentalIncome`, `OperatingExpense`, `Transaction` models exist in `core/models.py`
- `core/services/portfolio.py` has `aggregate_portfolio(user)` returning `total_noi`, `avg_cap_rate`, `avg_coc`
- No time-series aggregation exists today

### Acceptance Criteria
- [ ] Add to `core/services/portfolio.py`:
  - `monthly_income_series(user, months: int = 12) -> list[dict]`  
    Returns a list of `{"month": "YYYY-MM", "gross_income": Decimal, "expenses": Decimal, "noi": Decimal}` for the last `months` calendar months
  - `portfolio_trend_summary(user) -> dict`  
    Returns `{"trend_noi": Decimal, "trend_cap_rate": Decimal}` — the percentage change between the oldest and newest month in the 12-month series
- [ ] Unit tests in `core/tests/test_portfolio_scenarios.py`:
  - User with 12 months of rental income → correct month labels and income totals
  - User with no properties → empty list without error
  - `portfolio_trend_summary` with only one month → trend = `Decimal("0")` (no divide-by-zero)
  - Expenses with `frequency = "annual"` are correctly prorated to monthly
- [ ] Extend `templates/portfolio_dashboard.html` to show a simple text summary table of the 12-month series (no JS charting required for MVP)
- [ ] The `views_portfolio.py` view passes `monthly_series` and `trend_summary` to the template

### Files to Change
| File | Action |
|------|--------|
| `core/services/portfolio.py` | **Edit** — add `monthly_income_series` and `portfolio_trend_summary` |
| `core/tests/test_portfolio_scenarios.py` | **Create** |
| `templates/portfolio_dashboard.html` | **Edit** — add trend table |
| `core/views_portfolio.py` | **Edit** — add context keys |

### Implementation Notes
- Use `django.db.models.functions.TruncMonth` for grouping
- Use `Decimal` for all monetary values; guard all divisions
- `OperatingExpense.monthly_amount()` method already normalises frequency
- Import `aggregate_portfolio` for the summary; keep functions composable

### Definition of Done
- `pytest core/tests/test_portfolio_scenarios.py -v` passes
- `ruff check core/services/portfolio.py core/tests/test_portfolio_scenarios.py` passes
- Portfolio dashboard shows the 12-month trend table (screenshot in PR)

### Labels
`enhancement` `phase-2` `backend` `frontend`
