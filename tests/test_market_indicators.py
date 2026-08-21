"""Tests for market cycle indicators."""

from decimal import Decimal

import pytest

from core.models.growth import MarketIndicator, MarketIndicatorType


class TestMarketIndicatorModel:
    """Tests for MarketIndicator model."""

    @pytest.mark.django_db
    def test_market_indicator_creation(self) -> None:
        """Test creating a MarketIndicator with all required fields."""
        indicator = MarketIndicator.objects.create(
            metro_area="Dallas-Fort Worth-Arlington, TX",
            indicator_type=MarketIndicatorType.MEDIAN_PRICE,
            value=Decimal("425000"),
            date_recorded="2026-01-15",
        )
        assert indicator.metro_area == "Dallas-Fort Worth-Arlington, TX"
        assert indicator.indicator_type == MarketIndicatorType.MEDIAN_PRICE
        assert indicator.value == Decimal("425000")
        assert str(indicator.date_recorded) == "2026-01-15"

    @pytest.mark.django_db
    def test_market_indicator_types(self) -> None:
        """Test all indicator types can be created."""
        types = [
            MarketIndicatorType.MEDIAN_PRICE,
            MarketIndicatorType.DOM,
            MarketIndicatorType.MONTHS_SUPPLY,
            MarketIndicatorType.PRICE_TO_INCOME,
            MarketIndicatorType.RENT_GROWTH_YOY,
        ]
        for t in types:
            indicator = MarketIndicator.objects.create(
                metro_area="Test Metro",
                indicator_type=t,
                value=Decimal("100"),
                date_recorded="2026-01-15",
            )
            assert indicator.indicator_type == t

    @pytest.mark.django_db
    def test_unique_constraint_metro_type_date(self) -> None:
        """Test that metro_area + indicator_type + date_recorded is unique."""
        MarketIndicator.objects.create(
            metro_area="Test Metro",
            indicator_type=MarketIndicatorType.MEDIAN_PRICE,
            value=Decimal("100"),
            date_recorded="2026-01-15",
        )
        # Creating another with same metro, type, date should fail
        with pytest.raises(Exception):
            MarketIndicator.objects.create(
                metro_area="Test Metro",
                indicator_type=MarketIndicatorType.MEDIAN_PRICE,
                value=Decimal("200"),
                date_recorded="2026-01-15",
            )


