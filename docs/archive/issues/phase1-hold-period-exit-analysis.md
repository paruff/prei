## Phase 1 — Hold Period & Exit Analysis (`finance/utils.py`)

> **Revised Phase:** 1 (promoted from "not in plan")
> **Strategy context:** [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md)
> · Tracking issue: open `docs/issues/tracking-product-strategy-pivot.md` as a GitHub issue
> and replace this line with the actual issue number once created.
>
> Every passive investor thinks in 5/7/10-year windows. The current model is static.
> See §4 of the product strategy doc.

**Suggested model:** GPT-4.1
**Django version:** Django 4.2 LTS
**Task type:** finance utils functions
**Files to edit:** `investor_app/finance/utils.py`, `tests/test_hold_period.py` (new)
**Reference file:** `investor_app/finance/utils.py` (existing IRR/projection pattern)
**Depends on:** Phase 1 Depreciation & Tax Modeling issue (for `annual_depreciation` and `depreciation_recapture_tax`)
**Do not:** Add Django model imports to `finance/utils.py`
**Do not:** Use `float` for currency

### User Story

As a passive real estate investor, I want to see a year-by-year projection over a 10-year hold
period — including cash flow, equity build-up, and net sale proceeds — so that I can compare
total return against a stock portfolio alternative without building my own Excel model.

### Background

Passive investors evaluate deals on total return over a hold period, not just today's cap rate.
The key drivers are: rental income growth, expense inflation, mortgage paydown (equity), property
appreciation, and net sale proceeds after taxes and closing costs. None of these time-series
calculations currently exist in `finance/utils.py`.

**Current state:**
- `calculate_monthly_mortgage()` exists (starting point)
- `irr()` exists (pre-tax; will be supplemented by `after_tax_irr` from depreciation issue)
- No year-by-year projection function exists
- No sale proceeds calculator exists

### Acceptance Criteria

- [ ] `project_annual_cash_flows(gross_rent_year1: Decimal, operating_expense_year1: Decimal, annual_debt_service: Decimal, rent_growth_rate: Decimal, expense_growth_rate: Decimal, hold_years: int) -> list[Decimal]`
  - Returns list of annual after-debt-service cash flows for each year of hold period
  - `gross_rent_year1` grows at `rent_growth_rate` each year: `gross_rent_year1 × (1 + rent_growth_rate)^year`
  - `operating_expense_year1` grows at `expense_growth_rate` each year: `operating_expense_year1 × (1 + expense_growth_rate)^year`
  - Annual NOI per year = `gross_rent × (1 + rent_growth_rate)^year - operating_expense × (1 + expense_growth_rate)^year`
  - Annual cash flow = NOI − `annual_debt_service` (debt service is constant for fixed-rate loans)
  - Raises `ValueError` if `hold_years < 1` or `hold_years > 50`
  - Raises `ValueError` if any rate is outside `[-0.5, 0.5]` (sanity guard)

- [ ] `project_property_value(purchase_price: Decimal, appreciation_rate: Decimal, hold_years: int) -> Decimal`
  - Returns projected property value at end of hold period
  - Supports conservative/base/optimistic by varying `appreciation_rate`
  - Raises `ValueError` if `appreciation_rate < -1`

- [ ] `net_sale_proceeds(sale_price: Decimal, original_purchase_price: Decimal, outstanding_loan_balance: Decimal, accumulated_depreciation: Decimal, agent_commission_rate: Decimal = Decimal("0.06"), closing_cost_rate: Decimal = Decimal("0.01"), long_term_cg_rate: Decimal = Decimal("0.15"), depreciation_recapture_rate: Decimal = Decimal("0.25")) -> Decimal`
  - Returns net cash to investor after: agent commissions, closing costs, capital gains tax, depreciation recapture
  - Capital gain = `sale_price - original_purchase_price`
  - Depreciation recapture applied to `accumulated_depreciation` at `depreciation_recapture_rate`
  - Guards against negative `outstanding_loan_balance`

- [ ] `total_return_summary(purchase_price: Decimal, down_payment: Decimal, annual_cash_flows: list[Decimal], net_sale_proceeds: Decimal) -> dict`
  - Returns dict with keys: `total_cash_flow`, `net_sale_proceeds`, `total_return`, `total_return_on_equity`, `annualized_irr`
  - `annualized_irr` computed via `irr()` from full cash flow series (down_payment as negative year-0, then annual flows, then flows[-1] + net_sale_proceeds in final year)

- [ ] All functions have Google-style docstrings and type hints
- [ ] `tests/test_hold_period.py` covers:
  - [ ] Boundary: `hold_years = 1`, `hold_years = 30`
  - [ ] Boundary: `hold_years = 0` (should raise)
  - [ ] Zero appreciation rate (value unchanged)
  - [ ] Zero rent growth rate (flat cash flows)
  - [ ] Negative appreciation (market downturn scenario)
  - [ ] Net sale proceeds when property declined in value (no capital gains tax, only recapture)
  - [ ] Very large values ($10M property)

### Architecture Check

- All functions are pure Python — no Django imports
- `Decimal` used for all inputs/outputs
- Functions live in `investor_app/finance/utils.py`

### Notes

- Typical conservative/base/optimistic appreciation rates for US residential: 0%, 3%, 5%
- Typical rent growth rate: 3% per year
- Typical expense growth rate (inflation-linked): 2–3% per year
- Long-term capital gains rate (federal): 0%, 15%, or 20% depending on income; default 15% is reasonable for middle-income investors
- Read default rates from `settings` where possible, but accept as function parameters
