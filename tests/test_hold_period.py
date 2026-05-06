"""Tests for hold period & exit analysis functions in investor_app/finance/utils.py."""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    net_sale_proceeds,
    project_annual_cash_flows,
    project_property_value,
    total_return_summary,
)


class TestProjectAnnualCashFlows:
    """Tests for project_annual_cash_flows function."""

    def test_hold_years_1_boundary(self) -> None:
        """Boundary: hold_years=1 returns a single-element list."""
        flows = project_annual_cash_flows(
            Decimal("36000"),
            Decimal("12000"),
            Decimal("18000"),
            Decimal("0.03"),
            Decimal("0.02"),
            1,
        )
        assert len(flows) == 1
        # Year 1: NOI = 36000 - 12000 = 24000; CF = 24000 - 18000 = 6000
        assert flows[0] == Decimal("6000")

    def test_hold_years_30_boundary(self) -> None:
        """Boundary: hold_years=30 returns a 30-element list."""
        flows = project_annual_cash_flows(
            Decimal("36000"),
            Decimal("12000"),
            Decimal("18000"),
            Decimal("0.03"),
            Decimal("0.02"),
            30,
        )
        assert len(flows) == 30

    def test_hold_years_0_raises(self) -> None:
        """Boundary: hold_years=0 should raise ValueError."""
        with pytest.raises(ValueError, match="hold_years must be between 1 and 50"):
            project_annual_cash_flows(
                Decimal("36000"),
                Decimal("12000"),
                Decimal("18000"),
                Decimal("0.03"),
                Decimal("0.02"),
                0,
            )

    def test_hold_years_51_raises(self) -> None:
        """hold_years=51 exceeds maximum and should raise ValueError."""
        with pytest.raises(ValueError, match="hold_years must be between 1 and 50"):
            project_annual_cash_flows(
                Decimal("36000"),
                Decimal("12000"),
                Decimal("18000"),
                Decimal("0.03"),
                Decimal("0.02"),
                51,
            )

    def test_hold_years_negative_raises(self) -> None:
        """Negative hold_years should raise ValueError."""
        with pytest.raises(ValueError, match="hold_years must be between 1 and 50"):
            project_annual_cash_flows(
                Decimal("36000"),
                Decimal("12000"),
                Decimal("18000"),
                Decimal("0.03"),
                Decimal("0.02"),
                -1,
            )

    def test_zero_rent_growth_flat_cash_flows(self) -> None:
        """Zero rent growth rate produces identical gross rent each year."""
        flows = project_annual_cash_flows(
            Decimal("36000"),
            Decimal("12000"),
            Decimal("18000"),
            Decimal("0.00"),  # no rent growth
            Decimal("0.00"),  # no expense growth
            5,
        )
        # All cash flows should be the same: 36000 - 12000 - 18000 = 6000
        assert all(cf == Decimal("6000") for cf in flows)

    def test_rent_grows_expenses_flat(self) -> None:
        """Rent growing while expenses stay flat should increase cash flow each year."""
        flows = project_annual_cash_flows(
            Decimal("36000"),
            Decimal("12000"),
            Decimal("18000"),
            Decimal("0.05"),
            Decimal("0.00"),
            3,
        )
        assert flows[1] > flows[0]
        assert flows[2] > flows[1]

    def test_rent_growth_rate_too_high_raises(self) -> None:
        """rent_growth_rate > 0.5 should raise ValueError."""
        with pytest.raises(ValueError, match="rent_growth_rate must be in"):
            project_annual_cash_flows(
                Decimal("36000"),
                Decimal("12000"),
                Decimal("18000"),
                Decimal("0.6"),
                Decimal("0.02"),
                5,
            )

    def test_expense_growth_rate_too_low_raises(self) -> None:
        """expense_growth_rate < -0.5 should raise ValueError."""
        with pytest.raises(ValueError, match="expense_growth_rate must be in"):
            project_annual_cash_flows(
                Decimal("36000"),
                Decimal("12000"),
                Decimal("18000"),
                Decimal("0.03"),
                Decimal("-0.6"),
                5,
            )

    def test_negative_cash_flow_when_expenses_exceed_noi(self) -> None:
        """Cash flow can be negative when debt service exceeds NOI."""
        flows = project_annual_cash_flows(
            Decimal("20000"),
            Decimal("10000"),
            Decimal("15000"),  # debt > NOI
            Decimal("0.00"),
            Decimal("0.00"),
            1,
        )
        # NOI = 10000, debt = 15000 → CF = -5000
        assert flows[0] == Decimal("-5000")

    def test_returns_list_of_decimals(self) -> None:
        """All returned elements should be Decimal instances."""
        flows = project_annual_cash_flows(
            Decimal("36000"),
            Decimal("12000"),
            Decimal("18000"),
            Decimal("0.03"),
            Decimal("0.02"),
            5,
        )
        assert all(isinstance(cf, Decimal) for cf in flows)

    def test_very_large_values(self) -> None:
        """$10M property scenario should not raise or overflow."""
        flows = project_annual_cash_flows(
            Decimal("600000"),  # gross rent year 1
            Decimal("200000"),  # opex year 1
            Decimal("350000"),  # annual debt service
            Decimal("0.03"),
            Decimal("0.02"),
            10,
        )
        assert len(flows) == 10
        assert all(isinstance(cf, Decimal) for cf in flows)

    def test_year1_values_not_compounded(self) -> None:
        """Year 1 uses growth rates to the power of 0 (no compounding)."""
        flows = project_annual_cash_flows(
            Decimal("36000"),
            Decimal("12000"),
            Decimal("18000"),
            Decimal("0.03"),
            Decimal("0.02"),
            1,
        )
        # Year 1: (1+r)^0 = 1, so rent=36000, opex=12000, NOI=24000, CF=6000
        assert flows[0] == Decimal("6000")


