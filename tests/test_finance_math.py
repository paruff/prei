"""Parameterized financial math verification suite — Phase B.

Each test compares the production KPI implementation against an
independently-written reference implementation.  A deviation greater
than the function's tolerance is treated as a regression failure.

300+ edge cases across 9 core KPI functions. NOI, cap rate, cash-on-cash,
DSCR, IRR, the 1% rule, and GRM each carry 50+ cases (docs/TOP_01_PLAN.md
Phase B, B-2); mortgage and depreciation retain their original coverage.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

# ── Production functions ───────────────────────────────────────────────────
from investor_app.finance.mortgage import calculate_monthly_mortgage
from investor_app.finance.scoring import gross_rent_multiplier, one_percent_rule
from investor_app.finance.taxes import annual_depreciation
from investor_app.finance.utils import cap_rate, cash_on_cash, dscr, irr, noi

# ── Reference implementations ──────────────────────────────────────────────
from tests.finance_reference import (
    ref_annual_depreciation,
    ref_cap_rate,
    ref_cash_on_cash,
    ref_dscr,
    ref_gross_rent_multiplier,
    ref_irr,
    ref_monthly_mortgage,
    ref_noi,
    ref_one_percent_rule,
)

_D = Decimal


def _case(ref_fn, label: str, *args):
    """Build a (label, *args, expected) case tuple, deriving ``expected``
    from the reference implementation itself. Used for bulk-generated edge
    cases where the point is catching prod/ref divergence (regression
    detection, the actual goal of this suite), not re-deriving the
    arithmetic by hand for every row.
    """
    return (label, *args, ref_fn(*args))


# Shared value pools for generated edge cases.
_POS = [100, 500, 1000, 5000, 10000, 50000, 100000, 250000, 500000, 999999]
_NEG = [-100, -500, -1000, -5000, -10000, -50000, -100000, -250000, -500000, -999999]
_EXTREME_LARGE = [1_000_000, 5_000_000, 10_000_000, 100_000_000, 999_999_999]
_EXTREME_SMALL = [
    "0.0001",
    "0.0005",
    "0.001",
    "0.005",
    "0.01",
    "0.05",
    "0.1",
    "0.5",
    "0.9999",
]
_CURRENCY = [
    "1234.56",
    "9999.99",
    "50000.01",
    "123456.78",
    "654321.99",
    "0.99",
    "1000000.01",
]


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

NOI_EXTRA_CASES = (
    [_case(ref_noi, f"zero_income_{e}", _D("0"), _D(str(e))) for e in _POS]
    + [_case(ref_noi, f"zero_expenses_{i}", _D(str(i)), _D("0")) for i in _POS]
    + [_case(ref_noi, f"negative_income_{i}", _D(str(i)), _D("800")) for i in _NEG]
    + [_case(ref_noi, f"negative_expenses_{e}", _D("1500"), _D(str(e))) for e in _NEG]
    + [
        _case(ref_noi, f"extreme_large_{i}", _D(str(i)), _D(str(i // 2)))
        for i in _EXTREME_LARGE
    ]
    + [_case(ref_noi, f"extreme_small_{v}", _D(v), _D("0")) for v in _EXTREME_SMALL]
    + [_case(ref_noi, f"currency_precision_{v}", _D(v), _D("1")) for v in _CURRENCY]
    + [_case(ref_noi, f"boundary_equal_{v}", _D(str(v)), _D(str(v))) for v in _POS]
    + [
        (f"int_coercion_{i}", i, i // 2, ref_noi(_D(str(i)), _D(str(i // 2))))
        for i in _POS[:5]
    ]
)
NOI_CASES = NOI_CASES + NOI_EXTRA_CASES


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

CAP_RATE_EXTRA_CASES = (
    [_case(ref_cap_rate, f"zero_price_{n}", _D(str(n)), _D("0")) for n in _POS]
    + [_case(ref_cap_rate, f"zero_noi_{p}", _D("0"), _D(str(p))) for p in _POS]
    + [_case(ref_cap_rate, f"negative_noi_{n}", _D(str(n)), _D("200000")) for n in _NEG]
    + [
        _case(ref_cap_rate, f"negative_price_{p}", _D("12000"), _D(str(p)))
        for p in _NEG
    ]
    + [
        _case(ref_cap_rate, f"extreme_large_{n}", _D(str(n)), _D(str(n * 5)))
        for n in _EXTREME_LARGE
    ]
    + [
        _case(ref_cap_rate, f"extreme_small_{v}", _D(v), _D("200000"))
        for v in _EXTREME_SMALL
    ]
    + [
        _case(ref_cap_rate, f"currency_precision_{v}", _D(v), _D("200000.01"))
        for v in _CURRENCY
    ]
    + [_case(ref_cap_rate, f"boundary_equal_{v}", _D(str(v)), _D(str(v))) for v in _POS]
    + [
        (f"int_coercion_{n}", n, 200000, ref_cap_rate(_D(str(n)), _D("200000")))
        for n in _POS[:5]
    ]
)
CAP_RATE_CASES = CAP_RATE_CASES + CAP_RATE_EXTRA_CASES


@pytest.mark.parametrize("label,noi,price,expected", CAP_RATE_CASES)
def test_cap_rate(label: str, noi: Decimal, price: Decimal, expected: Decimal) -> None:
    prod = cap_rate(noi, price)
    # ref_cap_rate only promises Decimal in/Decimal out (no to_decimal() of
    # its own); int/int-coercion cases pass raw ints to exercise production's
    # own to_decimal() boundary, so coerce here to keep ref's arithmetic in
    # Decimal too (bare int/int division would otherwise silently produce a
    # float and fail comparison against production's Decimal result).
    ref = ref_cap_rate(_D(str(noi)), _D(str(price)))
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

COC_EXTRA_CASES = (
    [_case(ref_cash_on_cash, f"zero_invested_{n}", _D(str(n)), _D("0")) for n in _POS]
    + [_case(ref_cash_on_cash, f"zero_cashflow_{p}", _D("0"), _D(str(p))) for p in _POS]
    + [
        _case(ref_cash_on_cash, f"negative_cashflow_{n}", _D(str(n)), _D("50000"))
        for n in _NEG
    ]
    + [
        _case(ref_cash_on_cash, f"negative_invested_{p}", _D("6000"), _D(str(p)))
        for p in _NEG
    ]
    + [
        _case(ref_cash_on_cash, f"extreme_large_{n}", _D(str(n)), _D(str(n * 2)))
        for n in _EXTREME_LARGE
    ]
    + [
        _case(ref_cash_on_cash, f"extreme_small_{v}", _D(v), _D("50000"))
        for v in _EXTREME_SMALL
    ]
    + [
        _case(ref_cash_on_cash, f"currency_precision_{v}", _D(v), _D("45678.90"))
        for v in _CURRENCY
    ]
    + [
        _case(ref_cash_on_cash, f"boundary_equal_{v}", _D(str(v)), _D(str(v)))
        for v in _POS
    ]
    + [
        (f"int_coercion_{n}", n, 50000, ref_cash_on_cash(_D(str(n)), _D("50000")))
        for n in _POS[:5]
    ]
)
COC_CASES = COC_CASES + COC_EXTRA_CASES


@pytest.mark.parametrize("label,cf,invested,expected", COC_CASES)
def test_cash_on_cash(
    label: str, cf: Decimal, invested: Decimal, expected: Decimal
) -> None:
    prod = cash_on_cash(cf, invested)
    ref = ref_cash_on_cash(_D(str(cf)), _D(str(invested)))
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

DSCR_EXTRA_CASES = (
    [_case(ref_dscr, f"zero_debt_{n}", _D(str(n)), _D("0")) for n in _POS]
    + [_case(ref_dscr, f"zero_noi_{d}", _D("0"), _D(str(d))) for d in _POS]
    + [_case(ref_dscr, f"negative_noi_{n}", _D(str(n)), _D("12000")) for n in _NEG]
    + [_case(ref_dscr, f"negative_debt_{d}", _D("15000"), _D(str(d))) for d in _NEG]
    + [
        _case(ref_dscr, f"extreme_large_{n}", _D(str(n)), _D(str(n // 3)))
        for n in _EXTREME_LARGE
    ]
    + [
        _case(ref_dscr, f"extreme_small_{v}", _D(v), _D("12000"))
        for v in _EXTREME_SMALL
    ]
    + [
        _case(ref_dscr, f"currency_precision_{v}", _D(v), _D("9876.54"))
        for v in _CURRENCY
    ]
    + [_case(ref_dscr, f"boundary_equal_{v}", _D(str(v)), _D(str(v))) for v in _POS]
    + [
        (f"int_coercion_{n}", n, 12000, ref_dscr(_D(str(n)), _D("12000")))
        for n in _POS[:5]
    ]
)
DSCR_CASES = DSCR_CASES + DSCR_EXTRA_CASES


@pytest.mark.parametrize("label,noi,debt,expected", DSCR_CASES)
def test_dscr(label: str, noi: Decimal, debt: Decimal, expected: Decimal) -> None:
    prod = dscr(noi, debt)
    ref = ref_dscr(_D(str(noi)), _D(str(debt)))
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

ONE_PCT_EXTRA_CASES = (
    [_case(ref_one_percent_rule, f"zero_rent_{p}", _D("0"), _D(str(p))) for p in _POS]
    + [
        _case(ref_one_percent_rule, f"negative_rent_{r}", _D(str(r)), _D("200000"))
        for r in _NEG
    ]
    + [
        _case(
            ref_one_percent_rule,
            f"extreme_large_{p}",
            _D(str(p // 50)),
            _D(str(p)),
        )
        for p in _EXTREME_LARGE
    ]
    + [
        _case(ref_one_percent_rule, f"extreme_small_price_{v}", _D("50"), _D(v))
        for v in _EXTREME_SMALL
    ]
    + [
        _case(ref_one_percent_rule, f"currency_precision_{v}", _D(v), _D("20000"))
        for v in _CURRENCY
    ]
    + [
        _case(
            ref_one_percent_rule,
            f"boundary_exact_{v}",
            _D(str(v)) * _D("0.01"),
            _D(str(v)),
        )
        for v in _POS
    ]
    + [
        (f"int_coercion_{p}", 2000, p, ref_one_percent_rule(_D("2000"), _D(str(p))))
        for p in _POS[:5]
    ]
)
ONE_PCT_CASES = ONE_PCT_CASES + ONE_PCT_EXTRA_CASES


@pytest.mark.parametrize("label,rent,price,expected", ONE_PCT_CASES)
def test_one_percent_rule(
    label: str, rent: Decimal, price: Decimal, expected: bool
) -> None:
    prod = one_percent_rule(rent, price)
    ref = ref_one_percent_rule(rent, price)
    assert prod == ref, f"1% Rule {label}: prod={prod} ref={ref}"
    assert ref == expected, f"1% Rule {label}: expected={expected} got={ref}"


# purchase_price <= 0 is invalid for the 1% Rule (production raises ValueError
# at investor_app/finance/utils.py:1663) — verify both production and the
# reference implementation enforce the same contract.
ONE_PCT_ERROR_CASES = [(f"zero_price_{r}", _D(str(r)), _D("0")) for r in _POS[:5]] + [
    (f"negative_price_{r}_{p}", _D(str(r)), _D(str(p)))
    for r, p in zip(_POS[:5], _NEG[:5])
]


@pytest.mark.parametrize("label,rent,price", ONE_PCT_ERROR_CASES)
def test_one_percent_rule_raises(label: str, rent: Decimal, price: Decimal) -> None:
    with pytest.raises(ValueError):
        one_percent_rule(rent, price)
    with pytest.raises(ValueError):
        ref_one_percent_rule(rent, price)


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

GRM_EXTRA_CASES = (
    [
        _case(ref_gross_rent_multiplier, f"zero_price_{r}", _D("0"), _D(str(r)))
        for r in _POS
    ]
    + [
        _case(ref_gross_rent_multiplier, f"negative_price_{p}", _D(str(p)), _D("24000"))
        for p in _NEG
    ]
    + [
        _case(
            ref_gross_rent_multiplier,
            f"extreme_large_{p}",
            _D(str(p)),
            _D(str(p // 10)),
        )
        for p in _EXTREME_LARGE
    ]
    + [
        _case(ref_gross_rent_multiplier, f"extreme_small_rent_{v}", _D("50000"), _D(v))
        for v in _EXTREME_SMALL
    ]
    + [
        _case(
            ref_gross_rent_multiplier, f"currency_precision_{v}", _D(v), _D("9876.54")
        )
        for v in _CURRENCY
    ]
    + [
        _case(ref_gross_rent_multiplier, f"boundary_equal_{v}", _D(str(v)), _D(str(v)))
        for v in _POS
    ]
    + [
        (
            f"int_coercion_{p}",
            p,
            24000,
            ref_gross_rent_multiplier(_D(str(p)), _D("24000")),
        )
        for p in _POS[:5]
    ]
)
GRM_CASES = GRM_CASES + GRM_EXTRA_CASES


@pytest.mark.parametrize("label,price,rent,expected", GRM_CASES)
def test_grm(label: str, price: Decimal, rent: Decimal, expected: Decimal) -> None:
    prod = gross_rent_multiplier(price, rent)
    ref = ref_gross_rent_multiplier(_D(str(price)), _D(str(rent)))
    assert abs(prod - ref) < _D("0.0001"), f"GRM {label}: prod={prod} ref={ref}"


# annual_rent <= 0 is invalid for GRM (production raises ValueError at
# investor_app/finance/utils.py:1687) — verify both production and the
# reference implementation enforce the same contract.
GRM_ERROR_CASES = [(f"zero_rent_{p}", _D(str(p)), _D("0")) for p in _POS[:5]] + [
    (f"negative_rent_{p}_{r}", _D(str(p)), _D(str(r)))
    for p, r in zip(_POS[:5], _NEG[:5])
]


@pytest.mark.parametrize("label,price,rent", GRM_ERROR_CASES)
def test_grm_raises(label: str, price: Decimal, rent: Decimal) -> None:
    with pytest.raises(ValueError):
        gross_rent_multiplier(price, rent)
    with pytest.raises(ValueError):
        ref_gross_rent_multiplier(price, rent)


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


# ═══════════════════════════════════════════════════════════════════════════
# IRR — Internal Rate of Return
# ═══════════════════════════════════════════════════════════════════════════


def _series(principal, annual_cf, years: int, exit_value=0) -> list[Decimal]:
    """Initial outflow, (years - 1) equal inflows, final inflow + exit value."""
    if years <= 1:
        return [Decimal(-principal), Decimal(annual_cf) + Decimal(exit_value)]
    return (
        [Decimal(-principal)]
        + [Decimal(annual_cf)] * (years - 1)
        + [Decimal(annual_cf) + Decimal(exit_value)]
    )


_IRR_NORMAL = [
    (f"normal_p{p}_y{y}", _series(p, int(p * 0.08), y, int(p * 0.1)))
    for p in [50000, 100000, 200000, 300000, 500000]
    for y in [3, 5, 7, 10]
]  # 20 cases

_IRR_LONG_SERIES = [
    (f"long_series_y{y}", _series(150000, 15000, y, 30000)) for y in [12, 15, 18, 20]
]  # 4 cases

_IRR_EXTREME_LARGE = [
    (f"extreme_large_p{p}", _series(p, int(p * 0.05), 5, int(p * 0.2)))
    for p in [10_000_000, 100_000_000, 999_999_999]
]  # 3 cases

_IRR_SMALL_MAGNITUDE = [
    (
        f"small_magnitude_p{p}",
        _series(p, max(5, int(p * 0.08)), 4, max(5, int(p * 0.1))),
    )
    for p in [500, 2000, 8000]
]  # 3 cases

_IRR_SINGLE_CASHFLOW = [
    (f"single_cashflow_{v}", [Decimal(-v)]) for v in [100, 100000, 1]
]  # 3 cases — no real root possible with only one period

_IRR_NO_SIGN_CHANGE = [
    ("all_positive_a", [Decimal(v) for v in [1000, 1000, 1000]]),
    ("all_positive_b", [Decimal(v) for v in [500, 600, 700, 800]]),
    ("all_positive_c", [Decimal(100)] * 10),
    ("all_negative_a", [Decimal(v) for v in [-1000, -500, -200]]),
    ("all_negative_b", [Decimal(-100)] * 5),
]  # 5 cases — no sign change, no real root

_IRR_VARIED = (
    [
        (
            f"declining_cf_p{p}",
            [Decimal(-p)] + [Decimal(int(p * 0.1 * (1 - 0.05 * i))) for i in range(6)],
        )
        for p in [80000, 150000, 250000]
    ]
    + [
        (
            f"growing_cf_p{p}",
            [Decimal(-p)] + [Decimal(int(p * 0.05 * (1 + 0.1 * i))) for i in range(6)],
        )
        for p in [80000, 150000, 250000]
    ]
    + [
        (
            f"currency_precision_p{p}",
            _series(p, p * Decimal("0.075"), 5, p * Decimal("0.15")),
        )
        for p in [Decimal("123456.78"), Decimal("99999.99")]
    ]
)  # 8 cases

_IRR_INT_COERCION = [
    ("int_coercion_a", [-100000, 12000, 12000, 12000, 130000]),
    ("int_coercion_b", [-50000, 6000, 6000, 60000]),
    ("int_coercion_c", [-200000, 20000, 20000, 20000, 20000, 220000]),
]  # 3 cases — raw ints, not Decimal, exercise to_decimal()/Decimal(str()) coercion

IRR_CASES = (
    _IRR_NORMAL
    + _IRR_LONG_SERIES
    + _IRR_EXTREME_LARGE
    + _IRR_SMALL_MAGNITUDE
    + _IRR_SINGLE_CASHFLOW
    + _IRR_NO_SIGN_CHANGE
    + _IRR_VARIED
    + _IRR_INT_COERCION
)  # 49 cases


@pytest.mark.parametrize("label,cashflows", IRR_CASES)
def test_irr(label: str, cashflows: list) -> None:
    prod = irr(cashflows)
    ref = ref_irr([Decimal(str(c)) for c in cashflows])
    assert abs(prod - ref) < _D("0.0005"), f"IRR {label}: prod={prod} ref={ref}"


# Cashflow series with more than one sign change can have multiple
# mathematically valid real roots. numpy_financial.irr and our bisection
# search aren't guaranteed to converge on the *same* root in that case, so
# rather than asserting prod == ref, verify each independently satisfies
# NPV(rate) ≈ 0 — the actual definition of a valid IRR.
IRR_MULTIPLE_ROOT_CASES = [
    (
        "multi_sign_change_a",
        [Decimal("-100000"), Decimal("300000"), Decimal("-220000")],
    ),
    ("multi_sign_change_b", [Decimal("-50000"), Decimal("120000"), Decimal("-71000")]),
    (
        "multi_sign_change_c",
        [Decimal("-200000"), Decimal("500000"), Decimal("-310000")],
    ),
]  # 3 cases


def _npv_at(rate: Decimal, cashflows: list[Decimal]) -> Decimal:
    base = Decimal("1") + rate
    return sum((cf / (base**t) for t, cf in enumerate(cashflows)), Decimal("0"))


@pytest.mark.parametrize("label,cashflows", IRR_MULTIPLE_ROOT_CASES)
def test_irr_multiple_roots(label: str, cashflows: list[Decimal]) -> None:
    prod = irr(cashflows)
    ref = ref_irr(cashflows)
    assert abs(_npv_at(prod, cashflows)) < _D("1"), (
        f"IRR {label}: production rate {prod} does not zero NPV"
    )
    assert abs(_npv_at(ref, cashflows)) < _D("1"), (
        f"IRR {label}: reference rate {ref} does not zero NPV"
    )
