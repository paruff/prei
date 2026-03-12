## Phase 2.1 — Deal Analyzer Unit Tests (`test_deal_analyzer.py`)

### User Story
As a developer, I want comprehensive tests for all deal-analyzer KPI functions so that boundary conditions are documented and regressions are caught in CI.

### Background
The following functions already exist in `investor_app/finance/utils.py` but have **no dedicated boundary tests**:

| Function | Description |
|----------|-------------|
| `noi(monthly_income, monthly_expenses)` | Net Operating Income |
| `cap_rate(annual_noi, purchase_price)` | Capitalization Rate |
| `cash_on_cash(annual_cash_flow, total_cash_invested)` | Cash-on-Cash Return |
| `dscr(annual_noi, annual_debt_service)` | Debt Service Coverage Ratio |
| `irr(cashflows)` | Internal Rate of Return |
| `calculate_monthly_mortgage(...)` | Monthly mortgage payment |
| `calculate_break_even_rent(...)` | Break-even monthly rent |
| `calculate_roi_components(...)` | Full ROI breakdown |
| `calculate_flip_strategy(...)` | Flip deal KPIs |
| `calculate_rental_strategy(...)` | Rental deal KPIs |

Existing coverage lives in `core/tests/test_finance_utils.py` but does **not** cover zero-denominator, negative, and very large value paths.

### Acceptance Criteria
- [ ] Create `core/tests/test_deal_analyzer.py`
- [ ] For each function listed above, tests must cover:
  - **Happy path** — typical realistic inputs, assert expected output within tolerance
  - **Zero denominator** — e.g., `cap_rate(Decimal("1000"), Decimal("0"))` should return `Decimal("0")` (not raise)
  - **Negative inputs** — e.g., negative cash flow, negative NOI
  - **Very large values** — e.g., `purchase_price = Decimal("999999999.99")`
- [ ] `irr` test: wrap in `try/except` to confirm safe fallback when cashflows have no real solution
- [ ] All assertions use `pytest.approx` or compare `Decimal` values within a small tolerance
- [ ] Test file passes `ruff check` with zero violations

### Files to Change
| File | Action |
|------|--------|
| `core/tests/test_deal_analyzer.py` | **Create** |
| `investor_app/finance/utils.py` | **Edit** (if any function raises instead of returning `0` on zero-denominator — fix to return `Decimal("0")`) |

### Implementation Notes
- Import pattern: `from investor_app.finance.utils import noi, cap_rate, ...`
- Use `Decimal` for all inputs; never `float`
- Follow patterns in `core/tests/test_finance_utils.py`
- Use `pytest.mark.parametrize` where input/output pairs are natural

### Definition of Done
- `pytest core/tests/test_deal_analyzer.py -v` passes (all green)
- `ruff check core/tests/test_deal_analyzer.py` passes
- Zero-denominator paths confirmed to return `Decimal("0")` not raise

### Labels
`test` `phase-2` `backend`
