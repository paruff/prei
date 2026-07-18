# Design: Phase B — Financial Math Verification
# Written: 2026-07-18
# Status: Draft

---

## 1. Architecture

### 1.1 Reference Implementation (`tests/finance_reference.py`)

A standalone Python module with zero dependencies (no Django, no numpy). Each function
is implemented independently from the production code — a second implementation of the
same formula, written from the mathematical derivation.

```
tests/finance_reference.py
  ├── ref_noi(income, expenses) → Decimal
  ├── ref_cap_rate(noi, price) → Decimal
  ├── ref_cash_on_cash(cash_flow, invested) → Decimal
  ├── ref_dscr(noi, debt_service) → Decimal
  ├── ref_monthly_mortgage(P, r, n) → Decimal
  ├── ref_one_percent_rule(rent, price) → bool
  ├── ref_gross_rent_multiplier(price, rent) → Decimal
  └── ref_annual_depreciation(purchase, land) → Decimal
```

### 1.2 Test Suite (`tests/test_finance_math.py`)

Parameterized tests using `@pytest.mark.parametrize`. Each test:
1. Computes result via production function
2. Computes result via reference function
3. Asserts `abs(prod - ref) < tolerance`

Edge case matrix:

```
                 zero    negative   extreme   precision
noi               ✓        ✓          ✓          ✓
cap_rate          ✓        ✓          ✓          ✓
cash_on_cash      ✓        ✓          ✓          ✓
dscr              ✓        ✓          ✓
mortgage          ✓        ✓          ✓          ✓
one_percent       ✓                               ✓
grm               ✓        ✓          ✓
depreciation      ✓        ✓
```

### 1.3 CI Gate

Add a new job to `ci-quality.yml`:

```yaml
finance-math:
  name: "💰 Financial Math"
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v7
    - uses: ./.github/actions/python-setup
    - name: Install deps
      run: pip install -r requirements.txt
    - name: Run financial math verification
      run: python -m pytest tests/test_finance_math.py -v --tb=short
```

Add to `pr-gates-pass` needs list.

### 1.4 Makefile Target

```makefile
test-finance-math:
	python -m pytest tests/test_finance_math.py -v --tb=short
```

### 1.5 Docstring Format

Each function gets a docstring with:
1. Mathematical formula in plain math notation
2. Variable definitions
3. Reference source (e.g., "per NAR Commercial Real Estate Standards")

---

## 2. Edge Case Definitions

| Category | Definition | Examples |
|---|---|---|
| Zero | Parameter is Decimal("0") | price=0, rent=0, rate=0 |
| Negative | Parameter is negative | NOI=-1000, cash_flow=-500 |
| Extreme | Parameter is 10x or 100x normal | price=10000000, rate=0.20 |
| Precision | Result requires 10+ decimal places | rate=0.0475/12, 30-year loan |
| Boundary | Parameter at formula boundary | rent = price * 0.01 (exact 1%) |
| Currency | Decimal precision with 2dp inputs | price=99999.99, land=5000.01 |

---

## 3. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Reference implementation replicates the same bug as production | Validate reference against at least one hand-calculated example per function |
| Decimal precision differences | Use `Decimal("0.01")` tolerance, not `abs` floating point |
| CI timeout (pip install) | Finance-math gate needs Django for tests, but tests shouldn't use the DB |
| New functions added that aren't verified | `make test-finance-math` lists covered functions in output |
