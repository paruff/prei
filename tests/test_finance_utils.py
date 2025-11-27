"""
Tests for investor_app.finance.utils module.

Test financial KPI calculations including:
- Net Operating Income (NOI)
- Cap Rate
- Cash-on-Cash Return
- Internal Rate of Return (IRR)
- Net Present Value (NPV)
"""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    calculate_cap_rate,
    calculate_cash_on_cash,
    calculate_irr,
    calculate_noi,
    npv,
    quantize_currency,
)


class TestQuantizeCurrency:
    """Tests for quantize_currency helper function."""

    def test_rounds_to_two_decimal_places_by_default(self):
        result = quantize_currency(Decimal("100.456"))
        assert result == Decimal("100.46")

    def test_rounds_to_custom_decimal_places(self):
        result = quantize_currency(Decimal("100.456789"), places=4)
        assert result == Decimal("100.4568")

    def test_half_up_rounding(self):
        result = quantize_currency(Decimal("100.125"))
        assert result == Decimal("100.13")

    def test_zero_value(self):
        result = quantize_currency(Decimal("0"))
        assert result == Decimal("0.00")

    def test_negative_value(self):
        result = quantize_currency(Decimal("-100.456"))
        assert result == Decimal("-100.46")


class TestCalculateNoi:
    """Tests for calculate_noi function."""

    def test_basic_noi_calculation(self):
        gross_income = Decimal("120000")
        operating_expenses = Decimal("40000")
        noi = calculate_noi(gross_income, operating_expenses)
        assert noi == Decimal("80000.00")

    def test_noi_with_float_inputs(self):
        noi = calculate_noi(120000.0, 40000.0)
        assert noi == Decimal("80000.00")

    def test_noi_with_string_inputs(self):
        noi = calculate_noi("120000", "40000")
        assert noi == Decimal("80000.00")

    def test_noi_zero_expenses(self):
        noi = calculate_noi(Decimal("100000"), Decimal("0"))
        assert noi == Decimal("100000.00")

    def test_noi_zero_income(self):
        noi = calculate_noi(Decimal("0"), Decimal("10000"))
        assert noi == Decimal("-10000.00")

    def test_noi_negative_result(self):
        # Operating expenses exceed income
        noi = calculate_noi(Decimal("50000"), Decimal("60000"))
        assert noi == Decimal("-10000.00")


class TestCalculateCapRate:
    """Tests for calculate_cap_rate function."""

    def test_basic_cap_rate(self):
        # NOI 50000, Purchase Price 1000000 => 5%
        cap_rate = calculate_cap_rate(Decimal("50000"), Decimal("1000000"))
        assert cap_rate == Decimal("0.0500")

    def test_cap_rate_with_float_inputs(self):
        cap_rate = calculate_cap_rate(50000.0, 1000000.0)
        assert cap_rate == Decimal("0.0500")

    def test_cap_rate_high_value(self):
        # NOI 100000, Purchase Price 800000 => 12.5%
        cap_rate = calculate_cap_rate(Decimal("100000"), Decimal("800000"))
        assert cap_rate == Decimal("0.1250")

    def test_cap_rate_zero_noi(self):
        cap_rate = calculate_cap_rate(Decimal("0"), Decimal("500000"))
        assert cap_rate == Decimal("0.0000")

    def test_cap_rate_zero_purchase_price_raises(self):
        with pytest.raises(ZeroDivisionError, match="purchase_price must be non-zero"):
            calculate_cap_rate(Decimal("50000"), Decimal("0"))

    def test_cap_rate_negative_noi(self):
        cap_rate = calculate_cap_rate(Decimal("-10000"), Decimal("500000"))
        assert cap_rate == Decimal("-0.0200")


