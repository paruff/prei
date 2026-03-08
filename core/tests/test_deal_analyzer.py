"""Boundary and regression tests for deal-analyzer KPI functions.

Covers happy-path, zero-denominator, negative, and very-large-value scenarios
for every function listed in the Phase 2.1 issue.
"""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    calculate_break_even_rent,
    calculate_flip_strategy,
    calculate_monthly_mortgage,
    calculate_rental_strategy,
    calculate_roi_components,
    cap_rate,
    cash_on_cash,
    dscr,
    irr,
    noi,
)

# ---------------------------------------------------------------------------
# noi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "monthly_income,monthly_expenses,expected",
    [
        (Decimal("1500"), Decimal("500"), Decimal("12000")),
        (Decimal("2000"), Decimal("800"), Decimal("14400")),
        (Decimal("0"), Decimal("0"), Decimal("0")),
    ],
)
def test_noi_happy_path(monthly_income, monthly_expenses, expected):
    assert noi(monthly_income, monthly_expenses) == expected


def test_noi_negative_income():
    """NOI with negative net income (expenses exceed income)."""
    result = noi(Decimal("500"), Decimal("1000"))
    assert result == Decimal("-6000")


def test_noi_negative_expenses():
    """NOI when expenses are negative (e.g. credit/refund)."""
    result = noi(Decimal("1000"), Decimal("-200"))
    assert result == Decimal("14400")


def test_noi_very_large_values():
    """NOI should not overflow or lose precision on large values."""
    result = noi(Decimal("999999"), Decimal("500000"))
    assert result == (Decimal("999999") - Decimal("500000")) * Decimal(12)


# ---------------------------------------------------------------------------
# cap_rate
# ---------------------------------------------------------------------------


def test_cap_rate_happy_path():
    """Standard cap-rate: 12 000 / 200 000 = 0.06."""
    result = cap_rate(Decimal("12000"), Decimal("200000"))
    assert abs(result - Decimal("0.06")) < Decimal("0.0001")


def test_cap_rate_zero_denominator():
    """Zero purchase price must return Decimal('0') — not raise."""
    assert cap_rate(Decimal("12000"), Decimal("0")) == Decimal("0")


def test_cap_rate_negative_noi():
    """Negative NOI yields a negative cap rate."""
    result = cap_rate(Decimal("-5000"), Decimal("200000"))
    assert result < Decimal("0")


def test_cap_rate_very_large_purchase_price():
    """Cap rate with a very large purchase price is near zero."""
    result = cap_rate(Decimal("12000"), Decimal("999999999.99"))
    assert result >= Decimal("0")
    assert result < Decimal("0.001")


def test_cap_rate_very_large_noi():
    """Cap rate with a very large NOI returns a large positive number."""
    result = cap_rate(Decimal("999999999.99"), Decimal("200000"))
    assert result > Decimal("1")


# ---------------------------------------------------------------------------
# cash_on_cash
# ---------------------------------------------------------------------------


def test_cash_on_cash_happy_path():
    """10 000 / 50 000 = 0.20 (20%)."""
    result = cash_on_cash(Decimal("10000"), Decimal("50000"))
    assert abs(result - Decimal("0.20")) < Decimal("0.0001")


def test_cash_on_cash_zero_denominator():
    """Zero cash invested must return Decimal('0') — not raise."""
    assert cash_on_cash(Decimal("10000"), Decimal("0")) == Decimal("0")


def test_cash_on_cash_negative_cash_flow():
    """Negative annual cash flow yields a negative CoC return."""
    result = cash_on_cash(Decimal("-3000"), Decimal("50000"))
    assert result < Decimal("0")


def test_cash_on_cash_very_large_values():
    """CoC with very large invested amount stays precise."""
    result = cash_on_cash(Decimal("50000"), Decimal("999999999.99"))
    assert result >= Decimal("0")
    assert result < Decimal("0.001")


# ---------------------------------------------------------------------------
# dscr
# ---------------------------------------------------------------------------


def test_dscr_happy_path():
    """DSCR: 24 000 / 20 000 = 1.20."""
    result = dscr(Decimal("24000"), Decimal("20000"))
    assert abs(result - Decimal("1.20")) < Decimal("0.0001")


def test_dscr_zero_denominator():
    """Zero debt service must return Decimal('0') — not raise."""
    assert dscr(Decimal("24000"), Decimal("0")) == Decimal("0")


def test_dscr_negative_noi():
    """Negative NOI produces a negative DSCR."""
    result = dscr(Decimal("-5000"), Decimal("20000"))
    assert result < Decimal("0")


def test_dscr_very_large_values():
    """DSCR should remain stable with large numbers."""
    result = dscr(Decimal("999999999.99"), Decimal("500000000"))
    assert result > Decimal("1")


# ---------------------------------------------------------------------------
# irr
# ---------------------------------------------------------------------------


