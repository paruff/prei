"""Tests for market scoring service and related finance utility."""

from decimal import Decimal

import pytest
from django.test import override_settings

from core.models import MarketSnapshot
from core.services.market_scoring import score_market, update_market_scores
from investor_app.finance.utils import (
    clamp_market_score,
    normalize_market_growth_rate_score,
    normalize_market_price_to_rent_score,
    price_to_rent_ratio,
)


class TestScoreMarket:
    """Tests for score_market."""

    def test_all_signals_populated_returns_score_in_range(self) -> None:
        """Composite score should be bounded between 0 and 100."""
        snapshot = MarketSnapshot(
            price_to_rent_ratio=Decimal("12"),
            population_growth_rate=Decimal("2.5"),
            employment_diversity_score=Decimal("70"),
            landlord_friendliness_score=Decimal("80"),
            rent_growth_rate=Decimal("4"),
        )

        score = score_market(snapshot)

        assert Decimal("0") <= score <= Decimal("100")

    def test_all_signals_none_returns_zero(self) -> None:
        """When all market signals are missing, score_market should return 0."""
        snapshot = MarketSnapshot()

        score = score_market(snapshot)

        assert score == Decimal("0")

    def test_none_snapshot_raises_value_error(self) -> None:
        """None snapshot should raise ValueError per public contract."""
        with pytest.raises(ValueError, match="snapshot cannot be None"):
            score_market(None)

    def test_partial_signals_returns_proportional_score(self) -> None:
        """Partial signal availability should not crash and should score proportionally."""
        snapshot = MarketSnapshot(landlord_friendliness_score=Decimal("80"))

        score = score_market(snapshot)

        assert score == Decimal("80")

    def test_partial_signals_weighted_average(self) -> None:
        """Multiple partial signals should use weighted average of active signals."""
        snapshot = MarketSnapshot(
            landlord_friendliness_score=Decimal("100"),
            employment_diversity_score=Decimal("50"),
        )

        score = score_market(snapshot)

        # (100*0.25 + 50*0.20) / (0.25 + 0.20) = 35 / 0.45 = 77.777...
        assert score == Decimal("77.78")

    @override_settings(
        MARKET_SCORE_WEIGHTS={
            "price_to_rent": "not-a-number",
            "landlord_friendliness": Decimal("0.75"),
        }
    )
    def test_invalid_market_score_weight_falls_back_to_default(self) -> None:
        """Invalid configured weight should fall back to default weight."""
        snapshot = MarketSnapshot(
            price_to_rent_ratio=Decimal("12"),
            landlord_friendliness_score=Decimal("50"),
        )

        score = score_market(snapshot)

        # Price-to-rent uses default fallback weight 0.25:
        # (100*0.25 + 50*0.75) / (0.25 + 0.75) = 62.5
        assert score == Decimal("62.50")


class TestPriceToRentRatio:
    """Tests for price_to_rent_ratio."""

    def test_zero_annual_rent_raises_value_error(self) -> None:
        """annual_median_rent = 0 must raise ValueError."""
        with pytest.raises(ValueError, match="annual_median_rent"):
            price_to_rent_ratio(Decimal("500000"), Decimal("0"))

    def test_large_values(self) -> None:
        """A $500k home and $24k annual rent should produce a valid ratio."""
        ratio = price_to_rent_ratio(Decimal("500000"), Decimal("24000"))

        # 500000 / 24000 = 20.833333...
        assert ratio.quantize(Decimal("0.0001")) == Decimal("20.8333")


class TestMarketScoreMathHelpers:
    """Tests for market-score math helpers in finance utils."""

    def test_normalize_market_price_to_rent_score_boundaries(self) -> None:
        """Price-to-rent normalization should respect threshold boundaries."""
        assert normalize_market_price_to_rent_score(Decimal("-1")) == Decimal("0")
        assert normalize_market_price_to_rent_score(Decimal("0")) == Decimal("0")
        assert normalize_market_price_to_rent_score(Decimal("14.99")) == Decimal("100")
        assert normalize_market_price_to_rent_score(Decimal("15")) == Decimal("100")
        assert normalize_market_price_to_rent_score(Decimal("20")) == Decimal("60")
        assert normalize_market_price_to_rent_score(Decimal("30")) == Decimal("0")

    def test_normalize_market_growth_rate_score_boundaries(self) -> None:
        """Growth-rate normalization should clamp to expected min/max range."""
        assert normalize_market_growth_rate_score(Decimal("-10")) == Decimal("0")
        assert normalize_market_growth_rate_score(Decimal("-5")) == Decimal("0")
        assert normalize_market_growth_rate_score(Decimal("10")) == Decimal("100")
        assert normalize_market_growth_rate_score(Decimal("12")) == Decimal("100")

    def test_clamp_market_score_boundaries(self) -> None:
        """Clamp helper should always return score in [0, 100]."""
        assert clamp_market_score(Decimal("-1")) == Decimal("0")
        assert clamp_market_score(Decimal("0")) == Decimal("0")
        assert clamp_market_score(Decimal("100")) == Decimal("100")
        assert clamp_market_score(Decimal("101")) == Decimal("100")


@pytest.mark.django_db
class TestUpdateMarketScores:
    """Tests for update_market_scores."""

    def test_empty_zip_code_list_returns_zero(self) -> None:
        """No zip codes should result in zero updated records."""
        updated = update_market_scores([])

        assert updated == 0

    def test_updates_market_score_and_returns_count(self) -> None:
        """Should persist market_score updates and report updated row count."""
        snapshot = MarketSnapshot.objects.create(
            zip_code="33101",
            landlord_friendliness_score=Decimal("80"),
        )

        updated = update_market_scores(["33101"])
        snapshot.refresh_from_db()

        assert updated == 1
        assert snapshot.market_score == Decimal("80.00")
