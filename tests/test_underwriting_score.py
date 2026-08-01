"""Tests for underwriting score v2 primitives.

Covers one_percent_rule and gross_rent_multiplier. The full underwriting
score is tested in core/tests/test_scoring_v2.py against the Django
implementation in core.services.scoring.
"""

from decimal import Decimal

import pytest

from investor_app.finance.scoring import (
    gross_rent_multiplier,
    one_percent_rule,
)

pytestmark = pytest.mark.unit

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
