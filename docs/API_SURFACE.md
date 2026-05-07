# API Surface — prei

> Auto-maintained by `@docs-agent`. Updated whenever `core/services/` or `investor_app/finance/utils.py` changes.
> DORA AI Cap 3: This document is loaded as context before every code generation session.
> Last updated: 2026-05-06 (added one_percent_rule, gross_rent_multiplier, score_listing_v2)

-----

## Instructions for @docs-agent

When updating this file:

1. Scan all files in `core/services/` and `investor_app/finance/` for public functions
1. Document each using the format below
1. Remove any entries for functions that no longer exist
1. Add a "Last updated" timestamp at the top

-----

## Services

<!-- @docs-agent: populate from core/services/ -->

### `market_data.refresh_market_snapshot(zip_code)`

**Purpose:** Orchestrate all four market-data adapters (crime, schools, rents, comps) for a ZIP
code and upsert the results into `MarketSnapshot`. Returns the saved instance. Adapter failures
are caught, logged at ERROR level, and replaced with `Decimal("0")` so the snapshot is always
persisted.

**Parameters:**
- `zip_code: str` — Five-digit (or formatted) ZIP code to refresh.

**Returns:** `core.models.MarketSnapshot` — The upserted snapshot instance.

**Side effects:**
- Reads one `core.models.Listing` for the ZIP (used to compute `rent_index` and `price_trend`).
- Writes/updates one `core.models.MarketSnapshot` row via `update_or_create`.

**Error cases:**
- Each adapter is wrapped in `try/except`; if an adapter raises, its field defaults to
  `Decimal("0")` and an ERROR is logged — the snapshot is still saved.
- No exception is propagated to the caller.

**Example:**

```python
from core.services.market_data import refresh_market_snapshot

snap = refresh_market_snapshot("78701")
# → MarketSnapshot(zip_code="78701", crime_score=Decimal("2.5"),
#                  school_rating=Decimal("8.0"), rent_index=Decimal("1800.00"),
#                  price_trend=Decimal("0.0333"))
```

---

### `cma.find_undervalued(listings, threshold)`

**Purpose:** Return listings whose price-per-sq-ft is below `median_ppsf * threshold`.
**Parameters:**
- `listings: Iterable[Listing]` — Candidate listings.
- `threshold: Decimal` — Fraction of median PPSF below which a listing is flagged (default `0.85`).

**Returns:** `list[tuple[Listing, Decimal]]` — Pairs of (listing, ppsf) for undervalued properties.
**Side effects:** None (pure calculation; no DB writes)
**Error cases:** Returns empty list when no listings have `sq_ft > 0`.
**Example:**

```python
from decimal import Decimal
from core.services.cma import find_undervalued

undervalued = find_undervalued(Listing.objects.all(), threshold=Decimal("0.90"))
```

---

### `portfolio.aggregate_portfolio(user)`

**Purpose:** Aggregate NOI, cap rate, and cash-on-cash return across a user's portfolio.
**Parameters:**
- `user` — Django `User` instance.

**Returns:** `dict` with keys `total_noi`, `avg_cap_rate`, `avg_coc` (all `Decimal`).
**Side effects:** Reads `Property`, `RentalIncome`, and `OperatingExpense` rows for the user.
**Error cases:** Returns zeroed dict when the user has no properties.
**Example:**

```python
from core.services.portfolio import aggregate_portfolio

summary = aggregate_portfolio(request.user)
# → {"total_noi": Decimal("18000.00"), "avg_cap_rate": Decimal("0.06"),
#    "avg_coc": Decimal("0.12")}
```

-----

### `portfolio.monthly_income_series(user, months=12)`

**Purpose:** Return month-by-month gross income, expenses, and NOI for the last N calendar months.
**Parameters:**
- `user` — Django `User` instance.
- `months: int` — Number of trailing calendar months (default 12).

