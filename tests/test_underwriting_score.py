"""Tests for underwriting score v2 functions.

Covers one_percent_rule, gross_rent_multiplier, and score_listing_v2.
"""

from decimal import Decimal

import pytest

from investor_app.finance.utils import (
    gross_rent_multiplier,
    one_percent_rule,
    score_listing_v2,
)

# ── one_percent_rule ───────────────────────────────────────────────────────────


class TestOnePercentRule:
    """Tests for one_percent_rule."""

    def test_exactly_at_threshold_returns_true(self) -> None:
        """Monthly rent equal to exactly 1% of purchase price → True."""
        result = one_percent_rule(
            monthly_rent=Decimal("1000"),
            purchase_price=Decimal("100000"),
        )
        assert result is True

    def test_above_threshold_returns_true(self) -> None:
        """Monthly rent above 1% of purchase price → True."""
        result = one_percent_rule(
            monthly_rent=Decimal("1500"),
            purchase_price=Decimal("100000"),
        )
        assert result is True

    def test_below_threshold_returns_false(self) -> None:
        """Monthly rent below 1% of purchase price → False."""
        result = one_percent_rule(
            monthly_rent=Decimal("800"),
            purchase_price=Decimal("100000"),
        )
        assert result is False

    def test_zero_purchase_price_raises_value_error(self) -> None:
        """purchase_price = 0 must raise ValueError."""
        with pytest.raises(ValueError, match="purchase_price"):
            one_percent_rule(
                monthly_rent=Decimal("1000"),
                purchase_price=Decimal("0"),
            )

    def test_negative_purchase_price_raises_value_error(self) -> None:
        """purchase_price < 0 must raise ValueError."""
        with pytest.raises(ValueError, match="purchase_price"):
            one_percent_rule(
                monthly_rent=Decimal("1000"),
                purchase_price=Decimal("-50000"),
            )

    def test_zero_monthly_rent_below_threshold(self) -> None:
        """Zero monthly rent is below 1% threshold → False."""
        result = one_percent_rule(
            monthly_rent=Decimal("0"),
            purchase_price=Decimal("100000"),
        )
        assert result is False


# ── gross_rent_multiplier ──────────────────────────────────────────────────────


class TestGrossRentMultiplier:
    """Tests for gross_rent_multiplier."""

    def test_typical_grm(self) -> None:
        """Typical GRM calculation: 200k / 20k = 10."""
        result = gross_rent_multiplier(
            purchase_price=Decimal("200000"),
            annual_rent=Decimal("20000"),
        )
        assert result == Decimal("10")

    def test_low_grm_excellent(self) -> None:
        """GRM < 10 should compute correctly."""
        result = gross_rent_multiplier(
            purchase_price=Decimal("90000"),
            annual_rent=Decimal("18000"),
        )
        assert result == Decimal("5")

    def test_high_grm_poor(self) -> None:
        """GRM > 20 should compute correctly."""
        result = gross_rent_multiplier(
            purchase_price=Decimal("500000"),
            annual_rent=Decimal("18000"),
        )
        assert result > Decimal("20")

    def test_zero_annual_rent_raises_value_error(self) -> None:
        """annual_rent = 0 must raise ValueError."""
        with pytest.raises(ValueError, match="annual_rent"):
            gross_rent_multiplier(
                purchase_price=Decimal("200000"),
                annual_rent=Decimal("0"),
            )

    def test_negative_annual_rent_raises_value_error(self) -> None:
        """annual_rent < 0 must raise ValueError."""
        with pytest.raises(ValueError, match="annual_rent"):
            gross_rent_multiplier(
                purchase_price=Decimal("200000"),
                annual_rent=Decimal("-10000"),
            )

    def test_returns_decimal(self) -> None:
        """Result should be a Decimal."""
        result = gross_rent_multiplier(
            purchase_price=Decimal("300000"),
            annual_rent=Decimal("24000"),
        )
        assert isinstance(result, Decimal)


# ── score_listing_v2 ───────────────────────────────────────────────────────────