def test_irr_happy_path():
    """Standard IRR: initial outlay followed by positive returns."""
    cashflows = [Decimal("-100000")] + [Decimal("15000")] * 10
    result = irr(cashflows)
    assert isinstance(result, Decimal)
    # Realistic annual IRR should be a small positive number
    assert result > Decimal("0")
    assert result < Decimal("1")


def test_irr_no_real_solution_returns_zero():
    """IRR must return Decimal('0') rather than raise when no real solution."""
    # All-negative cash flows have no IRR solution
    cashflows = [Decimal("-10000")] * 5
    result = irr(cashflows)
    assert result == Decimal("0")


def test_irr_all_positive_returns_zero():
    """All-positive cash flows have no valid IRR — safe fallback must return Decimal('0')."""
    cashflows = [Decimal("1000")] * 5
    result = irr(cashflows)
    # numpy-financial returns nan for all-positive series; our wrapper normalises to 0
    assert result == Decimal("0")


def test_irr_single_period():
    """Two-period cash flow: -100, +110 → IRR ≈ 10%."""
    cashflows = [Decimal("-100"), Decimal("110")]
    result = irr(cashflows)
    assert isinstance(result, Decimal)
    assert abs(result - Decimal("0.10")) < Decimal("0.001")


def test_irr_very_large_cashflows():
    """IRR with large dollar amounts should still return a valid Decimal."""
    cashflows = [Decimal("-999999999")] + [Decimal("200000000")] * 8
    result = irr(cashflows)
    assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# calculate_monthly_mortgage
# ---------------------------------------------------------------------------


def test_mortgage_known_value():
    """$280 000 at 7.5% for 30 years should produce ~$1 958.35/month."""
    payment = calculate_monthly_mortgage(Decimal("280000"), Decimal("7.5"), 30)
    assert abs(payment - Decimal("1958.35")) < Decimal("1.00")


def test_mortgage_large_loan_amount():
    """Mortgage on a very large loan (e.g. $10 M) should not overflow."""
    payment = calculate_monthly_mortgage(
        Decimal("10000000"), Decimal("7.5"), 30
    )
    # Proportional to $280k → $1 958.35, so $10M ≈ $69 941
    assert payment > Decimal("60000")
    assert payment < Decimal("80000")


def test_mortgage_very_high_interest():
    """High interest rate (e.g. 20%) returns a higher payment than 7.5%."""
    payment_high = calculate_monthly_mortgage(Decimal("280000"), Decimal("20"), 30)
    payment_normal = calculate_monthly_mortgage(Decimal("280000"), Decimal("7.5"), 30)
    assert payment_high > payment_normal


def test_mortgage_short_term():
    """15-year mortgage on same loan/rate pays more per month than 30-year."""
    payment_15 = calculate_monthly_mortgage(Decimal("280000"), Decimal("7.5"), 15)
    payment_30 = calculate_monthly_mortgage(Decimal("280000"), Decimal("7.5"), 30)
    assert payment_15 > payment_30


# ---------------------------------------------------------------------------
# calculate_break_even_rent
# ---------------------------------------------------------------------------


def test_break_even_rent_happy_path():
    """Standard break-even rent calculation."""
    result = calculate_break_even_rent(
        Decimal("2500"), Decimal("5"), Decimal("10")
    )
    assert "monthly" in result
    assert "annual" in result
    # rent * (1 - 0.05) * (1 - 0.10) = 2500  →  rent = 2500 / (0.95 * 0.90) ≈ 2923.98
    assert abs(result["monthly"] - Decimal("2924")) < Decimal("1.00")
    # The function quantizes monthly and annual independently from the same pre-rounded
    # intermediate, so annual != monthly * 12 exactly; allow up to one cent of drift.
    assert abs(result["annual"] - result["monthly"] * Decimal(12)) < Decimal("0.10")


def test_break_even_rent_zero_vacancy_zero_management():
    """With 0% vacancy and 0% management, break-even rent equals costs."""
    result = calculate_break_even_rent(
        Decimal("2000"), Decimal("0"), Decimal("0")
    )
    assert result["monthly"] == Decimal("2000.00")


def test_break_even_rent_zero_denominator():
    """100% vacancy makes divisor zero — must return Decimal('0'), not raise."""
    result = calculate_break_even_rent(
        Decimal("2500"), Decimal("100"), Decimal("0")
    )
    assert result["monthly"] == Decimal("0")
    assert result["annual"] == Decimal("0")


def test_break_even_rent_zero_denominator_via_management():
    """100% management fee makes divisor zero — must return Decimal('0'), not raise."""
    result = calculate_break_even_rent(
        Decimal("2500"), Decimal("0"), Decimal("100")
    )
    assert result["monthly"] == Decimal("0")
    assert result["annual"] == Decimal("0")