**Returns:** `list[dict]` with keys `{"month": "YYYY-MM", "gross_income": Decimal, "expenses": Decimal, "noi": Decimal}`, oldest first. Returns `[]` when the user has no properties.
**Side effects:** Reads `RentalIncome` and `OperatingExpense` rows for the user's properties.
**Error cases:** Raises `ValueError` when `months < 1`. Returns empty list when user has no properties.
**Example:**

```python
from core.services.portfolio import monthly_income_series

series = monthly_income_series(request.user, months=3)
# → [{"month": "2025-02", "gross_income": Decimal("1900"), "expenses": Decimal("300"), "noi": Decimal("1600")}, ...]
```

-----

### `portfolio.portfolio_trend_summary(user)`

**Purpose:** Return the percentage change in NOI and cap rate between the oldest and newest month in the 12-month series.
**Parameters:**
- `user` — Django `User` instance.

**Returns:** `dict` with keys `trend_noi` and `trend_cap_rate` (both `Decimal`, rounded to 2 d.p.). Returns zeroes when there is ≤ 1 month of data or when the oldest month has zero values.
**Side effects:** Reads `RentalIncome`, `OperatingExpense`, and `Property` rows for the user.
**Error cases:** Guards against divide-by-zero; always returns a valid dict.
**Example:**

```python
from core.services.portfolio import portfolio_trend_summary

trend = portfolio_trend_summary(request.user)
# → {"trend_noi": Decimal("5.26"), "trend_cap_rate": Decimal("5.26")}
```

-----

## Finance Utilities

> Module: `investor_app/finance/utils.py`
> All functions are pure (no DB access, no Django imports) and use `Decimal` for currency.

### `calculate_noi(gross_income, operating_expenses)`

**Purpose:** Calculate Net Operating Income (NOI = Gross Income − Operating Expenses).
**Parameters:**
- `gross_income: Decimal` — Total annual rental and other income from the property.
- `operating_expenses: Decimal` — Total annual operating expenses (excluding debt service).

**Returns:** `Decimal` — Net Operating Income.
**Side effects:** None (pure function)
**Error cases:** None.
**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import calculate_noi

noi = calculate_noi(Decimal("12000.00"), Decimal("3000.00"))
# → Decimal("9000.00")
```

---

### `calculate_cap_rate(annual_noi, property_value)`

**Purpose:** Calculate the Capitalization Rate (Cap Rate = NOI / Property Value).
**Parameters:**
- `annual_noi: Decimal` — Net Operating Income.
- `property_value: Decimal` — Current market value or purchase price of the property.

**Returns:** `Decimal` — Capitalization rate rounded to 4 decimal places (e.g., `Decimal("0.0600")` for 6%).
**Side effects:** None (pure function)
**Error cases:** Raises `ValueError` if `property_value` is zero.
**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import calculate_cap_rate

cap = calculate_cap_rate(Decimal("9000.00"), Decimal("150000.00"))
# → Decimal("0.0600")
```

---

### `calculate_cash_on_cash(annual_cash_flow, total_cash_invested)`

**Purpose:** Calculate Cash-on-Cash Return (CoC = Annual Cash Flow / Total Cash Invested).
**Parameters:**
- `annual_cash_flow: Decimal` — Annual pre-tax cash flow from the investment.
- `total_cash_invested: Decimal` — Total cash invested (down payment + closing costs).

**Returns:** `Decimal` — Cash-on-Cash return rounded to 4 decimal places (e.g., `Decimal("0.1500")` for 15%).
**Side effects:** None (pure function)
**Error cases:** Raises `ValueError` if `total_cash_invested` is zero.
**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import calculate_cash_on_cash

