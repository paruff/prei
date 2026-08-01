"""Unit, integration, and E2E tests for the offer stage handler.

The offer port to core.services.offer is Decimal-based (LIMIT-21 resolved),
so float equality/type assertions from the pydantic era were replaced with
Decimal comparisons.
"""

import pytest
from dataclasses import replace
from decimal import Decimal

from core.services.offer import (
    OfferInput,
    OfferStrategy,
    solve_offer,
)

BASE_INPUT = OfferInput(
    mao=Decimal("300000.00"),
    arv=Decimal("420000.00"),
    rehab_budget=Decimal("20000.00"),
    desired_equity=Decimal("0.20"),
)

# ═══════════════════════════════════════════════════════════════════════════════
#  UNIT
# ═══════════════════════════════════════════════════════════════════════════════


class TestOfferUnit:
    def test_conservative_below_mao(self):
        result = solve_offer(BASE_INPUT, OfferStrategy.CONSERVATIVE)
        assert result.offer_price < BASE_INPUT.mao
        assert result.premium_over_mao < 0

    def test_target_at_mao(self):
        result = solve_offer(BASE_INPUT, OfferStrategy.TARGET)
        assert result.offer_price == pytest.approx(
            BASE_INPUT.mao, rel=Decimal("0.0001")
        )
        assert result.premium_pct == pytest.approx(0, abs=Decimal("0.0001"))

    def test_aggressive_above_mao(self):
        result = solve_offer(BASE_INPUT, OfferStrategy.AGGRESSIVE)
        assert result.offer_price > BASE_INPUT.mao
        assert result.premium_over_mao > 0

    def test_competition_multiplier_increases_offer(self):
        base = solve_offer(BASE_INPUT, OfferStrategy.TARGET)
        hot = solve_offer(
            replace(BASE_INPUT, competition_multiplier=Decimal("1.5")),
            OfferStrategy.TARGET,
        )
        assert hot.offer_price > base.offer_price

    def test_competition_multiplier_decreases_offer(self):
        cold = solve_offer(
            replace(BASE_INPUT, competition_multiplier=Decimal("0.75")),
            OfferStrategy.TARGET,
        )
        assert cold.offer_price < BASE_INPUT.mao

    def test_equity_constraint_clamps_offer(self):
        """High desired equity clamps offer below MAO."""
        high_equity = OfferInput(
            mao=Decimal("300000"),
            arv=Decimal("320000"),
            rehab_budget=Decimal("20000"),
            desired_equity=Decimal("0.25"),
        )
        result = solve_offer(high_equity, OfferStrategy.AGGRESSIVE)
        # Max offer for 25% equity: 320000*0.75 - 20000 = 220000
        assert result.offer_price <= Decimal("220000")

    def test_no_arv_skips_equity_calc(self):
        """Without ARV, equity fields are None."""
        result = solve_offer(replace(BASE_INPUT, arv=None), OfferStrategy.TARGET)
        assert result.estimated_equity is None
        assert result.estimated_equity_pct is None

    def test_mao_zero_raises_value_error(self):
        """MAO of zero is rejected (must be > 0)."""
        with pytest.raises(ValueError):
            solve_offer(OfferInput(mao=Decimal("0")), OfferStrategy.TARGET)

    def test_strategy_enum_values(self):
        assert OfferStrategy.CONSERVATIVE.value == "conservative"
        assert OfferStrategy.TARGET.value == "target"
        assert OfferStrategy.AGGRESSIVE.value == "aggressive"

    def test_premium_pct_positive_for_aggressive(self):
        result = solve_offer(BASE_INPUT, OfferStrategy.AGGRESSIVE)
        assert result.premium_pct > 0

    def test_premium_pct_negative_for_conservative(self):
        result = solve_offer(BASE_INPUT, OfferStrategy.CONSERVATIVE)
        assert result.premium_pct < 0

    def test_offer_metrics_are_decimal(self):
        result = solve_offer(BASE_INPUT, OfferStrategy.TARGET)
        assert isinstance(result.offer_price, Decimal)
        assert isinstance(result.premium_over_mao, Decimal)

    def test_equity_calculation_correct(self):
        """Equity = ARV - (offer + rehab). For TARGET strategy: offer = MAO = 300k."""
        result = solve_offer(BASE_INPUT, OfferStrategy.TARGET)
        assert BASE_INPUT.arv is not None
        # offer = MAO = 300000 (no clamp since 300000 + 20000 = 320000 <= 420000*0.80 = 336000)
        expected_equity = BASE_INPUT.arv - (BASE_INPUT.mao + BASE_INPUT.rehab_budget)
        assert result.estimated_equity == pytest.approx(
            expected_equity, rel=Decimal("0.0001")
        )
        assert result.estimated_equity == pytest.approx(
            Decimal("100000.00"), rel=Decimal("0.0001")
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION — offer + underwriting
# ═══════════════════════════════════════════════════════════════════════════════


class TestOfferIntegration:
    def test_offer_from_underwriting_mao(self):
        """Underwriting MAO feeds directly into offer solver."""
        from core.services.underwriting import (
            solve_underwriting,
            UnderwritingInput,
        )

        uw = solve_underwriting(
            UnderwritingInput(
                purchase_price=Decimal("300000"),
                estimated_rent=Decimal("2500"),
                property_tax_annual=Decimal("3600"),
                insurance_annual=Decimal("1200"),
            ),
            target_cap_rate=0.08,
        )
        offer = solve_offer(
            OfferInput(mao=uw.mao, arv=uw.mao * Decimal("1.15")), OfferStrategy.TARGET
        )
        assert offer.offer_price == pytest.approx(uw.mao, rel=Decimal("0.001"))
        assert offer.estimated_equity is not None
        assert offer.estimated_equity > 0

    def test_offer_strategies_spread(self):
        """CONSERVATIVE < TARGET < AGGRESSIVE for same input."""
        c = solve_offer(BASE_INPUT, OfferStrategy.CONSERVATIVE).offer_price
        t = solve_offer(BASE_INPUT, OfferStrategy.TARGET).offer_price
        a = solve_offer(BASE_INPUT, OfferStrategy.AGGRESSIVE).offer_price
        assert c < t < a

    def test_offer_equity_clamp_preserves_strategy_label(self):
        """Clamped offer still reports correct strategy."""
        result = solve_offer(
            OfferInput(
                mao=Decimal("300000"),
                arv=Decimal("310000"),
                rehab_budget=Decimal("20000"),
                desired_equity=Decimal("0.20"),
            ),
            OfferStrategy.AGGRESSIVE,
        )
        assert result.strategy == OfferStrategy.AGGRESSIVE


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E — offer as part of full pipeline
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestOfferE2E:
    def test_e2e_underwriting_to_offer(self):
        """Underwriting MAO feeds offer calculation."""
        from core.services.underwriting import (
            solve_underwriting,
            UnderwritingInput,
        )

        uw = solve_underwriting(
            UnderwritingInput(
                purchase_price=Decimal("350000"),
                estimated_rent=Decimal("2800"),
                property_tax_annual=Decimal("3600"),
                insurance_annual=Decimal("1200"),
            ),
            target_cap_rate=0.08,
        )
        offer = solve_offer(
            OfferInput(mao=uw.mao, arv=uw.mao * Decimal("1.2")), OfferStrategy.TARGET
        )
        assert offer.offer_price > 0
        assert offer.estimated_equity is not None

    def test_e2e_multiple_strategies(self):
        """Generate offers for all three strategies from same underwriting."""
        from core.services.underwriting import (
            solve_underwriting,
            UnderwritingInput,
        )

        uw = solve_underwriting(
            UnderwritingInput(
                purchase_price=Decimal("300000"),
                estimated_rent=Decimal("2500"),
                property_tax_annual=Decimal("3600"),
                insurance_annual=Decimal("1200"),
            ),
            0.08,
        )
        for s in [
            OfferStrategy.CONSERVATIVE,
            OfferStrategy.TARGET,
            OfferStrategy.AGGRESSIVE,
        ]:
            offer = solve_offer(OfferInput(mao=uw.mao), s)
            assert offer.offer_price > 0
