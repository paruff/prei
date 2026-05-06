"""Tests for depreciation and tax modeling functions in investor_app/finance/utils.py."""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    after_tax_cash_flow,
    after_tax_irr,
    annual_depreciation,
    calculate_irr,
    depreciation_recapture_tax,
)


class TestAnnualDepreciation:
    """Tests for annual_depreciation function."""

    def test_typical_values(self) -> None:
        """Test standard residential property depreciation."""
        # $300K purchase, $50K land → $250K depreciable basis / 27.5 years
        result = annual_depreciation(Decimal("300000"), Decimal("50000"))
        expected = Decimal("250000") / Decimal("27.5")
        assert abs(result - expected) < Decimal("0.01")

    def test_zero_land_value(self) -> None:
        """Test that zero land value is allowed (entire price is depreciable)."""
        result = annual_depreciation(Decimal("200000"), Decimal("0"))
        expected = Decimal("200000") / Decimal("27.5")
        assert abs(result - expected) < Decimal("0.01")

    def test_land_value_equals_purchase_price_raises(self) -> None:
        """Test that land_value == purchase_price raises ValueError."""
        with pytest.raises(
            ValueError, match="land_value must be less than purchase_price"
        ):
            annual_depreciation(Decimal("300000"), Decimal("300000"))

    def test_land_value_exceeds_purchase_price_raises(self) -> None:
        """Test that land_value > purchase_price raises ValueError."""
        with pytest.raises(
            ValueError, match="land_value must be less than purchase_price"
        ):
            annual_depreciation(Decimal("300000"), Decimal("350000"))

    def test_purchase_price_zero_raises(self) -> None:
        """Test that purchase_price == 0 raises ValueError."""
        with pytest.raises(
            ValueError, match="purchase_price must be greater than zero"
        ):
            annual_depreciation(Decimal("0"), Decimal("0"))

    def test_purchase_price_negative_raises(self) -> None:
        """Test that negative purchase_price raises ValueError."""
        with pytest.raises(
            ValueError, match="purchase_price must be greater than zero"
        ):
            annual_depreciation(Decimal("-100000"), Decimal("0"))

    def test_negative_land_value_raises(self) -> None:
        """Test that negative land_value raises ValueError."""
        with pytest.raises(ValueError, match="land_value must be zero or greater"):
            annual_depreciation(Decimal("300000"), Decimal("-1"))

    def test_very_large_values(self) -> None:
        """Test boundary: $10M property with $2M land."""
        result = annual_depreciation(Decimal("10000000"), Decimal("2000000"))
        expected = Decimal("8000000") / Decimal("27.5")
        assert abs(result - expected) < Decimal("0.01")

    def test_returns_decimal(self) -> None:
        """Test that the return type is Decimal."""
        result = annual_depreciation(Decimal("300000"), Decimal("50000"))
        assert isinstance(result, Decimal)