coc = calculate_cash_on_cash(Decimal("3000.00"), Decimal("20000.00"))
# → Decimal("0.1500")
```

---

### `calculate_irr(cash_flows)`

**Purpose:** Calculate the Internal Rate of Return (IRR) using `numpy-financial`.
**Parameters:**
- `cash_flows: Sequence[float | int | Decimal]` — Sequence of cash flows. The first value is typically negative (initial investment), followed by periodic returns. Accepts `int`, `float`, or `Decimal`; each value is coerced to `float` internally.

**Returns:** `Decimal` — IRR as a Decimal (e.g., `Decimal("0.0699")` for ~7%).
**Side effects:** None (pure function)
**Error cases:**
- Raises `ValueError` if fewer than 2 cash flows are supplied.
- Raises `ValueError` if the IRR cannot be computed (e.g., all non-negative flows).

**Example:**

```python
from investor_app.finance.utils import calculate_irr

irr = calculate_irr([-1000, 500, 600])
# → Decimal("0.0699")  (approximately)
```

---

### `project_annual_cash_flows(gross_rent_year1, operating_expense_year1, annual_debt_service, rent_growth_rate, expense_growth_rate, hold_years)`

**Purpose:** Project year-by-year after-debt-service cash flows over a hold period using compound growth rates for rent and expenses. Debt service is constant (fixed-rate mortgage assumption).

**Parameters:**
- `gross_rent_year1: Decimal` — Gross rental income in year 1 (must be ≥ 0).
- `operating_expense_year1: Decimal` — Operating expenses in year 1 (must be ≥ 0).
- `annual_debt_service: Decimal` — Fixed annual mortgage payment (principal + interest; must be ≥ 0).
- `rent_growth_rate: Decimal` — Annual rent growth rate as a decimal (e.g., `Decimal("0.03")` for 3%). Must be in `[-0.5, 0.5]`.
- `expense_growth_rate: Decimal` — Annual expense growth rate as a decimal. Must be in `[-0.5, 0.5]`.
- `hold_years: int` — Number of years in the hold period. Must be in `[1, 50]`.

**Returns:** `list[Decimal]` — Annual after-debt-service cash flows, one entry per year (`len == hold_years`). Negative values indicate years where debt service exceeds NOI.
**Side effects:** None (pure function)
**Error cases:**
- Raises `ValueError` if `gross_rent_year1`, `operating_expense_year1`, or `annual_debt_service` is negative.
- Raises `ValueError` if `hold_years` is outside `[1, 50]`.
- Raises `ValueError` if `rent_growth_rate` or `expense_growth_rate` is outside `[-0.5, 0.5]`.

**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import project_annual_cash_flows

flows = project_annual_cash_flows(
    Decimal("36000"), Decimal("12000"), Decimal("18000"),
    rent_growth_rate=Decimal("0.03"), expense_growth_rate=Decimal("0.02"),
    hold_years=5,
)
# → [Decimal("6000"), Decimal("6760.00"), ...]  (5 entries)
```

---

### `project_property_value(purchase_price, appreciation_rate, hold_years)`

**Purpose:** Project the market value of a property at the end of a hold period using compound annual appreciation. Supports conservative / base / optimistic scenarios by varying `appreciation_rate`.

**Parameters:**
- `purchase_price: Decimal` — Original purchase price of the property (must be > 0).
- `appreciation_rate: Decimal` — Expected annual appreciation rate as a decimal (e.g., `Decimal("0.03")` for 3%). Must be >= `-1`.
- `hold_years: int` — Number of years to project forward. Must be in `[1, 50]`.

**Returns:** `Decimal` — Projected property value at end of hold period.
**Side effects:** None (pure function)
**Error cases:**
- Raises `ValueError` if `purchase_price` ≤ 0.
- Raises `ValueError` if `appreciation_rate` < -1.
- Raises `ValueError` if `hold_years` is outside `[1, 50]`.

**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import project_property_value

