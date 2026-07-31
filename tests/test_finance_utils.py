"""Tests for finance utility functions."""

from decimal import Decimal

import pytest

from investor_app.finance.taxes import (
    calculate_after_tax_cashflow,
    calculate_annual_depreciation,
)


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
        with pytest.raises(
            ValueError, match="purchase_price must be greater than zero"
        ):
            calculate_annual_depreciation(Decimal("0"), Decimal("0.20"))

    def test_negative_purchase_price_raises_error(self) -> None:
        """Test that negative purchase price raises ValueError."""
        with pytest.raises(
            ValueError, match="purchase_price must be greater than zero"
        ):
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