class TestCalculateCashOnCash:
    """Tests for calculate_cash_on_cash function."""

    def test_basic_cash_on_cash(self):
        # Annual cash flow 10000, invested 100000 => 10%
        coc = calculate_cash_on_cash(Decimal("10000"), Decimal("100000"))
        assert coc == Decimal("0.1000")

    def test_cash_on_cash_with_float_inputs(self):
        coc = calculate_cash_on_cash(15000.0, 150000.0)
        assert coc == Decimal("0.1000")

    def test_cash_on_cash_high_return(self):
        # 20% return
        coc = calculate_cash_on_cash(Decimal("40000"), Decimal("200000"))
        assert coc == Decimal("0.2000")

    def test_cash_on_cash_zero_cash_flow(self):
        coc = calculate_cash_on_cash(Decimal("0"), Decimal("100000"))
        assert coc == Decimal("0.0000")

    def test_cash_on_cash_zero_invested_raises(self):
        with pytest.raises(
            ZeroDivisionError, match="total_cash_invested must be non-zero"
        ):
            calculate_cash_on_cash(Decimal("10000"), Decimal("0"))

    def test_cash_on_cash_negative_cash_flow(self):
        coc = calculate_cash_on_cash(Decimal("-5000"), Decimal("100000"))
        assert coc == Decimal("-0.0500")


class TestCalculateIrr:
    """Tests for calculate_irr function."""

    def test_basic_irr(self):
        # Initial investment -100000, annual returns 30000 for 5 years
        cashflows = [-100000, 30000, 30000, 30000, 30000, 30000]
        irr = calculate_irr(cashflows)
        # IRR should be approximately 15.24%
        assert irr == Decimal("0.1524")

    def test_irr_with_decimal_inputs(self):
        cashflows = [
            Decimal("-100000"),
            Decimal("50000"),
            Decimal("50000"),
            Decimal("50000"),
        ]
        irr = calculate_irr(cashflows)
        # IRR should be approximately 23.38%
        assert irr == Decimal("0.2338")

    def test_irr_with_string_inputs(self):
        cashflows = ["-100000", "40000", "40000", "40000", "40000"]
        irr = calculate_irr(cashflows)
        assert isinstance(irr, Decimal)
        # Should be around 21.86%
        assert irr == Decimal("0.2186")

    def test_irr_break_even(self):
        # Initial -100000, return 100000 in year 1 => 0% IRR
        cashflows = [-100000, 100000]
        irr = calculate_irr(cashflows)
        assert irr == Decimal("0.0000")

    def test_irr_high_return(self):
        # Initial -50000, return 100000 year 1 => 100% IRR
        cashflows = [-50000, 100000]
        irr = calculate_irr(cashflows)
        assert irr == Decimal("1.0000")


class TestNpv:
    """Tests for npv function."""

    def test_basic_npv(self):
        # 8% discount rate
        cashflows = [-100000, 30000, 30000, 30000, 30000, 30000]
        result = npv(0.08, cashflows)
        # NPV should be approximately 19,781
        assert result == Decimal("19781.30")

    def test_npv_with_decimal_inputs(self):
        cashflows = [
            Decimal("-100000"),
            Decimal("40000"),
            Decimal("40000"),
            Decimal("40000"),
        ]
        result = npv(0.10, cashflows)
        # NPV at 10%
        assert isinstance(result, Decimal)

    def test_npv_zero_discount_rate(self):
        cashflows = [-100, 50, 50, 50]
        result = npv(0.0, cashflows)
        # With 0% discount, NPV = sum of cashflows = 50
        assert result == Decimal("50.00")

    def test_npv_high_discount_rate(self):
        cashflows = [-100000, 50000, 50000, 50000]
        result = npv(0.50, cashflows)
        # High discount rate reduces NPV significantly
        assert result < Decimal("0")

    def test_npv_negative_result(self):
        # Investment doesn't pay off
        cashflows = [-100000, 10000, 10000, 10000]
        result = npv(0.10, cashflows)
        # NPV should be negative
        assert result < 0


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_large_values_noi(self):
        noi = calculate_noi(Decimal("999999999.99"), Decimal("123456789.12"))
        assert noi == Decimal("876543210.87")

    def test_very_small_values_cap_rate(self):
        cap_rate = calculate_cap_rate(Decimal("0.01"), Decimal("1000000"))
        assert cap_rate == Decimal("0.0000")

    def test_precision_preservation(self):
        # Test that we maintain precision through calculations
        result = calculate_noi(Decimal("123456.789"), Decimal("12345.678"))
        assert result == Decimal("111111.11")
