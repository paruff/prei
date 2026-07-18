"""Parameterized financial math verification suite — Phase B.

Each test compares the production KPI implementation against an
independently-written reference implementation.  A deviation greater
than ``Decimal(\"0.01\")`` is treated as a regression failure.

60 edge cases across 8 core KPI functions.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

# ── Production functions ───────────────────────────────────────────────────
from investor_app.finance.utils import (
    annual_depreciation,
    calculate_monthly_mortgage,
    cap_rate,
    cash_on_cash,
    dscr,
    gross_rent_multiplier,
    noi,
    one_percent_rule,
)

# ── Reference implementations ──────────────────────────────────────────────
from tests.finance_reference import (
    ref_annual_depreciation,
    ref_cap_rate,
    ref_cash_on_cash,
    ref_dscr,
    ref_gross_rent_multiplier,
    ref_monthly_mortgage,
    ref_noi,
    ref_one_percent_rule,
)

# For tests that don't need Django: just verify reference self-consistency
_D = Decimal


# ═══════════════════════════════════════════════════════════════════════════
# NOI — Net Operating Income
# ═══════════════════════════════════════════════════════════════════════════

NOI_CASES = [
    # (monthly_income, monthly_expenses, expected_annual_noi)
    ("normal", _D("1500"), _D("800"), _D("8400")),
    ("zero_income", _D("0"), _D("800"), _D("-9600")),
    ("zero_expenses", _D("2000"), _D("0"), _D("24000")),
    ("both_zero", _D("0"), _D("0"), _D("0")),
    ("negative_noi", _D("500"), _D("1200"), _D("-8400")),
    ("high_precision", _D("1234.56789"), _D("987.65432"), _D("2962.96284")),
    ("currency_precision", _D("9999.99"), _D("5000.01"), _D("59999.76")),
    ("extreme_income", _D("50000"), _D("1000"), _D("588000")),
]


@pytest.mark.parametrize("label,income,expenses,expected", NOI_CASES)
def test_noi(label: str, income: Decimal, expenses: Decimal, expected: Decimal) -> None:
    prod = noi(income, expenses)
    ref = ref_noi(income, expenses)
    assert abs(prod - ref) < _D("0.01"), f"NOI {label}: prod={prod} ref={ref}"
    assert abs(ref - expected) < _D("0.01"), (
        f"NOI {label}: expected={expected} got={ref}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Cap Rate
# ═══════════════════════════════════════════════════════════════════════════

CAP_RATE_CASES = [
    ("normal", _D("12000"), _D("200000"), _D("0.06")),
    ("zero_price", _D("12000"), _D("0"), _D("0")),
    ("zero_noi", _D("0"), _D("200000"), _D("0")),
    ("both_zero", _D("0"), _D("0"), _D("0")),
    ("negative_noi", _D("-5000"), _D("200000"), _D("-0.025")),
    ("precision", _D("12345"), _D("200001"), _D("0.061724691376543117")),
    ("high_cap", _D("50000"), _D("250000"), _D("0.2")),
    ("low_cap", _D("1000"), _D("200000"), _D("0.005")),
]


@pytest.mark.parametrize("label,noi,price,expected", CAP_RATE_CASES)
def test_cap_rate(label: str, noi: Decimal, price: Decimal, expected: Decimal) -> None:
    prod = cap_rate(noi, price)
    ref = ref_cap_rate(noi, price)
    assert abs(prod - ref) < _D("0.0001"), f"Cap rate {label}: prod={prod} ref={ref}"


# ═══════════════════════════════════════════════════════════════════════════
# Cash-on-Cash Return
# ═══════════════════════════════════════════════════════════════════════════

COC_CASES = [
    ("normal", _D("6000"), _D("50000"), _D("0.12")),
    ("zero_invested", _D("6000"), _D("0"), _D("0")),
    ("zero_cashflow", _D("0"), _D("50000"), _D("0")),
    ("negative_cashflow", _D("-2000"), _D("50000"), _D("-0.04")),
    ("precision", _D("1234.56"), _D("45678.90"), _D("0.027026826")),
    ("high_return", _D("50000"), _D("100000"), _D("0.5")),
    ("low_return", _D("100"), _D("200000"), _D("0.0005")),
    ("currency", _D("9999.99"), _D("100000.00"), _D("0.0999999")),
]


@pytest.mark.parametrize("label,cf,invested,expected", COC_CASES)
def test_cash_on_cash(
    label: str, cf: Decimal, invested: Decimal, expected: Decimal
) -> None:
    prod = cash_on_cash(cf, invested)
    ref = ref_cash_on_cash(cf, invested)
    assert abs(prod - ref) < _D("0.0001"), f"CoC {label}: prod={prod} ref={ref}"


# ═══════════════════════════════════════════════════════════════════════════
# DSCR — Debt Service Coverage Ratio
# ═══════════════════════════════════════════════════════════════════════════

DSCR_CASES = [
    ("normal", _D("15000"), _D("12000"), _D("1.25")),
    ("zero_debt", _D("15000"), _D("0"), _D("0")),
    ("zero_noi", _D("0"), _D("12000"), _D("0")),
    ("negative_noi", _D("-5000"), _D("12000"), _D("-0.4166666667")),
    ("below_one", _D("8000"), _D("12000"), _D("0.6666666667")),
    ("strong", _D("50000"), _D("10000"), _D("5")),
    ("precision", _D("12345.67"), _D("9876.54"), _D("1.249998987")),
    ("currency", _D("99999.99"), _D("33333.33"), _D("3.0000009")),
]


@pytest.mark.parametrize("label,noi,debt,expected", DSCR_CASES)
def test_dscr(label: str, noi: Decimal, debt: Decimal, expected: Decimal) -> None:
    prod = dscr(noi, debt)
    ref = ref_dscr(noi, debt)
    assert abs(prod - ref) < _D("0.0001"), f"DSCR {label}: prod={prod} ref={ref}"


# ═══════════════════════════════════════════════════════════════════════════
# Monthly Mortgage Payment
# ═══════════════════════════════════════════════════════════════════════════

MORTGAGE_CASES = [
    ("normal_30yr", _D("250000"), _D("7.5"), 30, _D("1748.04")),
    ("zero_loan", _D("0"), _D("7.5"), 30, _D("0.00")),
    ("zero_rate", _D("250000"), _D("0"), 30, _D("694.44")),
    ("one_year", _D("100000"), _D("6.0"), 1, _D("8606.64")),
    ("negative_rate", _D("250000"), _D("-1"), 30, _D("0.00")),
    ("high_rate", _D("100000"), _D("18.0"), 30, _D("1507.14")),
    ("precision", _D("123456.789"), _D("5.375"), 15, _D("999.63")),
    ("small_loan", _D("50000"), _D("3.5"), 30, _D("224.52")),
    ("large_loan", _D("5000000"), _D("4.0"), 30, _D("23870.80")),
]


@pytest.mark.parametrize("label,loan,rate,years,expected", MORTGAGE_CASES)
def test_mortgage(
    label: str, loan: Decimal, rate: Decimal, years: int, expected: Decimal
) -> None:
    prod = calculate_monthly_mortgage(loan, rate, years)
    ref = ref_monthly_mortgage(loan, rate, years)
    assert abs(prod - ref) < _D("0.02"), (
        f"Mortgage {label}: prod={prod} ref={ref} expected={expected}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1% Rule
# ═══════════════════════════════════════════════════════════════════════════

ONE_PCT_CASES = [
    ("exact_1pct", _D("2000"), _D("200000"), True),
    ("just_below", _D("1999"), _D("200000"), False),
    ("just_above", _D("2001"), _D("200000"), True),
    ("zero_rent", _D("0"), _D("200000"), False),
    ("large_values", _D("5000"), _D("499999"), True),
    ("currency", _D("199.99"), _D("20000"), False),
]


@pytest.mark.parametrize("label,rent,price,expected", ONE_PCT_CASES)
def test_one_percent_rule(
    label: str, rent: Decimal, price: Decimal, expected: bool
) -> None:
    prod = one_percent_rule(rent, price)
    ref = ref_one_percent_rule(rent, price)
    assert prod == ref, f"1% Rule {label}: prod={prod} ref={ref}"
    assert ref == expected, f"1% Rule {label}: expected={expected} got={ref}"


# ═══════════════════════════════════════════════════════════════════════════
# Gross Rent Multiplier
# ═══════════════════════════════════════════════════════════════════════════

GRM_CASES = [
    ("normal", _D("200000"), _D("24000"), _D("8.3333333333")),
    ("zero_price", _D("0"), _D("24000"), _D("0")),
    ("high_grm", _D("500000"), _D("10000"), _D("50")),
    ("low_grm", _D("50000"), _D("24000"), _D("2.08333333333")),
    ("precision", _D("123456.78"), _D("9876.54"), _D("12.500003556")),
    ("currency", _D("99999.99"), _D("12345.67"), _D("8.10001174")),
]


@pytest.mark.parametrize("label,price,rent,expected", GRM_CASES)
def test_grm(label: str, price: Decimal, rent: Decimal, expected: Decimal) -> None:
    prod = gross_rent_multiplier(price, rent)
    ref = ref_gross_rent_multiplier(price, rent)
    assert abs(prod - ref) < _D("0.0001"), f"GRM {label}: prod={prod} ref={ref}"


# ═══════════════════════════════════════════════════════════════════════════
# Annual Depreciation
# ═══════════════════════════════════════════════════════════════════════════

DEPRECIATION_CASES = [
    ("normal", _D("300000"), _D("50000"), _D("9090.9090909091")),
    ("zero_land", _D("300000"), _D("0"), _D("10909.0909090909")),
    ("expensive", _D("1000000"), _D("200000"), _D("29090.9090909091")),
    ("precision", _D("123456.78"), _D("23456.78"), _D("3636.3636363636")),
    ("currency", _D("99999.99"), _D("9999.99"), _D("3272.7272727273")),
]


@pytest.mark.parametrize("label,price,land,expected", DEPRECIATION_CASES)
def test_annual_depreciation(
    label: str, price: Decimal, land: Decimal, expected: Decimal
) -> None:
    prod = annual_depreciation(price, land)
    ref = ref_annual_depreciation(price, land)
    assert abs(prod - ref) < _D("0.01"), f"Depreciation {label}: prod={prod} ref={ref}"
