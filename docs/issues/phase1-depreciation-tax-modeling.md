## Phase 1 — Depreciation & Tax Modeling (`finance/utils.py`)

> **Revised Phase:** 1 (promoted from "not in plan")
> **Strategy context:** [`docs/PRODUCT_STRATEGY.md`](../PRODUCT_STRATEGY.md) · Tracking issue: #TRACKING
>
> This is the single biggest missing feature for sophisticated passive investors.
> See §3 of the product strategy doc.

**Suggested model:** GPT-4.1
**Django version:** Django 4.2 LTS
**Task type:** finance utils functions
**Files to edit:** `investor_app/finance/utils.py`, `tests/test_tax_analysis.py` (new)
**Reference file:** `investor_app/finance/utils.py` (existing IRR/CoC pattern)
**Do not:** Add Django model imports to `finance/utils.py` — all inputs must be plain Python types.
**Do not:** Use `float` for currency — use `Decimal` throughout; convert to `float` only for numpy calls, then back to `Decimal`.

### User Story

As a passive real estate investor, I want to see the depreciation schedule and after-tax cash flow
for a rental property so that I can compare my true after-tax return against alternative investments
like index funds.

### Background

The IRS allows 27.5-year straight-line depreciation on residential rental property. For a $300K
property with $50K land value, that's ~$9,100/year in paper loss that can shelter taxable income
without any actual cash outflow. The current `irr()` function in `finance/utils.py` returns a
pre-tax IRR, which significantly understates the benefit of real estate investing for most
taxpayers.

**Current state:**
- `irr(cash_flows)` exists — returns pre-tax
- `compute_analysis_for_property()` calculates NOI, CoC, Cap Rate — all pre-tax
- No depreciation function exists
- No after-tax cash flow function exists

### Acceptance Criteria

- [ ] `annual_depreciation(purchase_price: Decimal, land_value: Decimal, holding_years: int = 27) -> Decimal`
  - Uses 27.5-year straight-line: `(purchase_price - land_value) / Decimal("27.5")`
  - Raises `ValueError` if `land_value >= purchase_price`
  - Raises `ValueError` if `purchase_price <= 0` or `land_value < 0`
  - Returns `Decimal("0")` for years beyond the schedule

- [ ] `after_tax_cash_flow(noi: Decimal, annual_debt_service: Decimal, annual_depreciation: Decimal, marginal_tax_rate: Decimal) -> Decimal`
  - Formula: `(NOI - debt_service) + (depreciation × tax_rate)`
  - The depreciation tax shield is added back as cash benefit
  - Guards against `marginal_tax_rate` outside `[0, 1]` range (raises `ValueError`)

- [ ] `after_tax_irr(cash_flows: list[Decimal], depreciation_schedule: list[Decimal], marginal_tax_rate: Decimal) -> Decimal`
  - Adjusts each period's cash flow by the depreciation tax shield
  - Wraps `numpy_financial.irr()` in try/except with `Decimal("0")` fallback and logging
  - Returns `Decimal` (not `float`)

- [ ] `depreciation_recapture_tax(accumulated_depreciation: Decimal, recapture_rate: Decimal = Decimal("0.25")) -> Decimal`
  - Used in exit/sale proceeds calculation
  - `recapture_rate` defaults to 25% (IRS Section 1250 rate)

- [ ] All functions have Google-style docstrings and type hints
- [ ] `tests/test_tax_analysis.py` covers:
  - [ ] Boundary: zero land value, land value = purchase price (should raise)
  - [ ] Boundary: purchase price = 0 (should raise)
  - [ ] Boundary: very large values (e.g., $10M property)
  - [ ] Negative: marginal tax rate outside [0, 1] (should raise)
  - [ ] Zero tax rate produces same after-tax as pre-tax
  - [ ] Depreciation recapture at 25%

### Architecture Check

- All functions are pure Python — no Django imports
- `Decimal` used for all inputs/outputs; float only inside numpy-financial calls
- Functions live in `investor_app/finance/utils.py`
- Tests in `tests/test_tax_analysis.py` (or `tests/finance/test_tax_analysis.py` if test directory is nested)

### Notes

- Do **not** implement cost segregation or PAL rules in this issue — those are follow-on
- Land value is typically 10–25% of purchase price in most US markets; expose as a parameter, not hardcoded
- The `marginal_tax_rate` should be read from `settings.DEFAULT_MARGINAL_TAX_RATE` when called from services (but the function itself takes it as a parameter)