class TestScoreListingV2:
    """Tests for score_listing_v2."""

    # -- Helpers ----------------------------------------------------------------

    def _realistic_inputs(self, **overrides) -> dict:
        """Return a baseline set of realistic inputs for score_listing_v2."""
        base = dict(
            purchase_price=Decimal("250000"),
            monthly_rent=Decimal("2500"),  # 1% rule: 2500/250000 = 1.0% → pass
            annual_noi=Decimal("18000"),  # cap rate 7.2%
            local_market_cap_rate=Decimal("0.06"),
            down_payment=Decimal("62500"),  # 25% down
            annual_debt_service=Decimal("14400"),
        )
        base.update(overrides)
        return base

    # -- Smoke test / basic structure ------------------------------------------

    def test_returns_expected_keys(self) -> None:
        """score_listing_v2 should return a dict with all required keys."""
        result = score_listing_v2(**self._realistic_inputs())
        assert set(result.keys()) == {
            "one_percent_rule_pass",
            "grm",
            "cap_rate",
            "cap_rate_vs_market",
            "coc_year1",
            "composite_score",
        }

    def test_realistic_composite_score_in_range(self) -> None:
        """Composite score must be in [0, 100] for realistic inputs."""
        result = score_listing_v2(**self._realistic_inputs())
        score = result["composite_score"]
        assert Decimal("0") <= score <= Decimal("100")

    def test_one_percent_rule_pass_reflected(self) -> None:
        """one_percent_rule_pass should be True when rent >= 1% of price."""
        result = score_listing_v2(**self._realistic_inputs())
        assert result["one_percent_rule_pass"] is True

    def test_cap_rate_vs_market_positive_when_above(self) -> None:
        """cap_rate_vs_market should be positive when property cap > local market cap."""
        result = score_listing_v2(**self._realistic_inputs())
        # 7.2% property cap vs 6% market → positive difference
        assert result["cap_rate_vs_market"] > Decimal("0")

    # -- 1% rule failure caps composite score ----------------------------------

    def test_failing_one_percent_rule_caps_score_at_40(self) -> None:
        """A deal that fails the 1% rule must have composite_score <= 40."""
        # monthly_rent = 800 on a 250k property → 0.32% → fails
        result = score_listing_v2(**self._realistic_inputs(monthly_rent=Decimal("800")))
        assert result["one_percent_rule_pass"] is False
        assert result["composite_score"] <= Decimal("40")

    # -- Above-market vs. below-market cap rate --------------------------------

    def test_above_market_cap_rate_raises_score_vs_below(self) -> None:
        """A deal with a cap rate above market should score higher than one below market."""
        above = score_listing_v2(
            **self._realistic_inputs(local_market_cap_rate=Decimal("0.04"))
        )  # property cap 7.2% vs 4% market → above
        below = score_listing_v2(
            **self._realistic_inputs(local_market_cap_rate=Decimal("0.09"))
        )  # property cap 7.2% vs 9% market → below
        assert above["composite_score"] > below["composite_score"]

    # -- Boundary: very large purchase price -----------------------------------

    def test_large_purchase_price(self) -> None:
        """score_listing_v2 must handle a $10M property without raising."""
        result = score_listing_v2(
            purchase_price=Decimal("10000000"),
            monthly_rent=Decimal("100000"),  # 1% of 10M → pass
            annual_noi=Decimal("720000"),  # 7.2% cap rate
            local_market_cap_rate=Decimal("0.06"),
            down_payment=Decimal("2500000"),
            annual_debt_service=Decimal("576000"),
        )
        assert Decimal("0") <= result["composite_score"] <= Decimal("100")

    # -- ValueError on invalid inputs ------------------------------------------

    def test_zero_purchase_price_raises(self) -> None:
        with pytest.raises(ValueError, match="purchase_price"):
            score_listing_v2(**self._realistic_inputs(purchase_price=Decimal("0")))

    def test_negative_purchase_price_raises(self) -> None:
        with pytest.raises(ValueError, match="purchase_price"):
            score_listing_v2(**self._realistic_inputs(purchase_price=Decimal("-1")))

    def test_zero_monthly_rent_raises(self) -> None:
        with pytest.raises(ValueError, match="monthly_rent"):
            score_listing_v2(**self._realistic_inputs(monthly_rent=Decimal("0")))

    def test_zero_annual_noi_raises(self) -> None:
        with pytest.raises(ValueError, match="annual_noi"):
            score_listing_v2(**self._realistic_inputs(annual_noi=Decimal("0")))

    def test_zero_local_market_cap_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="local_market_cap_rate"):
            score_listing_v2(
                **self._realistic_inputs(local_market_cap_rate=Decimal("0"))
            )

    def test_zero_down_payment_raises(self) -> None:
        with pytest.raises(ValueError, match="down_payment"):
            score_listing_v2(**self._realistic_inputs(down_payment=Decimal("0")))

    def test_zero_annual_debt_service_raises(self) -> None:
        with pytest.raises(ValueError, match="annual_debt_service"):
            score_listing_v2(**self._realistic_inputs(annual_debt_service=Decimal("0")))

    def test_negative_monthly_rent_raises(self) -> None:
        with pytest.raises(ValueError, match="monthly_rent"):
            score_listing_v2(**self._realistic_inputs(monthly_rent=Decimal("-500")))

    def test_negative_annual_noi_raises(self) -> None:
        with pytest.raises(ValueError, match="annual_noi"):
            score_listing_v2(**self._realistic_inputs(annual_noi=Decimal("-1000")))

    def test_negative_local_market_cap_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="local_market_cap_rate"):
            score_listing_v2(
                **self._realistic_inputs(local_market_cap_rate=Decimal("-0.05"))
            )

    def test_negative_down_payment_raises(self) -> None:
        with pytest.raises(ValueError, match="down_payment"):
            score_listing_v2(**self._realistic_inputs(down_payment=Decimal("-1000")))

    def test_negative_annual_debt_service_raises(self) -> None:
        with pytest.raises(ValueError, match="annual_debt_service"):
            score_listing_v2(
                **self._realistic_inputs(annual_debt_service=Decimal("-1000"))
            )

    def test_grm_matches_expected(self) -> None:
        """GRM should be purchase_price / annual_rent."""
        result = score_listing_v2(**self._realistic_inputs())
        expected_grm = Decimal("250000") / (Decimal("2500") * 12)
        # Allow small rounding difference
        assert abs(result["grm"] - expected_grm) < Decimal("0.0001")

    def test_cap_rate_matches_expected(self) -> None:
        """cap_rate should be annual_noi / purchase_price."""
        result = score_listing_v2(**self._realistic_inputs())
        expected = Decimal("18000") / Decimal("250000")
        assert abs(result["cap_rate"] - expected) < Decimal("0.0001")

    def test_coc_year1_matches_expected(self) -> None:
        """coc_year1 should be (annual_noi - annual_debt_service) / down_payment."""
        result = score_listing_v2(**self._realistic_inputs())
        expected = (Decimal("18000") - Decimal("14400")) / Decimal("62500")
        assert abs(result["coc_year1"] - expected) < Decimal("0.0001")