class TestProjectPropertyValue:
    """Tests for project_property_value function."""

    def test_zero_appreciation_rate_value_unchanged(self) -> None:
        """Zero appreciation rate should return the purchase price unchanged."""
        result = project_property_value(Decimal("300000"), Decimal("0"), 10)
        assert result == Decimal("300000")

    def test_positive_appreciation(self) -> None:
        """Positive appreciation should produce a value greater than purchase price."""
        result = project_property_value(Decimal("300000"), Decimal("0.03"), 10)
        assert result > Decimal("300000")

    def test_negative_appreciation_market_downturn(self) -> None:
        """Negative appreciation (market downturn) should produce a lower value."""
        result = project_property_value(Decimal("300000"), Decimal("-0.05"), 5)
        assert result < Decimal("300000")

    def test_appreciation_rate_below_minus_one_raises(self) -> None:
        """appreciation_rate < -1 should raise ValueError."""
        with pytest.raises(
            ValueError, match="appreciation_rate must be greater than -1"
        ):
            project_property_value(Decimal("300000"), Decimal("-1.1"), 10)

    def test_appreciation_rate_exactly_minus_one_allowed(self) -> None:
        """appreciation_rate == -1 is the boundary; strictly -1 means total value loss."""
        # The spec raises only for rate < -1; rate == -1 is allowed (value goes to 0)
        result = project_property_value(Decimal("300000"), Decimal("-1"), 1)
        assert result == Decimal("0")

    def test_hold_years_1_boundary(self) -> None:
        """hold_years=1 should return one year of appreciation."""
        result = project_property_value(Decimal("300000"), Decimal("0.03"), 1)
        expected = Decimal("300000") * Decimal("1.03")
        assert abs(result - expected) < Decimal("0.01")

    def test_hold_years_30_boundary(self) -> None:
        """hold_years=30 should not raise."""
        result = project_property_value(Decimal("300000"), Decimal("0.03"), 30)
        assert isinstance(result, Decimal)
        assert result > Decimal("300000")

    def test_hold_years_0_raises(self) -> None:
        """hold_years=0 should raise ValueError."""
        with pytest.raises(ValueError, match="hold_years must be between 1 and 50"):
            project_property_value(Decimal("300000"), Decimal("0.03"), 0)

    def test_hold_years_51_raises(self) -> None:
        """hold_years=51 exceeds maximum and should raise ValueError."""
        with pytest.raises(ValueError, match="hold_years must be between 1 and 50"):
            project_property_value(Decimal("300000"), Decimal("0.03"), 51)

    def test_purchase_price_zero_raises(self) -> None:
        """purchase_price=0 should raise ValueError."""
        with pytest.raises(
            ValueError, match="purchase_price must be greater than zero"
        ):
            project_property_value(Decimal("0"), Decimal("0.03"), 10)

    def test_purchase_price_negative_raises(self) -> None:
        """Negative purchase_price should raise ValueError."""
        with pytest.raises(
            ValueError, match="purchase_price must be greater than zero"
        ):
            project_property_value(Decimal("-100000"), Decimal("0.03"), 10)

    def test_very_large_values(self) -> None:
        """$10M property should not raise or overflow."""
        result = project_property_value(Decimal("10000000"), Decimal("0.03"), 10)
        assert isinstance(result, Decimal)
        assert result > Decimal("10000000")

    def test_returns_decimal(self) -> None:
        """Return type should be Decimal."""
        result = project_property_value(Decimal("300000"), Decimal("0.03"), 10)
        assert isinstance(result, Decimal)

    def test_compound_calculation(self) -> None:
        """Verify compound appreciation formula: price × (1 + rate)^years."""
        price = Decimal("300000")
        rate = Decimal("0.05")
        years = 5
        result = project_property_value(price, rate, years)
        expected = price * (Decimal("1") + rate) ** years
        assert abs(result - expected) < Decimal("0.001")