value = project_property_value(Decimal("300000"), Decimal("0.03"), 10)
# → Decimal("403175....")  (approximately $403,176)
```

---

### `net_sale_proceeds(sale_price, original_purchase_price, outstanding_loan_balance, accumulated_depreciation, agent_commission_rate, closing_cost_rate, long_term_cg_rate, depreciation_recapture_rate)`

**Purpose:** Calculate net cash to investor after agent commissions, closing costs, loan payoff, long-term capital gains tax (clamped to zero on a loss sale), and IRS Section 1250 depreciation recapture.

**Parameters:**
- `sale_price: Decimal` — Gross sale price of the property.
- `original_purchase_price: Decimal` — Price paid at acquisition.
- `outstanding_loan_balance: Decimal` — Remaining mortgage balance at time of sale (must be ≥ 0).
- `accumulated_depreciation: Decimal` — Total depreciation taken over the holding period (must be ≥ 0).
- `agent_commission_rate: Decimal` — Broker commission as a decimal (default `Decimal("0.06")` = 6%).
- `closing_cost_rate: Decimal` — Seller's closing costs as a decimal (default `Decimal("0.01")` = 1%).
- `long_term_cg_rate: Decimal` — Federal long-term capital gains tax rate (default `Decimal("0.15")` = 15%).
- `depreciation_recapture_rate: Decimal` — IRS Section 1250 recapture rate (default `Decimal("0.25")` = 25%).

**Returns:** `Decimal` — Net cash proceeds to investor (may be negative if costs exceed gross proceeds).
**Side effects:** None (pure function)
**Error cases:**
- Raises `ValueError` if `outstanding_loan_balance` < 0.
- Raises `ValueError` if `accumulated_depreciation` < 0.
- Raises `ValueError` if any rate parameter is outside `[0, 1]`.

**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import net_sale_proceeds

proceeds = net_sale_proceeds(
    sale_price=Decimal("400000"),
    original_purchase_price=Decimal("300000"),
    outstanding_loan_balance=Decimal("200000"),
    accumulated_depreciation=Decimal("45000"),
)
# → Decimal("145750")
```

---

### `one_percent_rule(monthly_rent, purchase_price)`

**Purpose:** Quick pass/fail filter — returns `True` if monthly rent is ≥ 1% of purchase price.
**Parameters:**
- `monthly_rent: Decimal` — Expected gross monthly rental income.
- `purchase_price: Decimal` — Total purchase price of the property. Must be > 0.

**Returns:** `bool` — `True` when `monthly_rent / purchase_price >= 0.01`.
**Side effects:** None (pure function)
**Error cases:** Raises `ValueError` if `purchase_price` ≤ 0.
**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import one_percent_rule

passes = one_percent_rule(Decimal("2500"), Decimal("250000"))
# → True  (2500 / 250000 == 0.01, exactly at threshold)
```

---

### `gross_rent_multiplier(purchase_price, annual_rent)`

**Purpose:** Calculate the Gross Rent Multiplier (GRM = Purchase Price / Annual Rent). Lower is better. Benchmark: < 10 excellent, 10–15 good, 15–20 fair, > 20 poor.
**Parameters:**
- `purchase_price: Decimal` — Total purchase price of the property.
- `annual_rent: Decimal` — Expected gross annual rental income. Must be > 0.

**Returns:** `Decimal` — GRM value.
**Side effects:** None (pure function)
**Error cases:** Raises `ValueError` if `annual_rent` ≤ 0.
**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import gross_rent_multiplier

grm = gross_rent_multiplier(Decimal("200000"), Decimal("20000"))
# → Decimal("10")
```

---

### `score_listing_v2(purchase_price, monthly_rent, annual_noi, local_market_cap_rate, down_payment, annual_debt_service)`

**Purpose:** Compute an investor-grade multi-signal underwriting composite score (0–100) from four weighted signals: 1% Rule (20%), cap rate vs. local market (30%), Cash-on-Cash Year 1 (30%), GRM heuristic (20%). A deal failing the 1% Rule has its score capped at 40.
**Parameters:**
- `purchase_price: Decimal` — Total purchase price. Must be > 0.
- `monthly_rent: Decimal` — Expected gross monthly rental income. Must be > 0.
- `annual_noi: Decimal` — Net Operating Income for Year 1. Must be > 0.
- `local_market_cap_rate: Decimal` — Prevailing local market cap rate as a decimal (e.g., `Decimal("0.06")` for 6%). Sourced from `MarketSnapshot` at the service layer. Must be > 0.
- `down_payment: Decimal` — Cash down payment (total cash invested). Must be > 0.
- `annual_debt_service: Decimal` — Total annual principal + interest payments. Must be > 0.

