# Specification: Phase B — Financial Math Verification
# Written: 2026-07-18
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Phase B proves every core KPI calculation is mathematically correct. For a real
estate investment platform handling money decisions, an incorrect IRR or cap rate
is an existential bug. Each function gets: a reference implementation, a documented
formula derivation, and a parameterized test suite with ≥10 edge cases.

---

## 1. Problem Statement

**Current state:**
- 40+ financial functions in `investor_app/finance/utils.py` and `core/services/scoring.py`
- Existing tests cover happy paths only (`tests/test_finance_utils.py` has 20 tests total)
- No reference implementation to validate against
- Formula derivations are in developer heads, not docstrings
- Edge cases (zero, negative, extreme values, precision) are untested
- No CI gate blocks merging if a KPI calculation changes incorrectly

**Desired state:**
- Reference implementation for core KPIs that serves as ground truth
- Parameterized test suite with 50+ edge cases across 8 core functions
- CI gate that fails on any KPI deviation from reference
- Every function has its mathematical formula in the docstring

---

## 2. Scope

### Core KPI Functions (must-verify)

| Function | Formula | Edge Cases |
|---|---|---|
| `noi()` | `monthly_income - monthly_expenses` | Zero income, zero expenses, negative NOI |
| `cap_rate()` | `annual_noi / purchase_price` | Zero price, zero NOI, decimal precision |
| `cash_on_cash()` | `annual_cash_flow / total_cash_invested` | Zero investment, negative cash flow |
| `dscr()` | `annual_noi / annual_debt_service` | Zero debt service, negative NOI |
| `calculate_monthly_mortgage()` | `P * r * (1+r)^n / ((1+r)^n - 1)` | Zero principal, zero rate, 0-year term |
| `one_percent_rule()` | `monthly_rent >= purchase_price * 0.01` | Zero rent, zero price |
| `gross_rent_multiplier()` | `purchase_price / annual_rent` | Zero rent, negative price |
| `annual_depreciation()` | `(purchase_price - land_value) / 27.5` | Zero value, land > purchase |

### Out of Scope (Phase C or later)
- `irr()` — requires numerical methods, needs dedicated verification
- `score_listing_v2()` — composite score, depends on market data
- `calculate_flip_strategy()` — multi-step workflow, too complex for initial pass
- `calculate_tax_benefits()` — jurisdiction-dependent formulas
- `brrrr_coc_return()` — multi-variable simulation

---

## 3. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | Reference implementation in `tests/finance_reference.py` — pure Python, no Django deps | P0 |
| F-02 | Parameterized test suite — ≥50 edge cases across 8 core functions | P0 |
| F-03 | CI gate: `make test-finance-math` that fails on any KPI deviation | P1 |
| F-04 | Every core function has its mathematical formula in the docstring | P1 |
| F-05 | Reference values validated against an external calculator (Excel or online) | P1 |
| F-06 | Edge cases cover: zero, negative, extreme (10x, 100x), precision (10+ decimal places) | P0 |

---

## 4. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | `tests/finance_reference.py` implements all 8 core KPI functions independently | unit |
| AC-02 | Test suite runs: `python -m pytest tests/test_finance_math.py -v` with ≥50 parametrized cases | unit |
| AC-03 | Every test compares production implementation against reference implementation with `abs(diff) < Decimal("0.01")` tolerance | unit |
| AC-04 | Edge case tests for `calculate_monthly_mortgage` include: P=0, r=0, n=0, r<0, n=1 | unit |
| AC-05 | Edge case tests for `cap_rate` include: price=0, noi=0, noi negative, price=1 | unit |
| AC-06 | Edge case tests for `dscr` include: debt_service=0, noi negative, noi<debt_service | unit |
| AC-07 | Edge case tests for `one_percent_rule` include: exact 1%, 0.99%, 1.01%, zero values | unit |
| AC-08 | `make test-finance-math` target runs the verification suite | unit |
| AC-09 | CI gate in `ci-quality.yml` runs `make test-finance-math` on every PR | unit |
| AC-10 | All 8 core function docstrings contain the mathematical formula (LaTeX or plain math) | unit |