def test_break_even_rent_very_large_costs():
    """Break-even rent with very large monthly costs stays consistent."""
    result = calculate_break_even_rent(
        Decimal("999999"), Decimal("8"), Decimal("10")
    )
    assert result["monthly"] > Decimal("999999")
    assert result["annual"] > result["monthly"]


def test_break_even_rent_parametrize():
    """Break-even rent scales linearly with monthly costs."""
    r1 = calculate_break_even_rent(Decimal("1000"), Decimal("5"), Decimal("5"))
    r2 = calculate_break_even_rent(Decimal("2000"), Decimal("5"), Decimal("5"))
    # Each result is independently quantized to 2 decimal places, so doubling the
    # monthly cost may introduce up to one cent of rounding difference per result
    # (worst case: 0.005 * 2 = 0.01 on each side → combined max drift ≈ 0.02).
    assert abs(r2["monthly"] - r1["monthly"] * 2) < Decimal("0.02")


# ---------------------------------------------------------------------------
# calculate_roi_components
# ---------------------------------------------------------------------------


def test_roi_components_happy_path():
    """Standard ROI: positive cash flow, typical inputs."""
    roi = calculate_roi_components(
        purchase_price=Decimal("300000"),
        loan_amount=Decimal("240000"),
        interest_rate=Decimal("7.0"),
        loan_term_years=30,
        total_cash_invested=Decimal("70000"),
        annual_cash_flow=Decimal("6000"),
        appreciation_rate=Decimal("3.0"),
        tax_bracket=Decimal("24"),
        num_years=5,
    )
    assert "year1" in roi
    assert "year5Projected" in roi
    assert "components" in roi
    assert roi["year1"]["roi"] > Decimal("-100")


def test_roi_components_zero_cash_invested():
    """When no cash is invested, ROI components default to zero."""
    roi = calculate_roi_components(
        purchase_price=Decimal("300000"),
        loan_amount=Decimal("0"),
        interest_rate=Decimal("0"),
        loan_term_years=30,
        total_cash_invested=Decimal("0"),
        annual_cash_flow=Decimal("0"),
        appreciation_rate=Decimal("3.0"),
        tax_bracket=Decimal("24"),
        num_years=5,
    )
    assert roi["year1"]["roi"] == Decimal("0.0")
    assert roi["year5Projected"]["roi"] == Decimal("0.0")


def test_roi_components_negative_cash_flow():
    """Negative annual cash flow is handled gracefully."""
    roi = calculate_roi_components(
        purchase_price=Decimal("300000"),
        loan_amount=Decimal("240000"),
        interest_rate=Decimal("7.0"),
        loan_term_years=30,
        total_cash_invested=Decimal("70000"),
        annual_cash_flow=Decimal("-5000"),
        appreciation_rate=Decimal("3.0"),
        tax_bracket=Decimal("24"),
        num_years=5,
    )
    assert isinstance(roi["year1"]["roi"], Decimal)
    assert roi["year1"]["cashFlow"] == Decimal("-5000.00")


def test_roi_components_very_large_purchase_price():
    """Very large purchase price does not cause errors."""
    roi = calculate_roi_components(
        purchase_price=Decimal("999999999.99"),
        loan_amount=Decimal("799999999.99"),
        interest_rate=Decimal("7.5"),
        loan_term_years=30,
        total_cash_invested=Decimal("200000000"),
        annual_cash_flow=Decimal("1000000"),
        appreciation_rate=Decimal("3.0"),
        tax_bracket=Decimal("24"),
        num_years=5,
    )
    assert "year1" in roi
    assert isinstance(roi["year1"]["roi"], Decimal)


# ---------------------------------------------------------------------------
# calculate_flip_strategy
# ---------------------------------------------------------------------------

_FLIP_DEFAULTS = dict(
    purchase_price=Decimal("200000"),
    renovation_costs=Decimal("30000"),
    holding_period_months=6,
    expected_sale_price=Decimal("280000"),
    selling_costs=Decimal("14000"),
    down_payment=Decimal("50000"),
    loan_amount=Decimal("150000"),
    interest_rate=Decimal("8.0"),
    loan_term_years=30,
    closing_costs=Decimal("5000"),
    property_tax_rate=Decimal("1.5"),
    insurance_annual=Decimal("1200"),
    utilities_monthly=Decimal("200"),
    property_type="single-family",
    year_built=2000,
)


def test_flip_strategy_happy_path():
    """Profitable flip: proceeds exceed all costs."""
    result = calculate_flip_strategy(**_FLIP_DEFAULTS)

    assert "netProfit" in result
    assert "roi" in result
    assert "annualizedReturn" in result
    assert "totalInvestment" in result
    assert result["netProfit"] > Decimal("0")
    assert result["roi"] > Decimal("0")


