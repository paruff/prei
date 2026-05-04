# API Surface — prei

> Auto-maintained by `@docs-agent`. Updated whenever `core/services/` or `investor_app/finance/utils.py` changes.
> DORA AI Cap 3: This document is loaded as context before every code generation session.
> Last updated: 2026-05-04

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

### [service_module].[function_name](params)

**Purpose:** [PLACEHOLDER]
**Parameters:** [PLACEHOLDER]
**Returns:** [PLACEHOLDER]
**Side effects:** [PLACEHOLDER]
**Error cases:** [PLACEHOLDER]
**Example:**

```python
# [PLACEHOLDER]
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