**Returns:** `ScoreV2Result` (TypedDict) with keys:
- `one_percent_rule_pass` (`bool`): `True` if `monthly_rent / purchase_price >= 0.01`.
- `grm` (`Decimal`): Gross Rent Multiplier.
- `cap_rate` (`Decimal`): `annual_noi / purchase_price`.
- `cap_rate_vs_market` (`Decimal`): `cap_rate − local_market_cap_rate`; positive = above market.
- `coc_year1` (`Decimal`): `(annual_noi − annual_debt_service) / down_payment`.
- `composite_score` (`Decimal`): Weighted composite in [0, 100]; capped at 40 when 1% rule fails.

**Side effects:** None (pure function)
**Error cases:** Raises `ValueError` if any input is ≤ 0.
**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import score_listing_v2

result = score_listing_v2(
    purchase_price=Decimal("250000"),
    monthly_rent=Decimal("2500"),
    annual_noi=Decimal("18000"),
    local_market_cap_rate=Decimal("0.06"),
    down_payment=Decimal("62500"),
    annual_debt_service=Decimal("14400"),
)
# → {"one_percent_rule_pass": True, "grm": Decimal("8.33..."), "cap_rate": Decimal("0.072"),
#    "cap_rate_vs_market": Decimal("0.012"), "coc_year1": Decimal("0.0576"),
#    "composite_score": Decimal("55.84...")}
```


**Purpose:** Aggregate hold-period results into a total-return summary dict. IRR is computed over the full cash-flow series (year-0 equity outflow, annual flows, exit-year flows + net sale proceeds).

**Parameters:**
- `purchase_price: Decimal` — Original acquisition price. Included in the returned summary as `"purchase_price"` for caller convenience.
- `down_payment: Decimal` — Equity invested at purchase; used as the year-0 outflow in the IRR calculation (must be ≥ 0).
- `annual_cash_flows: list[Decimal]` — Year-by-year cash flows from `project_annual_cash_flows()` (must be non-empty).
- `net_sale_proceeds_amount: Decimal` — Net sale proceeds from `net_sale_proceeds()`.

**Returns:** `dict[str, Decimal]` with keys:
- `purchase_price` (`Decimal`): The `purchase_price` argument.
- `total_cash_flow` (`Decimal`): Sum of `annual_cash_flows`.
- `net_sale_proceeds` (`Decimal`): The `net_sale_proceeds_amount` argument.
- `total_return` (`Decimal`): `total_cash_flow + net_sale_proceeds`.
- `total_return_on_equity` (`Decimal`): `total_return / down_payment`, or `Decimal("0")` if `down_payment` is zero.
- `annualized_irr` (`Decimal`): IRR over the full cash-flow series.

**Side effects:** None (pure function)
**Error cases:**
- Raises `ValueError` if `annual_cash_flows` is empty.
- Raises `ValueError` if `down_payment` < 0.

**Example:**

```python
from decimal import Decimal
from investor_app.finance.utils import total_return_summary

summary = total_return_summary(
    purchase_price=Decimal("300000"),
    down_payment=Decimal("60000"),
    annual_cash_flows=[Decimal("6000")] * 10,
    net_sale_proceeds_amount=Decimal("120000"),
)
# → {"purchase_price": Decimal("300000"), "total_cash_flow": Decimal("60000"),
#    "net_sale_proceeds": Decimal("120000"), "total_return": Decimal("180000"),
#    "total_return_on_equity": Decimal("3"), "annualized_irr": Decimal("...")}
```
