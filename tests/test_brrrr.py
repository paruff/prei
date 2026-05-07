"""Tests for BRRRR strategy finance utility functions.

Covers:
- estimate_arv
- estimate_rehab_cost
- max_refinance_loan
- cash_left_in_deal
- brrrr_coc_return
"""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    brrrr_coc_return,
    cash_left_in_deal,
    estimate_arv,
    estimate_rehab_cost,
    max_refinance_loan,
)

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_COST_PER_SQFT: dict[str, Decimal] = {
    "cosmetic": Decimal("15"),
    "moderate": Decimal("35"),
    "full_gut": Decimal("75"),
}


# ---------------------------------------------------------------------------
# estimate_arv
# ---------------------------------------------------------------------------


class TestEstimateArv:
    """Tests for estimate_arv()."""

    def test_single_comp(self) -> None:
        """Single comparable — ARV equals price-per-sqft × subject sqft."""
        comps = [(Decimal("200000"), Decimal("1000"))]
        result = estimate_arv(comps, Decimal("1000"))
        assert result == Decimal("200000")

    def test_multiple_comps_median_ppsf(self) -> None:
        """Three comps — median PPSF is used, not average."""
        comps = [
            (Decimal("100000"), Decimal("1000")),  # ppsf = 100
            (Decimal("200000"), Decimal("1000")),  # ppsf = 200
            (Decimal("300000"), Decimal("1000")),  # ppsf = 300
        ]
        # Median PPSF = 200 → ARV = 200 × 1200
        result = estimate_arv(comps, Decimal("1200"))
        assert result == Decimal("240000")

    def test_comps_with_varying_sqft(self) -> None:
        """Comps of different sizes — PPSF normalises correctly."""
        comps = [
            (Decimal("150000"), Decimal("1500")),  # ppsf = 100
            (Decimal("300000"), Decimal("2000")),  # ppsf = 150
        ]
        # Median of [100, 150] = 125 → ARV = 125 × 1000
        result = estimate_arv(comps, Decimal("1000"))
        assert result == Decimal("125000")

    def test_empty_comps_raises(self) -> None:
        """Empty comparables list must raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            estimate_arv([], Decimal("1000"))

    def test_comp_sqft_zero_raises(self) -> None:
        """Comparable with sqft = 0 must raise ValueError."""
        comps = [(Decimal("200000"), Decimal("0"))]
        with pytest.raises(ValueError, match="sqft must be greater than zero"):
            estimate_arv(comps, Decimal("1000"))

    def test_comp_price_zero_raises(self) -> None:
        """Comparable with price = 0 must raise ValueError."""
        comps = [(Decimal("0"), Decimal("1000"))]
        with pytest.raises(ValueError, match="price must be greater than zero"):
            estimate_arv(comps, Decimal("1000"))

    def test_comp_price_negative_raises(self) -> None:
        """Comparable with negative price must raise ValueError."""
        comps = [(Decimal("-100"), Decimal("1000"))]
        with pytest.raises(ValueError, match="price must be greater than zero"):
            estimate_arv(comps, Decimal("1000"))

    def test_comp_sqft_negative_raises(self) -> None:
        """Comparable with negative sqft must raise ValueError."""
        comps = [(Decimal("200000"), Decimal("-500"))]
        with pytest.raises(ValueError, match="sqft must be greater than zero"):
            estimate_arv(comps, Decimal("1000"))

    def test_subject_sqft_zero_raises(self) -> None:
        """Subject sqft = 0 must raise ValueError."""
        comps = [(Decimal("200000"), Decimal("1000"))]
        with pytest.raises(ValueError, match="subject_sqft must be greater than zero"):
            estimate_arv(comps, Decimal("0"))

    def test_subject_sqft_negative_raises(self) -> None:
        """Negative subject sqft must raise ValueError."""
        comps = [(Decimal("200000"), Decimal("1000"))]
        with pytest.raises(ValueError, match="subject_sqft must be greater than zero"):
            estimate_arv(comps, Decimal("-1"))

    def test_large_values(self) -> None:
        """Very large purchase prices are handled without overflow."""
        comps = [(Decimal("5000000"), Decimal("5000"))]  # ppsf = 1000
        result = estimate_arv(comps, Decimal("10000"))
        assert result == Decimal("10000000")

    def test_even_number_of_comps_uses_median(self) -> None:
        """Even number of comps — median is the average of the two middle values."""
        comps = [
            (Decimal("100000"), Decimal("1000")),  # ppsf = 100
            (Decimal("200000"), Decimal("1000")),  # ppsf = 200
            (Decimal("300000"), Decimal("1000")),  # ppsf = 300
            (Decimal("400000"), Decimal("1000")),  # ppsf = 400
        ]
        # Median of [100, 200, 300, 400] = 250 → ARV = 250 × 1000
        result = estimate_arv(comps, Decimal("1000"))
        assert result == Decimal("250000")


# ---------------------------------------------------------------------------
# estimate_rehab_cost
# ---------------------------------------------------------------------------


class TestEstimateRehabCost:
    """Tests for estimate_rehab_cost()."""

    def test_cosmetic_level(self) -> None:
        """Cosmetic rehab uses $15/sqft."""
        result = estimate_rehab_cost(Decimal("1000"), "cosmetic", _COST_PER_SQFT)
        assert result == Decimal("15000")

    def test_moderate_level(self) -> None:
        """Moderate rehab uses $35/sqft."""
        result = estimate_rehab_cost(Decimal("1000"), "moderate", _COST_PER_SQFT)
        assert result == Decimal("35000")

    def test_full_gut_level(self) -> None:
        """Full gut rehab uses $75/sqft."""
        result = estimate_rehab_cost(Decimal("1000"), "full_gut", _COST_PER_SQFT)
        assert result == Decimal("75000")

    def test_unknown_level_raises(self) -> None:
        """Unknown renovation level must raise ValueError."""
        with pytest.raises(ValueError, match="renovation_level must be one of"):
            estimate_rehab_cost(Decimal("1000"), "luxury", _COST_PER_SQFT)

    def test_sqft_zero_raises(self) -> None:
        """Zero sqft must raise ValueError."""
        with pytest.raises(ValueError, match="sqft must be greater than zero"):
            estimate_rehab_cost(Decimal("0"), "cosmetic", _COST_PER_SQFT)

    def test_sqft_negative_raises(self) -> None:
        """Negative sqft must raise ValueError."""
        with pytest.raises(ValueError, match="sqft must be greater than zero"):
            estimate_rehab_cost(Decimal("-100"), "moderate", _COST_PER_SQFT)

    def test_large_sqft(self) -> None:
        """Very large property sqft is handled correctly."""
        result = estimate_rehab_cost(Decimal("50000"), "full_gut", _COST_PER_SQFT)
        assert result == Decimal("3750000")

    def test_fractional_sqft(self) -> None:
        """Fractional sqft produces correct decimal result."""
        result = estimate_rehab_cost(Decimal("1500.5"), "cosmetic", _COST_PER_SQFT)
        assert result == Decimal("22507.5")


# ---------------------------------------------------------------------------
# max_refinance_loan
# ---------------------------------------------------------------------------


class TestMaxRefinanceLoan:
    """Tests for max_refinance_loan()."""

    def test_standard_75_pct_ltv(self) -> None:
        """Standard 75 % LTV on a $200 000 ARV."""
        result = max_refinance_loan(Decimal("200000"), Decimal("0.75"))
        assert result == Decimal("150000")

    def test_default_ltv_is_75_pct(self) -> None:
        """Default LTV parameter is 0.75."""
        result = max_refinance_loan(Decimal("200000"))
        assert result == Decimal("150000")

    def test_ltv_zero_raises(self) -> None:
        """LTV of 0 must raise ValueError."""
        with pytest.raises(
            ValueError, match="ltv_ratio must be strictly between 0 and 1"
        ):
            max_refinance_loan(Decimal("200000"), Decimal("0"))

    def test_ltv_one_raises(self) -> None:
        """LTV of 1.0 must raise ValueError."""
        with pytest.raises(
            ValueError, match="ltv_ratio must be strictly between 0 and 1"
        ):
            max_refinance_loan(Decimal("200000"), Decimal("1"))

    def test_ltv_above_one_raises(self) -> None:
        """LTV > 1 must raise ValueError."""
        with pytest.raises(
            ValueError, match="ltv_ratio must be strictly between 0 and 1"
        ):
            max_refinance_loan(Decimal("200000"), Decimal("1.1"))

    def test_arv_zero_raises(self) -> None:
        """ARV of 0 must raise ValueError."""
        with pytest.raises(ValueError, match="arv must be greater than zero"):
            max_refinance_loan(Decimal("0"))

    def test_arv_negative_raises(self) -> None:
        """Negative ARV must raise ValueError."""
        with pytest.raises(ValueError, match="arv must be greater than zero"):
            max_refinance_loan(Decimal("-100000"))

    def test_high_ltv(self) -> None:
        """80 % LTV works for lenders allowing it."""
        result = max_refinance_loan(Decimal("250000"), Decimal("0.80"))
        assert result == Decimal("200000")

    def test_large_arv(self) -> None:
        """Large ARV ($500 000+) is handled correctly."""
        result = max_refinance_loan(Decimal("500000"), Decimal("0.75"))
        assert result == Decimal("375000")


# ---------------------------------------------------------------------------
# cash_left_in_deal
# ---------------------------------------------------------------------------


class TestCashLeftInDeal:
    """Tests for cash_left_in_deal()."""

    def test_positive_capital_remaining(self) -> None:
        """When refi proceeds < total cost, capital remains in the deal."""
        result = cash_left_in_deal(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("30000"),
            cash_out_refi_amount=Decimal("100000"),
        )
        assert result == Decimal("30000")

    def test_breakeven_zero_capital_left(self) -> None:
        """When refi proceeds exactly cover total cost, result is zero."""
        result = cash_left_in_deal(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("30000"),
            cash_out_refi_amount=Decimal("130000"),
        )
        assert result == Decimal("0")

    def test_negative_capital_infinite_coc(self) -> None:
        """When refi proceeds exceed total cost, capital left is negative (infinite CoC)."""
        result = cash_left_in_deal(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("30000"),
            cash_out_refi_amount=Decimal("150000"),
        )
        assert result == Decimal("-20000")

    def test_includes_closing_costs(self) -> None:
        """Closing costs are added to total invested capital."""
        result = cash_left_in_deal(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("30000"),
            cash_out_refi_amount=Decimal("130000"),
            closing_costs=Decimal("5000"),
        )
        assert result == Decimal("5000")

    def test_large_purchase_price(self) -> None:
        """$500 000+ purchase price is handled correctly."""
        result = cash_left_in_deal(
            purchase_price=Decimal("500000"),
            rehab_cost=Decimal("75000"),
            cash_out_refi_amount=Decimal("412500"),  # 75% of $550k ARV
        )
        assert result == Decimal("162500")

    def test_zero_rehab_cost(self) -> None:
        """Zero rehab (turnkey) still calculates correctly."""
        result = cash_left_in_deal(
            purchase_price=Decimal("200000"),
            rehab_cost=Decimal("0"),
            cash_out_refi_amount=Decimal("150000"),
        )
        assert result == Decimal("50000")


# ---------------------------------------------------------------------------
# brrrr_coc_return
# ---------------------------------------------------------------------------


class TestBrrrrCocReturn:
    """Tests for brrrr_coc_return()."""

    def test_infinite_coc_when_zero_capital_left(self) -> None:
        """Zero capital left → Decimal('Infinity')."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("6000"),
            cash_left_in_deal=Decimal("0"),
        )
        assert result == Decimal("Infinity")

    def test_infinite_coc_when_negative_capital_left(self) -> None:
        """Negative capital left → Decimal('Infinity')."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("6000"),
            cash_left_in_deal=Decimal("-10000"),
        )
        assert result == Decimal("Infinity")

    def test_normal_positive_coc(self) -> None:
        """Normal scenario: positive cash flow, positive capital left."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("6000"),
            cash_left_in_deal=Decimal("30000"),
        )
        assert result == Decimal("0.2")

    def test_zero_cash_flow_with_positive_capital_left(self) -> None:
        """Zero cash flow with positive capital left → Decimal('0')."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("0"),
            cash_left_in_deal=Decimal("30000"),
        )
        assert result == Decimal("0")

    def test_negative_cash_flow_with_positive_capital_left(self) -> None:
        """Negative cash flow (losing deal) returns negative CoC."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("-3000"),
            cash_left_in_deal=Decimal("30000"),
        )
        assert result == Decimal("-0.1")

    def test_large_values(self) -> None:
        """Large purchase price scenario ($500 000+)."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("12000"),
            cash_left_in_deal=Decimal("150000"),
        )
        assert result == Decimal("0.08")

    def test_infinite_coc_with_zero_cash_flow(self) -> None:
        """No cash flow but all capital recouped still returns Infinity."""
        result = brrrr_coc_return(
            annual_net_cash_flow=Decimal("0"),
            cash_left_in_deal=Decimal("0"),
        )
        assert result == Decimal("Infinity")