def test_flip_strategy_negative_profit():
    """Flip with a selling price lower than total costs produces negative profit."""
    params = {**_FLIP_DEFAULTS, "expected_sale_price": Decimal("200000")}
    result = calculate_flip_strategy(**params)

    assert result["netProfit"] < Decimal("0")
    assert result["roi"] < Decimal("0")


def test_flip_strategy_zero_investment():
    """Flip with zero down payment + closing costs → roi defaults to zero."""
    params = {
        **_FLIP_DEFAULTS,
        "down_payment": Decimal("0"),
        "closing_costs": Decimal("0"),
        "renovation_costs": Decimal("0"),
    }
    result = calculate_flip_strategy(**params)

    assert result["roi"] == Decimal("0.0")
    assert result["annualizedReturn"] == Decimal("0.0")


def test_flip_strategy_very_large_values():
    """Flip on a very large property does not raise."""
    params = {
        **_FLIP_DEFAULTS,
        "purchase_price": Decimal("5000000"),
        "expected_sale_price": Decimal("6500000"),
        "selling_costs": Decimal("325000"),
        "loan_amount": Decimal("4000000"),
        "down_payment": Decimal("1000000"),
        "renovation_costs": Decimal("500000"),
    }
    result = calculate_flip_strategy(**params)
    assert isinstance(result["netProfit"], Decimal)
    assert isinstance(result["roi"], Decimal)


def test_flip_strategy_keys():
    """Return dict contains all expected keys."""
    result = calculate_flip_strategy(**_FLIP_DEFAULTS)
    expected_keys = {
        "totalInvestment",
        "holdingCosts",
        "renovationCosts",
        "saleProceeds",
        "sellingCosts",
        "netProfit",
        "roi",
        "timeframe",
        "annualizedReturn",
    }
    assert expected_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# calculate_rental_strategy
# ---------------------------------------------------------------------------

_RENTAL_DEFAULTS = dict(
    purchase_price=Decimal("350000"),
    down_payment=Decimal("70000"),
    loan_amount=Decimal("280000"),
    interest_rate=Decimal("7.5"),
    loan_term_years=30,
    closing_costs=Decimal("7000"),
    annual_cash_flow=Decimal("5000"),
    appreciation_rate=Decimal("3.0"),
    holding_period_years=5,
)


def test_rental_strategy_happy_path():
    """Standard rental hold with positive cash flow."""
    result = calculate_rental_strategy(**_RENTAL_DEFAULTS)

    assert "totalInvestment" in result
    assert "roi" in result
    assert "annualizedReturn" in result
    assert result["totalInvestment"] == Decimal("77000.00")
    assert result["roi"] > Decimal("0")


def test_rental_strategy_negative_cash_flow():
    """Rental with negative annual cash flow (carrying cost exceeds rent)."""
    params = {**_RENTAL_DEFAULTS, "annual_cash_flow": Decimal("-6000")}
    result = calculate_rental_strategy(**params)

    assert isinstance(result["roi"], Decimal)
    # Negative cash flow reduces total gain but appreciation/equity may offset it
    total_key = "totalCashFlow5Years"
    assert result[total_key] == Decimal("-30000.00")


def test_rental_strategy_zero_investment():
    """Zero down payment + zero closing costs → roi defaults to zero."""
    params = {
        **_RENTAL_DEFAULTS,
        "down_payment": Decimal("0"),
        "closing_costs": Decimal("0"),
    }
    result = calculate_rental_strategy(**params)

    assert result["roi"] == Decimal("0.0")
    assert result["annualizedReturn"] == Decimal("0.0")


def test_rental_strategy_very_large_values():
    """Very large purchase price and loan amount do not raise."""
    params = {
        **_RENTAL_DEFAULTS,
        "purchase_price": Decimal("999999999.99"),
        "loan_amount": Decimal("799999999.99"),
        "down_payment": Decimal("200000000"),
        "annual_cash_flow": Decimal("1000000"),
    }
    result = calculate_rental_strategy(**params)
    assert isinstance(result["roi"], Decimal)
    assert isinstance(result["annualizedReturn"], Decimal)


def test_rental_strategy_holding_period_keys():
    """Return dict contains dynamic keys based on holding period."""
    result = calculate_rental_strategy(**_RENTAL_DEFAULTS)
    assert "year5CashFlow" in result
    assert "totalCashFlow5Years" in result
    assert "equityBuildup5Years" in result
    assert "appreciation5Years" in result
    assert "totalGain5Years" in result


def test_rental_strategy_different_holding_period():
    """Holding period of 10 years produces differently keyed output."""
    params = {**_RENTAL_DEFAULTS, "holding_period_years": 10}
    result = calculate_rental_strategy(**params)
    assert "year10CashFlow" in result
    assert "totalCashFlow10Years" in result
    assert "equityBuildup10Years" in result
