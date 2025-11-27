"""Tests for finance utility functions."""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    calculate_cap_rate,
    calculate_cash_on_cash,
    calculate_irr,
    calculate_noi,
)


class TestCalculateNoi:
    """Tests for calculate_noi function."""

    def test_positive_noi(self) -> None:
        """Test NOI calculation with positive result."""
        gross_income = Decimal("120000")
        operating_expenses = Decimal("40000")
        result = calculate_noi(gross_income, operating_expenses)
        assert result == Decimal("80000")

    def test_negative_noi(self) -> None:
        """Test NOI calculation with negative result."""
        gross_income = Decimal("30000")
        operating_expenses = Decimal("45000")
        result = calculate_noi(gross_income, operating_expenses)
        assert result == Decimal("-15000")

    def test_zero_noi(self) -> None:
        """Test NOI calculation with zero result."""
        gross_income = Decimal("50000")
        operating_expenses = Decimal("50000")
        result = calculate_noi(gross_income, operating_expenses)
        assert result == Decimal("0")

    def test_decimal_precision(self) -> None:
        """Test that NOI preserves decimal precision."""
        gross_income = Decimal("100000.55")
        operating_expenses = Decimal("33333.33")
        result = calculate_noi(gross_income, operating_expenses)
        assert result == Decimal("66667.22")


class TestCalculateCapRate:
    """Tests for calculate_cap_rate function."""

    def test_typical_cap_rate(self) -> None:
        """Test cap rate calculation with typical values."""
        noi = Decimal("80000")
        property_value = Decimal("1000000")
        result = calculate_cap_rate(noi, property_value)
        assert result == Decimal("0.08")

    def test_high_cap_rate(self) -> None:
        """Test cap rate calculation with high return."""
        noi = Decimal("150000")
        property_value = Decimal("1000000")
        result = calculate_cap_rate(noi, property_value)
        assert result == Decimal("0.15")

    def test_zero_property_value_raises_error(self) -> None:
        """Test that zero property value raises ValueError."""
        noi = Decimal("80000")
        property_value = Decimal("0")
        with pytest.raises(ValueError, match="Property value cannot be zero"):
            calculate_cap_rate(noi, property_value)

    def test_decimal_precision(self) -> None:
        """Test that cap rate preserves decimal precision."""
        noi = Decimal("75000")
        property_value = Decimal("1000000")
        result = calculate_cap_rate(noi, property_value)
        assert result == Decimal("0.075")


class TestCalculateCashOnCash:
    """Tests for calculate_cash_on_cash function."""

    def test_typical_cash_on_cash(self) -> None:
        """Test cash-on-cash calculation with typical values."""
        annual_cash_flow = Decimal("20000")
        total_cash_invested = Decimal("200000")
        result = calculate_cash_on_cash(annual_cash_flow, total_cash_invested)
        assert result == Decimal("0.1")

    def test_high_cash_on_cash(self) -> None:
        """Test cash-on-cash calculation with high return."""
        annual_cash_flow = Decimal("50000")
        total_cash_invested = Decimal("200000")
        result = calculate_cash_on_cash(annual_cash_flow, total_cash_invested)
        assert result == Decimal("0.25")

    def test_negative_cash_flow(self) -> None:
        """Test cash-on-cash with negative cash flow."""
        annual_cash_flow = Decimal("-10000")
        total_cash_invested = Decimal("200000")
        result = calculate_cash_on_cash(annual_cash_flow, total_cash_invested)
        assert result == Decimal("-0.05")

    def test_zero_cash_invested_raises_error(self) -> None:
        """Test that zero cash invested raises ValueError."""
        annual_cash_flow = Decimal("20000")
        total_cash_invested = Decimal("0")
        with pytest.raises(ValueError, match="Total cash invested cannot be zero"):
            calculate_cash_on_cash(annual_cash_flow, total_cash_invested)


class TestCalculateIrr:
    """Tests for calculate_irr function."""

    def test_positive_irr(self) -> None:
        """Test IRR calculation with positive returns."""
        cash_flows = [
            Decimal("-100000"),
            Decimal("30000"),
            Decimal("35000"),
            Decimal("40000"),
            Decimal("45000"),
        ]
        result = calculate_irr(cash_flows)
        # IRR should be approximately 15-20%
        assert Decimal("0.10") < result < Decimal("0.25")

    def test_negative_irr(self) -> None:
        """Test IRR calculation with negative returns."""
        cash_flows = [
            Decimal("-100000"),
            Decimal("10000"),
            Decimal("10000"),
            Decimal("10000"),
        ]
        result = calculate_irr(cash_flows)
        assert result < Decimal("0")

    def test_simple_irr(self) -> None:
        """Test IRR with simple doubling investment."""
        # If you invest 100 and get 200 back in year 1, IRR = 100%
        cash_flows = [Decimal("-100"), Decimal("200")]
        result = calculate_irr(cash_flows)
        assert abs(result - Decimal("1.0")) < Decimal("0.0001")

    def test_insufficient_cash_flows_raises_error(self) -> None:
        """Test that fewer than 2 cash flows raises ValueError."""
        cash_flows = [Decimal("-100000")]
        with pytest.raises(ValueError, match="At least 2 cash flows are required"):
            calculate_irr(cash_flows)

    def test_empty_cash_flows_raises_error(self) -> None:
        """Test that empty cash flows raises ValueError."""
        cash_flows: list[Decimal] = []
        with pytest.raises(ValueError, match="At least 2 cash flows are required"):
            calculate_irr(cash_flows)

    def test_returns_decimal(self) -> None:
        """Test that IRR returns a Decimal type."""
        cash_flows = [Decimal("-100"), Decimal("110")]
        result = calculate_irr(cash_flows)
        assert isinstance(result, Decimal)