class TestNetSaleProceeds:
    """Tests for net_sale_proceeds function."""

    def test_typical_profitable_sale(self) -> None:
        """Standard scenario: sale above purchase price with capital gains."""
        result = net_sale_proceeds(
            sale_price=Decimal("400000"),
            original_purchase_price=Decimal("300000"),
            outstanding_loan_balance=Decimal("200000"),
            accumulated_depreciation=Decimal("45000"),
        )
        # Commissions: 400000 × 0.06 = 24000
        # Closing: 400000 × 0.01 = 4000
        # Loan payoff: 200000
        # Gross proceeds: 400000 - 24000 - 4000 - 200000 = 172000
        # Capital gain: 400000 - 300000 = 100000; CG tax: 100000 × 0.15 = 15000
        # Recapture: 45000 × 0.25 = 11250
        # Net: 172000 - 15000 - 11250 = 145750
        assert abs(result - Decimal("145750")) < Decimal("0.01")

    def test_property_declined_no_capital_gains_tax(self) -> None:
        """When sale price < purchase price, no capital gains tax is owed."""
        result = net_sale_proceeds(
            sale_price=Decimal("250000"),
            original_purchase_price=Decimal("300000"),  # sold at a loss
            outstanding_loan_balance=Decimal("200000"),
            accumulated_depreciation=Decimal("30000"),
            long_term_cg_rate=Decimal("0.15"),
            depreciation_recapture_rate=Decimal("0.25"),
        )
        # Capital gain = 250000 - 300000 = -50000 → clamped to 0; no CG tax
        # Commissions: 250000 × 0.06 = 15000
        # Closing: 250000 × 0.01 = 2500
        # Gross: 250000 - 15000 - 2500 - 200000 = 32500
        # Recapture: 30000 × 0.25 = 7500
        # Net: 32500 - 7500 = 25000
        assert abs(result - Decimal("25000")) < Decimal("0.01")

    def test_zero_loan_balance(self) -> None:
        """Free-and-clear property (no mortgage) includes no loan payoff."""
        result = net_sale_proceeds(
            sale_price=Decimal("400000"),
            original_purchase_price=Decimal("300000"),
            outstanding_loan_balance=Decimal("0"),
            accumulated_depreciation=Decimal("45000"),
        )
        # Gross: 400000 - 24000 - 4000 - 0 = 372000
        # CG tax: 100000 × 0.15 = 15000
        # Recapture: 45000 × 0.25 = 11250
        # Net: 372000 - 15000 - 11250 = 345750
        assert abs(result - Decimal("345750")) < Decimal("0.01")

    def test_zero_accumulated_depreciation(self) -> None:
        """No prior depreciation means no recapture tax."""
        result = net_sale_proceeds(
            sale_price=Decimal("400000"),
            original_purchase_price=Decimal("300000"),
            outstanding_loan_balance=Decimal("200000"),
            accumulated_depreciation=Decimal("0"),
        )
        # No recapture; CG tax still applies
        expected = (
            Decimal("400000")
            - Decimal("400000") * Decimal("0.06")
            - Decimal("400000") * Decimal("0.01")
            - Decimal("200000")
            - Decimal("100000") * Decimal("0.15")
        )
        assert abs(result - expected) < Decimal("0.01")

    def test_negative_loan_balance_raises(self) -> None:
        """Negative outstanding_loan_balance should raise ValueError."""
        with pytest.raises(
            ValueError, match="outstanding_loan_balance must be zero or greater"
        ):
            net_sale_proceeds(
                sale_price=Decimal("400000"),
                original_purchase_price=Decimal("300000"),
                outstanding_loan_balance=Decimal("-1000"),
                accumulated_depreciation=Decimal("45000"),
            )

    def test_negative_accumulated_depreciation_raises(self) -> None:
        """Negative accumulated_depreciation should raise ValueError."""
        with pytest.raises(
            ValueError, match="accumulated_depreciation must be zero or greater"
        ):
            net_sale_proceeds(
                sale_price=Decimal("400000"),
                original_purchase_price=Decimal("300000"),
                outstanding_loan_balance=Decimal("200000"),
                accumulated_depreciation=Decimal("-1000"),
            )

    def test_commission_rate_above_one_raises(self) -> None:
        """agent_commission_rate > 1 should raise ValueError."""
        with pytest.raises(
            ValueError, match="agent_commission_rate must be between 0 and 1"
        ):
            net_sale_proceeds(
                sale_price=Decimal("400000"),
                original_purchase_price=Decimal("300000"),
                outstanding_loan_balance=Decimal("200000"),
                accumulated_depreciation=Decimal("45000"),
                agent_commission_rate=Decimal("1.5"),
            )

    def test_custom_rates(self) -> None:
        """Custom rate parameters should be honored."""
        result = net_sale_proceeds(
            sale_price=Decimal("500000"),
            original_purchase_price=Decimal("400000"),
            outstanding_loan_balance=Decimal("300000"),
            accumulated_depreciation=Decimal("50000"),
            agent_commission_rate=Decimal("0.05"),
            closing_cost_rate=Decimal("0.02"),
            long_term_cg_rate=Decimal("0.20"),
            depreciation_recapture_rate=Decimal("0.25"),
        )
        # Commissions: 500000 × 0.05 = 25000
        # Closing: 500000 × 0.02 = 10000
        # Gross: 500000 - 25000 - 10000 - 300000 = 165000
        # CG tax: (500000 - 400000) × 0.20 = 20000
        # Recapture: 50000 × 0.25 = 12500
        # Net: 165000 - 20000 - 12500 = 132500
        assert abs(result - Decimal("132500")) < Decimal("0.01")

    def test_returns_decimal(self) -> None:
        """Return type should be Decimal."""
        result = net_sale_proceeds(
            sale_price=Decimal("400000"),
            original_purchase_price=Decimal("300000"),
            outstanding_loan_balance=Decimal("200000"),
            accumulated_depreciation=Decimal("45000"),
        )
        assert isinstance(result, Decimal)

    def test_very_large_values(self) -> None:
        """$10M property scenario should not raise or overflow."""
        result = net_sale_proceeds(
            sale_price=Decimal("12000000"),
            original_purchase_price=Decimal("10000000"),
            outstanding_loan_balance=Decimal("6000000"),
            accumulated_depreciation=Decimal("800000"),
        )
        assert isinstance(result, Decimal)