class TestMarketIndicatorClassification:
    """Tests for market indicator classification/health scoring."""

    @pytest.mark.django_db
    def test_classify_median_price_healthy(self) -> None:
        """Test median price classification - moderate price = healthy."""
        from core.integrations.market.market_trends import classify_market_health

        # Median price around 3x income = healthy
        health = classify_market_health(
            indicator_type="median_price",
            value=Decimal("350000"),
            metro_area="Test Metro",
            median_income=Decimal("100000"),
        )
        assert health == "healthy"

    @pytest.mark.django_db
    def test_classify_median_price_overheated(self) -> None:
        """Test median price classification - high price = overheated."""
        from core.integrations.market.market_trends import classify_market_health

        # Price > 5x income = overheated
        health = classify_market_health(
            indicator_type="median_price",
            value=Decimal("600000"),
            metro_area="Test Metro",
            median_income=Decimal("100000"),
        )
        assert health == "overheated"

    @pytest.mark.django_db
    def test_classify_dom_healthy(self) -> None:
        """Test DOM classification - moderate DOM = healthy."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="dom",
            value=Decimal("30"),
            metro_area="Test Metro",
        )
        assert health == "healthy"

    @pytest.mark.django_db
    def test_classify_dom_caution(self) -> None:
        """Test DOM classification - low DOM = caution (overheated)."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="dom",
            value=Decimal("10"),
            metro_area="Test Metro",
        )
        assert health == "caution"

    @pytest.mark.django_db
    def test_classify_months_supply_healthy(self) -> None:
        """Test months supply classification - 4-6 months = healthy."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="months_supply",
            value=Decimal("5"),
            metro_area="Test Metro",
        )
        assert health == "healthy"

    @pytest.mark.django_db
    def test_classify_months_supply_sellers_market(self) -> None:
        """Test months supply classification - < 3 months = sellers market (overheated)."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="months_supply",
            value=Decimal("2"),
            metro_area="Test Metro",
        )
        assert health == "overheated"

    @pytest.mark.django_db
    def test_classify_price_to_income_healthy(self) -> None:
        """Test price-to-income classification - 3-4 ratio = healthy."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="price_to_income",
            value=Decimal("3.5"),
            metro_area="Test Metro",
        )
        assert health == "healthy"

    @pytest.mark.django_db
    def test_classify_rent_growth_healthy(self) -> None:
        """Test rent growth classification - 3-5% = healthy."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="rent_growth_yoy",
            value=Decimal("0.04"),  # 4%
            metro_area="Test Metro",
        )
        assert health == "healthy"

    @pytest.mark.django_db
    def test_classify_rent_growth_overheated(self) -> None:
        """Test rent growth classification - > 8% = overheated."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="rent_growth_yoy",
            value=Decimal("0.10"),  # 10%
            metro_area="Test Metro",
        )
        assert health == "overheated"

    @pytest.mark.django_db
    def test_classify_rent_growth_declining(self) -> None:
        """Test rent growth classification - negative = declining (caution)."""
        from core.integrations.market.market_trends import classify_market_health

        health = classify_market_health(
            indicator_type="rent_growth_yoy",
            value=Decimal("-0.02"),  # -2%
            metro_area="Test Metro",
        )
        assert health == "caution"


class TestMarketTrendsAdapter:
    """Tests for market trends adapter."""

    @pytest.mark.django_db
    def test_fetch_market_indicators_returns_data(self) -> None:
        """Test that fetch_market_indicators returns indicator data."""
        from core.integrations.market.market_trends import fetch_market_indicators

        # This will test the adapter interface
        # The actual implementation will use mock data or external APIs
        result = fetch_market_indicators(metro_area="Test Metro")
        assert isinstance(result, list)
        # Each item should have indicator_type, value, date_recorded
        for item in result:
            assert "indicator_type" in item
            assert "value" in item
            assert "date_recorded" in item

    @pytest.mark.django_db
    def test_get_latest_indicators(self) -> None:
        """Test getting latest indicators for a metro area."""
        from core.integrations.market.market_trends import get_latest_indicators

        result = get_latest_indicators(metro_area="Test Metro")
        assert isinstance(result, dict)
        # Should have all 5 indicator types
        expected_types = {
            "median_price",
            "dom",
            "months_supply",
            "price_to_income",
            "rent_growth_yoy",
        }
        for t in expected_types:
            assert t in result


class TestUpdateMarketIndicatorsCommand:
    """Tests for update_market_indicators management command."""

    @pytest.mark.django_db
    def test_command_creates_indicators(self, capsys) -> None:
        """Test that command creates market indicator records."""
        from django.core.management import call_command

        call_command("update_market_indicators", "--metro", "Test Metro")
        captured = capsys.readouterr()
        assert "Updated" in captured.out or "Created" in captured.out

        # Verify indicators were created
        from core.models.growth import MarketIndicator

        indicators = MarketIndicator.objects.filter(metro_area="Test Metro")
        assert indicators.count() >= 1


class TestMarketDashboardView:
    """Tests for market dashboard view."""

    @pytest.mark.django_db
    def test_dashboard_renders(self, client, user) -> None:
        """Test dashboard renders successfully."""
        client.force_login(user)
        response = client.get("/markets/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_dashboard_shows_indicators(self, client, user) -> None:
        """Test that dashboard shows indicator cards."""
        from core.models.growth import MarketIndicator, MarketIndicatorType

        # Create some test data
        MarketIndicator.objects.create(
            metro_area="Dallas-Fort Worth-Arlington, TX",
            indicator_type=MarketIndicatorType.MEDIAN_PRICE,
            value=Decimal("425000"),
            date_recorded="2026-01-15",
        )

        client.force_login(user)
        response = client.get("/markets/")
        assert response.status_code == 200
        assert "Dallas" in response.content.decode()


class TestSparklineHelpers:
    """Tests for trend chart helpers."""

    def test_build_sparkline_points_normalizes_values(self) -> None:
        """Points should be normalized into the 100x30 viewBox."""
        from core.integrations.market.market_trends import build_sparkline_points

        points = build_sparkline_points([Decimal("0"), Decimal("5"), Decimal("10")])
        # Rising series: min at bottom-left, max at top-right
        assert points == "0,30 50,15 100,0"

    def test_build_sparkline_points_flat_series(self) -> None:
        """All-equal values should draw a flat line at the midpoint."""
        from core.integrations.market.market_trends import build_sparkline_points

        points = build_sparkline_points([Decimal("3"), Decimal("3"), Decimal("3")])
        assert points == "0,15 50,15 100,15"

    def test_build_sparkline_points_empty(self) -> None:
        """Empty series produces no points."""
        from core.integrations.market.market_trends import build_sparkline_points

        assert build_sparkline_points([]) == ""

    @pytest.mark.django_db
    def test_get_indicator_history_returns_oldest_first(self) -> None:
        """History should be limited to recent values, oldest first."""
        from core.integrations.market.market_trends import get_indicator_history
        from core.models.growth import MarketIndicator, MarketIndicatorType

        MarketIndicator.objects.create(
            metro_area="History Metro",
            indicator_type=MarketIndicatorType.DOM,
            value=Decimal("40"),
            date_recorded="2026-01-01",
        )
        MarketIndicator.objects.create(
            metro_area="History Metro",
            indicator_type=MarketIndicatorType.DOM,
            value=Decimal("20"),
            date_recorded="2026-02-01",
        )

        history = get_indicator_history("History Metro", "dom")
        assert history == [Decimal("40"), Decimal("20")]

    @pytest.mark.django_db
    def test_get_indicator_history_respects_limit(self) -> None:
        """Only the ``limit`` most recent values are returned."""
        from core.integrations.market.market_trends import get_indicator_history
        from core.models.growth import MarketIndicator, MarketIndicatorType

        for month in range(1, 6):
            MarketIndicator.objects.create(
                metro_area="Limit Metro",
                indicator_type=MarketIndicatorType.DOM,
                value=Decimal(str(month)),
                date_recorded=f"2025-{month:02d}-01",
            )

        history = get_indicator_history("Limit Metro", "dom", limit=3)
        assert history == [Decimal("3"), Decimal("4"), Decimal("5")]

    @pytest.mark.django_db
    def test_get_latest_indicators_prefers_db_records(self) -> None:
        """Stored DB values should take precedence over adapter fallback."""
        from core.integrations.market.market_trends import get_latest_indicators
        from core.models.growth import MarketIndicator, MarketIndicatorType

        MarketIndicator.objects.create(
            metro_area="DB Metro",
            indicator_type=MarketIndicatorType.MEDIAN_PRICE,
            value=Decimal("999000"),
            date_recorded="2026-01-15",
        )

        result = get_latest_indicators("DB Metro")
        assert result["median_price"]["value"] == Decimal("999000")
        assert result["median_price"]["history"] == [Decimal("999000")]
        assert result["median_price"]["sparkline"] != ""


class TestMarketIndicatorsE2E:
    """End-to-end tests for market indicators feature."""

    @pytest.mark.django_db
    def test_market_dashboard_renders_with_indicators(self, client, user) -> None:
        """Test that market dashboard renders with indicators for tracked markets."""
        from core.models.growth import MarketIndicator, MarketIndicatorType

        # Create test data
        MarketIndicator.objects.create(
            metro_area="Dallas-Fort Worth-Arlington, TX",
            indicator_type=MarketIndicatorType.MEDIAN_PRICE,
            value=Decimal("425000"),
            date_recorded="2026-01-15",
        )
        MarketIndicator.objects.create(
            metro_area="Dallas-Fort Worth-Arlington, TX",
            indicator_type=MarketIndicatorType.DOM,
            value=Decimal("28"),
            date_recorded="2026-01-15",
        )

        client.force_login(user)
        response = client.get("/markets/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Dallas" in content
        assert "425000" in content or "425" in content  # Check median price shown
        assert "28" in content  # Check DOM shown
        # Trend chart (sparkline SVG) should render for each indicator
        assert "<polyline" in content
