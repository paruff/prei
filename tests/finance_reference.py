"""Reference implementations of core KPI functions for math verification.

Each function independently reimplements the same mathematical formula
as the production code in ``investor_app/finance/utils.py``, from the
mathematical derivation — not from the production code.  Used by
``tests/test_finance_math.py`` to detect formula regressions.

All functions use ``Decimal`` arithmetic.  No Django, numpy, or other
external dependencies.
"""

from __future__ import annotations

from decimal import Decimal


# ── NOI: Net Operating Income ──────────────────────────────────────────────


# NOI = (Monthly Income - Monthly Expenses) × 12
def ref_noi(monthly_income: Decimal, monthly_expenses: Decimal) -> Decimal:
    return (monthly_income - monthly_expenses) * Decimal(12)


# ── Cap Rate: Capitalization Rate ──────────────────────────────────────────


# Cap Rate = Annual NOI ÷ Purchase Price
def ref_cap_rate(annual_noi: Decimal, purchase_price: Decimal) -> Decimal:
    if purchase_price == Decimal("0"):
        return Decimal("0")
    return annual_noi / purchase_price


# ── Cash-on-Cash Return ────────────────────────────────────────────────────


# CoC = Annual Cash Flow ÷ Total Cash Invested
def ref_cash_on_cash(
    annual_cash_flow: Decimal, total_cash_invested: Decimal
) -> Decimal:
    if total_cash_invested == Decimal("0"):
        return Decimal("0")
    return annual_cash_flow / total_cash_invested


# ── DSCR: Debt Service Coverage Ratio ──────────────────────────────────────


# DSCR = Annual NOI ÷ Annual Debt Service
def ref_dscr(annual_noi: Decimal, annual_debt_service: Decimal) -> Decimal:
    if annual_debt_service == Decimal("0"):
        return Decimal("0")
    return annual_noi / annual_debt_service


# ── Monthly Mortgage Payment (Amortization) ────────────────────────────────


# M = P [ r(1+r)^n ] / [ (1+r)^n - 1 ]
# where r = monthly rate, n = number of payments
#
# Interest rate is supplied as a percentage (e.g., 7.5 for 7.5%)
def ref_monthly_mortgage(
    loan_amount: Decimal, interest_rate: Decimal, loan_term_years: int
) -> Decimal:
    loan = loan_amount
    rate_pct = interest_rate
    years = Decimal(loan_term_years)

    if loan == Decimal("0"):
        return Decimal("0")
    if rate_pct == Decimal("0"):
        return (loan / (years * Decimal(12))).quantize(Decimal("0.01"))

    monthly_rate = rate_pct / Decimal("100") / Decimal("12")
    num_payments = years * Decimal("12")

    # Standard amortization: M = P * r * (1+r)^n / ((1+r)^n - 1)
    factor = (Decimal("1") + monthly_rate) ** num_payments
    payment = loan * (monthly_rate * factor) / (factor - Decimal("1"))
    return payment.quantize(Decimal("0.01"))


# ── 1% Rule ───────────────────────────────────────────────────────────────


# Pass if monthly_rent >= purchase_price × 0.01
def ref_one_percent_rule(monthly_rent: Decimal, purchase_price: Decimal) -> bool:
    return monthly_rent >= purchase_price * Decimal("0.01")


# ── Gross Rent Multiplier ──────────────────────────────────────────────────


# GRM = Purchase Price ÷ Annual Rent
def ref_gross_rent_multiplier(purchase_price: Decimal, annual_rent: Decimal) -> Decimal:
    if annual_rent == Decimal("0"):
        return Decimal("0")
    return purchase_price / annual_rent


# ── Annual Depreciation (27.5-year straight-line) ──────────────────────────


# Annual Depreciation = (Purchase Price - Land Value) ÷ 27.5
def ref_annual_depreciation(purchase_price: Decimal, land_value: Decimal) -> Decimal:
    return (purchase_price - land_value) / Decimal("27.5")
