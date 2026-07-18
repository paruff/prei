"""Tests for the Offer stage handler — offer price optimization."""

import pytest
from pydantic import ValidationError

from prei.pipeline.handlers.offer import (
    OfferInput,
    OfferStrategy,
    solve_offer,
)


class TestOfferInput:
    """OfferInput validation tests."""

    def test_valid_input_defaults(self):
        i = OfferInput(mao=250000.0)
        assert i.mao == 250000.0
        assert i.arv is None
        assert i.rehab_budget == 0.0
        assert i.desired_equity == 0.0
        assert i.competition_multiplier == 1.0

    def test_valid_input_full(self):
        i = OfferInput(
            mao=250000.0,
            arv=320000.0,
            rehab_budget=30000.0,
            desired_equity=0.20,
            competition_multiplier=1.1,
        )
        assert i.arv == 320000.0
        assert i.rehab_budget == 30000.0
        assert i.desired_equity == 0.20

    def test_rehab_budget_negative_raises(self):
        with pytest.raises(ValidationError):
            OfferInput(mao=250000.0, rehab_budget=-100.0)

    def test_desired_equity_out_of_range(self):
        with pytest.raises(ValidationError):
            OfferInput(mao=250000.0, desired_equity=1.5)

    def test_competition_multiplier_out_of_range(self):
        with pytest.raises(ValidationError):
            OfferInput(mao=250000.0, competition_multiplier=3.0)


class TestSolveOffer:
    """Solve offer price with different strategies."""

    def test_conservative_strategy(self):
        i = OfferInput(mao=250000.0)
        result = solve_offer(i, strategy=OfferStrategy.CONSERVATIVE)
        assert result.strategy == OfferStrategy.CONSERVATIVE
        assert result.offer_price == 237500.0  # 250000 * 0.95
        assert result.premium_over_mao == -12500.0
        assert result.premium_pct == -0.05

    def test_target_strategy(self):
        i = OfferInput(mao=250000.0)
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        assert result.offer_price == 250000.0
        assert result.premium_over_mao == 0.0
        assert result.premium_pct == 0.0

    def test_aggressive_strategy(self):
        i = OfferInput(mao=250000.0)
        result = solve_offer(i, strategy=OfferStrategy.AGGRESSIVE)
        assert result.offer_price == 262500.0  # 250000 * 1.05
        assert result.premium_over_mao == 12500.0

    def test_competition_multiplier(self):
        i = OfferInput(mao=250000.0, competition_multiplier=1.2)
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        assert result.offer_price == 300000.0  # 250000 * 1.2

    def test_competition_multiplier_aggressive(self):
        i = OfferInput(mao=250000.0, competition_multiplier=1.15)
        result = solve_offer(i, strategy=OfferStrategy.AGGRESSIVE)
        assert result.offer_price == 301875.0  # 250000 * 1.05 * 1.15

    def test_equity_calculation_with_arv(self):
        i = OfferInput(
            mao=200000.0,
            arv=300000.0,
            rehab_budget=25000.0,
        )
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        assert result.estimated_equity is not None
        assert result.estimated_equity == 75000.0  # 300000 - (200000 + 25000)
        assert result.estimated_equity_pct is not None
        assert result.estimated_equity_pct == 0.25

    def test_equity_clamp_with_desired_equity(self):
        """When ARV is known and desired_equity is set, offer is clamped."""
        i = OfferInput(
            mao=270000.0,
            arv=300000.0,
            rehab_budget=25000.0,
            desired_equity=0.20,
        )
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        # max_offer = 300000 * (1 - 0.20) - 25000 = 215000
        # original offer = 270000 > 215000 → clamped to 215000
        assert result.offer_price == 215000.0
        assert result.estimated_equity == 60000.0
        assert result.estimated_equity_pct == 0.20

    def test_equity_not_clamped_when_below_cap(self):
        """When desired equity is already satisfied, no clamping occurs."""
        i = OfferInput(
            mao=200000.0,
            arv=300000.0,
            rehab_budget=25000.0,
            desired_equity=0.20,
        )
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        # max_offer = 300000 * (1 - 0.20) - 25000 = 215000
        # original offer = 200000 < 215000 → no clamp
        assert result.offer_price == 200000.0

    def test_no_equity_without_arv(self):
        i = OfferInput(mao=200000.0)
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        assert result.estimated_equity is None
        assert result.estimated_equity_pct is None

    def test_zero_mao(self):
        """Zero MAO should not crash (division by zero guard)."""
        i = OfferInput(mao=0.0)
        result = solve_offer(i, strategy=OfferStrategy.CONSERVATIVE)
        assert result.offer_price == 0.0
        assert result.premium_pct == 0.0

    def test_aggressive_with_equity_clamp(self):
        """Aggressive strategy is clamped by equity constraint."""
        i = OfferInput(
            mao=250000.0,
            arv=280000.0,
            rehab_budget=15000.0,
            desired_equity=0.20,
        )
        result = solve_offer(i, strategy=OfferStrategy.AGGRESSIVE)
        # raw = 250000 * 1.05 = 262500
        # max_offer = 280000 * (1 - 0.20) - 15000 = 209000
        assert result.offer_price == 209000.0

    def test_metrics_are_rounded(self):
        i = OfferInput(
            mao=123456.789,
            arv=200000.0,
            rehab_budget=12345.678,
        )
        result = solve_offer(i, strategy=OfferStrategy.TARGET)
        assert result.offer_price == 123456.79  # rounded to 2dp
        assert isinstance(result.offer_price, float)