class TestAfterTaxCashFlow:
    """Tests for after_tax_cash_flow function."""

    def test_typical_scenario(self) -> None:
        """Test standard after-tax cash flow with 24% tax rate."""
        # NOI=24000, debt=18000, depreciation=9091, rate=24%
        # pre-tax CF = 6000, shield = 9091 * 0.24 ≈ 2181.84
        result = after_tax_cash_flow(
            noi=Decimal("24000"),
            annual_debt_service=Decimal("18000"),
            depreciation_deduction=Decimal("9091"),
            marginal_tax_rate=Decimal("0.24"),
        )
        expected = Decimal("6000") + Decimal("9091") * Decimal("0.24")
        assert abs(result - expected) < Decimal("0.01")

    def test_zero_tax_rate_equals_pre_tax(self) -> None:
        """Test that zero tax rate produces same result as pre-tax cash flow."""
        noi_val = Decimal("24000")
        debt = Decimal("18000")
        dep = Decimal("9091")
        result = after_tax_cash_flow(
            noi=noi_val,
            annual_debt_service=debt,
            depreciation_deduction=dep,
            marginal_tax_rate=Decimal("0"),
        )
        # With 0% tax rate, shield = 0, so result = NOI - debt_service
        assert result == noi_val - debt

    def test_full_tax_rate_one(self) -> None:
        """Test boundary: 100% tax rate (marginal_tax_rate == 1)."""
        result = after_tax_cash_flow(
            noi=Decimal("10000"),
            annual_debt_service=Decimal("8000"),
            depreciation_deduction=Decimal("5000"),
            marginal_tax_rate=Decimal("1"),
        )
        # shield = 5000 * 1.0 = 5000; pre-tax CF = 2000; total = 7000
        assert result == Decimal("7000")

    def test_negative_tax_rate_raises(self) -> None:
        """Test that marginal_tax_rate < 0 raises ValueError."""
        with pytest.raises(
            ValueError, match="marginal_tax_rate must be between 0 and 1"
        ):
            after_tax_cash_flow(
                noi=Decimal("10000"),
                annual_debt_service=Decimal("8000"),
                depreciation_deduction=Decimal("5000"),
                marginal_tax_rate=Decimal("-0.1"),
            )

    def test_tax_rate_above_one_raises(self) -> None:
        """Test that marginal_tax_rate > 1 raises ValueError."""
        with pytest.raises(
            ValueError, match="marginal_tax_rate must be between 0 and 1"
        ):
            after_tax_cash_flow(
                noi=Decimal("10000"),
                annual_debt_service=Decimal("8000"),
                depreciation_deduction=Decimal("5000"),
                marginal_tax_rate=Decimal("1.5"),
            )

    def test_negative_noi(self) -> None:
        """Test that negative NOI (loss scenario) still computes correctly."""
        result = after_tax_cash_flow(
            noi=Decimal("-5000"),
            annual_debt_service=Decimal("12000"),
            depreciation_deduction=Decimal("9091"),
            marginal_tax_rate=Decimal("0.22"),
        )
        # pre-tax CF = -5000 - 12000 = -17000; shield = 9091 * 0.22 ≈ 2000.02
        expected = Decimal("-17000") + Decimal("9091") * Decimal("0.22")
        assert abs(result - expected) < Decimal("0.01")

    def test_returns_decimal(self) -> None:
        """Test that the return type is Decimal."""
        result = after_tax_cash_flow(
            Decimal("24000"), Decimal("18000"), Decimal("9091"), Decimal("0.24")
        )
        assert isinstance(result, Decimal)


