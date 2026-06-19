"""Tests for finance utility functions."""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    calculate_after_tax_cashflow,
    calculate_annual_depreciation,
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

    def test_all_positive_flows_raises_error(self) -> None:
        """Test that all-positive cash flows (no sign change) raise ValueError.

        numpy_financial.irr returns nan for flows with no sign change;
        calculate_irr should surface this as a ValueError.
        """
        cash_flows = [Decimal("10000"), Decimal("20000"), Decimal("30000")]
        with pytest.raises(ValueError, match="IRR could not be computed"):
            calculate_irr(cash_flows)


# ── Depreciation & After-Tax Cash Flow Tests ─────────────────────────────────


class TestCalculateAnnualDepreciation:
    """Tests for calculate_annual_depreciation function."""

    def test_basic_depreciation(self) -> None:
        """Test depreciation with $200k property, 20% land."""
        result = calculate_annual_depreciation(Decimal("200000"), Decimal("0.20"))
        expected = Decimal("200000") * Decimal("0.80") / Decimal("27.5")
        assert result == expected

    def test_default_land_value_pct(self) -> None:
        """Test that land_value_pct defaults to 0.20."""
        result = calculate_annual_depreciation(Decimal("300000"))
        expected = Decimal("300000") * Decimal("0.80") / Decimal("27.5")
        assert result == expected

    def test_zero_land(self) -> None:
        """Test depreciation with 0% land (all improvement)."""
        result = calculate_annual_depreciation(Decimal("200000"), Decimal("0"))
        expected = Decimal("200000") / Decimal("27.5")
        assert result == expected

    def test_high_land_value(self) -> None:
        """Test depreciation with 40% land."""
        result = calculate_annual_depreciation(Decimal("500000"), Decimal("0.40"))
        expected = Decimal("500000") * Decimal("0.60") / Decimal("27.5")
        assert result == expected

    def test_returns_decimal(self) -> None:
        """Test that result is a Decimal type."""
        result = calculate_annual_depreciation(Decimal("200000"), Decimal("0.20"))
        assert isinstance(result, Decimal)

    def test_zero_purchase_price_raises_error(self) -> None:
        """Test that zero purchase price raises ValueError."""
        with pytest.raises(ValueError, match="purchase_price must be greater than zero"):
            calculate_annual_depreciation(Decimal("0"), Decimal("0.20"))

    def test_negative_purchase_price_raises_error(self) -> None:
        """Test that negative purchase price raises ValueError."""
        with pytest.raises(ValueError, match="purchase_price must be greater than zero"):
            calculate_annual_depreciation(Decimal("-100000"), Decimal("0.20"))

    def test_land_value_pct_too_high_raises_error(self) -> None:
        """Test that land_value_pct >= 1 raises ValueError."""
        with pytest.raises(ValueError, match="land_value_pct must be in \\[0, 1\\)"):
            calculate_annual_depreciation(Decimal("200000"), Decimal("1.0"))

    def test_land_value_pct_negative_raises_error(self) -> None:
        """Test that negative land_value_pct raises ValueError."""
        with pytest.raises(ValueError, match="land_value_pct must be in \\[0, 1\\)"):
            calculate_annual_depreciation(Decimal("200000"), Decimal("-0.10"))

    def test_decimal_precision(self) -> None:
        """Test that result preserves decimal precision."""
        result = calculate_annual_depreciation(Decimal("250000"), Decimal("0.25"))
        # improvement = 250000 * 0.75 = 187500
        # annual = 187500 / 27.5 = 6818.1818...
        assert result == Decimal("187500") / Decimal("27.5")


class TestCalculateAfterTaxCashflow:
    """Tests for calculate_after_tax_cashflow function."""

    def test_taxable_profit(self) -> None:
        """Test after-tax with positive taxable income."""
        # $6000 cashflow, $5818 depreciation, 32% tax
        # taxable = 6000 - 5818 = 182
        # tax = 182 * 0.32 = 58.24
        # after_tax = 6000 - 58.24 = 5941.76
        result = calculate_after_tax_cashflow(
            Decimal("6000"), Decimal("5818"), Decimal("0.32")
        )
        assert abs(result - Decimal("5941.76")) < Decimal("0.01")

    def test_paper_loss(self) -> None:
        """Test after-tax with paper loss (depreciation exceeds cashflow)."""
        # $3000 cashflow, $5818 depreciation, 32% tax
        # taxable = 3000 - 5818 = -2818 (paper loss)
        # tax_savings = 2818 * 0.32 = 901.76
        # after_tax = 3000 + 901.76 = 3901.76
        result = calculate_after_tax_cashflow(
            Decimal("3000"), Decimal("5818"), Decimal("0.32")
        )
        assert abs(result - Decimal("3901.76")) < Decimal("0.01")

    def test_zero_depreciation(self) -> None:
        """Test after-tax with no depreciation."""
        # $10000 cashflow, $0 depreciation, 24% tax
        # taxable = 10000 - 0 = 10000
        # tax = 10000 * 0.24 = 2400
        # after_tax = 10000 - 2400 = 7600
        result = calculate_after_tax_cashflow(
            Decimal("10000"), Decimal("0"), Decimal("0.24")
        )
        assert result == Decimal("7600")

    def test_zero_tax_rate(self) -> None:
        """Test after-tax with 0% tax rate."""
        result = calculate_after_tax_cashflow(
            Decimal("6000"), Decimal("5818"), Decimal("0")
        )
        assert result == Decimal("6000")

    def test_high_depreciation(self) -> None:
        """Test after-tax with large depreciation creating significant tax savings."""
        # $2000 cashflow, $10000 depreciation, 35% tax
        # taxable = 2000 - 10000 = -8000 (paper loss)
        # tax_savings = 8000 * 0.35 = 2800
        # after_tax = 2000 + 2800 = 4800
        result = calculate_after_tax_cashflow(
            Decimal("2000"), Decimal("10000"), Decimal("0.35")
        )
        assert result == Decimal("4800")

    def test_returns_decimal(self) -> None:
        """Test that result is a Decimal type."""
        result = calculate_after_tax_cashflow(
            Decimal("6000"), Decimal("5818"), Decimal("0.32")
        )
        assert isinstance(result, Decimal)

    def test_tax_rate_too_high_raises_error(self) -> None:
        """Test that tax rate > 1 raises ValueError."""
        with pytest.raises(ValueError, match="marginal_tax_rate must be in \\[0, 1\\]"):
            calculate_after_tax_cashflow(
                Decimal("6000"), Decimal("5818"), Decimal("1.5")
            )

    def test_negative_tax_rate_raises_error(self) -> None:
        """Test that negative tax rate raises ValueError."""
        with pytest.raises(ValueError, match="marginal_tax_rate must be in \\[0, 1\\]"):
            calculate_after_tax_cashflow(
                Decimal("6000"), Decimal("5818"), Decimal("-0.10")
            )

    def test_exact_known_test_case(self) -> None:
        """Test the exact example from the issue specification."""
        result = calculate_after_tax_cashflow(
            Decimal("6000"), Decimal("5818"), Decimal("0.32")
        )
        assert abs(result - Decimal("5941.76")) < Decimal("0.01")
