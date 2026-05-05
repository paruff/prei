# API Surface — prei

> Auto-maintained by `@docs-agent`. Updated whenever `core/services/` or `investor_app/finance/utils.py` changes.
> DORA AI Cap 3: This document is loaded as context before every code generation session.
> Last updated: 2026-05-05

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