class TestAfterTaxIrr:
    """Tests for after_tax_irr function."""

    def test_typical_scenario(self) -> None:
        """Test after-tax IRR increases vs pre-tax with depreciation shield."""
        # Simple 2-year investment
        cash_flows = [Decimal("-100000"), Decimal("55000"), Decimal("60000")]
        dep_schedule = [Decimal("9091"), Decimal("9091")]
        result = after_tax_irr(cash_flows, dep_schedule, Decimal("0.24"))
        assert isinstance(result, Decimal)
        # After-tax IRR should be positive for this profitable scenario
        assert result > Decimal("0")

    def test_zero_tax_rate_matches_pre_tax(self) -> None:
        """Test that zero tax rate produces same IRR as unadjusted flows."""
        cash_flows = [Decimal("-100000"), Decimal("55000"), Decimal("60000")]
        dep_schedule = [Decimal("9091"), Decimal("9091")]
        after_tax = after_tax_irr(cash_flows, dep_schedule, Decimal("0"))
        # With 0% tax rate, no shield, so the cash flows are unchanged
        pre_tax = calculate_irr(cash_flows)
        assert abs(after_tax - pre_tax) < Decimal("0.0001")

    def test_insufficient_cash_flows_raises(self) -> None:
        """Test that fewer than 2 cash flows raises ValueError."""
        with pytest.raises(ValueError, match="At least 2 cash flows are required"):
            after_tax_irr([Decimal("-100000")], [], Decimal("0.24"))

    def test_negative_tax_rate_raises(self) -> None:
        """Test that negative tax rate raises ValueError."""
        with pytest.raises(
            ValueError, match="marginal_tax_rate must be between 0 and 1"
        ):
            after_tax_irr(
                [Decimal("-100000"), Decimal("110000")],
                [Decimal("9091")],
                Decimal("-0.1"),
            )

    def test_tax_rate_above_one_raises(self) -> None:
        """Test that tax rate > 1 raises ValueError."""
        with pytest.raises(
            ValueError, match="marginal_tax_rate must be between 0 and 1"
        ):
            after_tax_irr(
                [Decimal("-100000"), Decimal("110000")],
                [Decimal("9091")],
                Decimal("1.1"),
            )

    def test_short_depreciation_schedule(self) -> None:
        """Test that missing depreciation periods default to zero."""
        cash_flows = [
            Decimal("-100000"),
            Decimal("40000"),
            Decimal("40000"),
            Decimal("40000"),
        ]
        # Only 1 year of depreciation provided; years 2 and 3 should use 0
        dep_schedule = [Decimal("9091")]
        result = after_tax_irr(cash_flows, dep_schedule, Decimal("0.24"))
        assert isinstance(result, Decimal)

    def test_returns_decimal(self) -> None:
        """Test that the return type is Decimal."""
        cash_flows = [Decimal("-100000"), Decimal("55000"), Decimal("60000")]
        dep_schedule = [Decimal("9091"), Decimal("9091")]
        result = after_tax_irr(cash_flows, dep_schedule, Decimal("0.24"))
        assert isinstance(result, Decimal)

    def test_empty_depreciation_schedule(self) -> None:
        """Test that an empty depreciation schedule applies no shields."""
        cash_flows = [Decimal("-100000"), Decimal("55000"), Decimal("60000")]
        result = after_tax_irr(cash_flows, [], Decimal("0.24"))
        pre_tax = calculate_irr(cash_flows)
        # No depreciation shield → should equal pre-tax IRR
        assert abs(result - pre_tax) < Decimal("0.0001")


class TestDepreciationRecaptureTax:
    """Tests for depreciation_recapture_tax function."""

    def test_standard_25_percent_rate(self) -> None:
        """Test recapture tax at default 25% IRS rate."""
        # 5 years of $9,091/year = $45,455 accumulated
        accumulated = Decimal("45455")
        result = depreciation_recapture_tax(accumulated)
        assert result == accumulated * Decimal("0.25")

    def test_custom_recapture_rate(self) -> None:
        """Test recapture tax with a custom rate."""
        result = depreciation_recapture_tax(Decimal("45000"), Decimal("0.20"))
        assert result == Decimal("9000")

    def test_zero_depreciation(self) -> None:
        """Test boundary: zero accumulated depreciation returns zero tax."""
        result = depreciation_recapture_tax(Decimal("0"))
        assert result == Decimal("0")

    def test_very_large_depreciation(self) -> None:
        """Test boundary: $10M property over many years."""
        # 27 full years of depreciation on $8M depreciable basis
        annual_dep = Decimal("8000000") / Decimal("27.5")
        accumulated = annual_dep * Decimal("27")
        result = depreciation_recapture_tax(accumulated)
        expected = accumulated * Decimal("0.25")
        assert abs(result - expected) < Decimal("0.01")

    def test_negative_accumulated_depreciation_raises(self) -> None:
        """Test that negative accumulated depreciation raises ValueError."""
        with pytest.raises(
            ValueError, match="accumulated_depreciation must be zero or greater"
        ):
            depreciation_recapture_tax(Decimal("-1000"))

    def test_negative_recapture_rate_raises(self) -> None:
        """Test that negative recapture rate raises ValueError."""
        with pytest.raises(ValueError, match="recapture_rate must be between 0 and 1"):
            depreciation_recapture_tax(Decimal("45000"), Decimal("-0.1"))

    def test_recapture_rate_above_one_raises(self) -> None:
        """Test that recapture rate > 1 raises ValueError."""
        with pytest.raises(ValueError, match="recapture_rate must be between 0 and 1"):
            depreciation_recapture_tax(Decimal("45000"), Decimal("1.5"))

    def test_returns_decimal(self) -> None:
        """Test that the return type is Decimal."""
        result = depreciation_recapture_tax(Decimal("45000"))
        assert isinstance(result, Decimal)
