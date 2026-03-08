## Phase 4.1 — Portfolio What-If Scenario Modeling

### User Story
As an advanced investor, I want to model multiple "what-if" scenarios for my portfolio — changing assumptions like vacancy rate, interest rate, or purchase price — so that I can compare outcomes before committing capital.

### Background
- `core/services/portfolio.py` has `aggregate_portfolio(user)` and (after Phase 2.5) `monthly_income_series`
- `compute_analysis_for_property` in `investor_app/finance/utils.py` returns `InvestmentAnalysis`
- `templates/portfolio_dashboard.html` is the target template

### Acceptance Criteria
- [ ] Add to `core/services/portfolio.py`:
  - `run_scenario(user, overrides: dict) -> dict`  
    — applies `overrides` (keys: `vacancy_rate`, `interest_rate`, `purchase_price_delta_pct`) to all user properties and returns the resulting aggregate KPIs (`total_noi`, `avg_cap_rate`, `avg_coc`)
  - `compare_scenarios(user, scenarios: list[dict]) -> list[dict]`  
    — calls `run_scenario` for each dict in `scenarios`; returns a list of `{"label": str, **kpis}` dicts; `label` comes from `scenario.get("label", "Scenario N")`
- [ ] Unit tests in `core/tests/test_portfolio_scenarios.py` (extend or create):
  - `run_scenario` with `vacancy_rate = 0.5` → NOI lower than baseline
  - `run_scenario` with `purchase_price_delta_pct = -10` → cap rate higher than baseline
  - `compare_scenarios` with two named scenarios → list of two dicts with correct labels
  - User with no properties → returns zero KPIs without error
  - Divide-by-zero guard when `purchase_price` becomes zero after delta
- [ ] Add a "Scenarios" section to `templates/portfolio_dashboard.html`:
  - Form to input up to 3 scenario overrides (vacancy %, interest rate %, price change %)
  - Display results in a comparison table
- [ ] POST handler in `core/views_portfolio.py` or new view to run scenario and return context

### Files to Change
| File | Action |
|------|--------|
| `core/services/portfolio.py` | **Edit** — add `run_scenario`, `compare_scenarios` |
| `core/tests/test_portfolio_scenarios.py` | **Create** (or **Edit**) |
| `templates/portfolio_dashboard.html` | **Edit** — add scenarios form + comparison table |
| `core/views_portfolio.py` | **Edit** — handle POST for scenario modeling |
| `core/urls.py` | **Edit** — add URL for scenario POST if needed |

### Implementation Notes
- `overrides` dict is shallow — only the keys present are overridden; missing keys use `settings.FINANCE_DEFAULTS`
- Use `Decimal` for all override values; convert from form strings with `Decimal(str(...))`
- Guard all divides; return `Decimal("0")` on zero-denominator
- Do not persist scenario results to the DB; scenarios are ephemeral computations

### Definition of Done
- `pytest core/tests/test_portfolio_scenarios.py -v` passes
- `ruff check core/services/portfolio.py` passes
- Portfolio dashboard shows comparison table for at least 2 scenarios (screenshot in PR)

### Labels
`enhancement` `phase-4` `backend` `frontend`
