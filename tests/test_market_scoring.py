"""Tests for market scoring service and related finance utility."""

from decimal import Decimal

import pytest

from core.models import MarketSnapshot
from core.services.market_scoring import score_market, update_market_scores
from investor_app.finance.utils import price_to_rent_ratio


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

    def test_partial_signals_returns_proportional_score(self) -> None:
        """Partial signal availability should not crash and should score proportionally."""
        snapshot = MarketSnapshot(landlord_friendliness_score=Decimal("80"))

        score = score_market(snapshot)

        assert score == Decimal("80")


class TestPriceToRentRatio:
    """Tests for price_to_rent_ratio."""

    def test_zero_annual_rent_raises_value_error(self) -> None:
        """annual_median_rent = 0 must raise ValueError."""
        with pytest.raises(ValueError, match="annual_median_rent"):
            price_to_rent_ratio(Decimal("500000"), Decimal("0"))

    def test_large_values(self) -> None:
        """A $500k home and $24k annual rent should produce a valid ratio."""
        ratio = price_to_rent_ratio(Decimal("500000"), Decimal("24000"))

        assert ratio.quantize(Decimal("0.0001")) == Decimal("20.8333")


@pytest.mark.django_db
class TestUpdateMarketScores:
    """Tests for update_market_scores."""

    def test_empty_zip_code_list_returns_zero(self) -> None:
        """No zip codes should result in zero updated records."""
        updated = update_market_scores([])

        assert updated == 0