class TestTotalReturnSummary:
    """Tests for total_return_summary function."""

    def test_typical_scenario(self) -> None:
        """Standard 10-year hold with positive returns."""
        annual_cfs = [Decimal("6000")] * 10
        nsp = Decimal("120000")
        result = total_return_summary(
            Decimal("300000"), Decimal("60000"), annual_cfs, nsp
        )

        assert result["total_cash_flow"] == Decimal("60000")
        assert result["net_sale_proceeds"] == Decimal("120000")
        assert result["total_return"] == Decimal("180000")
        assert abs(result["total_return_on_equity"] - Decimal("3.0")) < Decimal(
            "0.0001"
        )
        assert isinstance(result["annualized_irr"], Decimal)

    def test_dict_keys_present(self) -> None:
        """All expected keys must be present in the returned dict."""
        result = total_return_summary(
            Decimal("300000"),
            Decimal("60000"),
            [Decimal("6000")] * 5,
            Decimal("60000"),
        )
        expected_keys = {
            "total_cash_flow",
            "net_sale_proceeds",
            "total_return",
            "total_return_on_equity",
            "annualized_irr",
        }
        assert set(result.keys()) == expected_keys

    def test_empty_annual_cash_flows_raises(self) -> None:
        """Empty annual_cash_flows list should raise ValueError."""
        with pytest.raises(
            ValueError, match="annual_cash_flows must contain at least one element"
        ):
            total_return_summary(
                Decimal("300000"), Decimal("60000"), [], Decimal("120000")
            )

    def test_negative_down_payment_raises(self) -> None:
        """Negative down_payment should raise ValueError."""
        with pytest.raises(ValueError, match="down_payment must be zero or greater"):
            total_return_summary(
                Decimal("300000"),
                Decimal("-1000"),
                [Decimal("6000")],
                Decimal("120000"),
            )

    def test_zero_down_payment_returns_zero_roe(self) -> None:
        """When down_payment is zero, total_return_on_equity should be 0 (no division)."""
        result = total_return_summary(
            Decimal("300000"),
            Decimal("0"),
            [Decimal("6000")],
            Decimal("60000"),
        )
        assert result["total_return_on_equity"] == Decimal("0")

    def test_negative_cash_flows(self) -> None:
        """Negative annual cash flows produce correct totals."""
        annual_cfs = [Decimal("-3000")] * 5
        result = total_return_summary(
            Decimal("300000"), Decimal("60000"), annual_cfs, Decimal("100000")
        )
        assert result["total_cash_flow"] == Decimal("-15000")
        assert result["total_return"] == Decimal("85000")

    def test_single_year_hold(self) -> None:
        """One-year hold should compute correctly."""
        result = total_return_summary(
            Decimal("300000"),
            Decimal("60000"),
            [Decimal("10000")],
            Decimal("50000"),
        )
        assert result["total_cash_flow"] == Decimal("10000")
        assert result["total_return"] == Decimal("60000")

    def test_irr_is_decimal(self) -> None:
        """annualized_irr must be a Decimal instance."""
        result = total_return_summary(
            Decimal("300000"),
            Decimal("60000"),
            [Decimal("6000")] * 10,
            Decimal("120000"),
        )
        assert isinstance(result["annualized_irr"], Decimal)

    def test_very_large_values(self) -> None:
        """$10M property scenario should not raise or overflow."""
        annual_cfs = [Decimal("50000")] * 10
        result = total_return_summary(
            Decimal("10000000"),
            Decimal("2000000"),
            annual_cfs,
            Decimal("3000000"),
        )
        assert isinstance(result["total_return"], Decimal)
        assert result["total_cash_flow"] == Decimal("500000")

    def test_positive_irr_for_profitable_deal(self) -> None:
        """A profitable deal (positive cash flows + positive exit) should yield positive IRR."""
        annual_cfs = [Decimal("8000")] * 10
        result = total_return_summary(
            Decimal("300000"),
            Decimal("60000"),
            annual_cfs,
            Decimal("150000"),
        )
        assert result["annualized_irr"] > Decimal("0")
