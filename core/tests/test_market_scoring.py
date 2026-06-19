"""Tests for market scoring: Price-to-Rent ratio and overall market score."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import MarketSnapshot, Property
from core.services.market_scoring import (
    calculate_price_to_rent_ratio,
    score_market,
)


# ── calculate_price_to_rent_ratio ─────────────────────────────────────────────


class TestCalculatePriceToRentRatio:
    """P/R = median_home_price / (median_monthly_rent * 12)."""

    def test_basic_ratio(self):
        """$200k home, $1,500/mo rent → P/R = 11.11."""
        result = calculate_price_to_rent_ratio(
            Decimal("200000"), Decimal("1500")
        )
        expected = Decimal("200000") / (Decimal("1500") * 12)
        assert result == expected.quantize(Decimal("0.01"))

    def test_strong_market(self):
        """P/R < 12 is a strong cashflow market."""
        # $100k home, $1,200/mo → P/R = 6.94
        result = calculate_price_to_rent_ratio(
            Decimal("100000"), Decimal("1200")
        )
        assert result < 12

    def test_moderate_market(self):
        """P/R 12–16 is moderate."""
        # $180k home, $1,200/mo → P/R = 12.50
        result = calculate_price_to_rent_ratio(
            Decimal("180000"), Decimal("1200")
        )
        assert 12 <= result < 16

    def test_borderline_market(self):
        """P/R 16–20 is borderline."""
        # $250k home, $1,300/mo → P/R = 16.03
        result = calculate_price_to_rent_ratio(
            Decimal("250000"), Decimal("1300")
        )
        assert 16 <= result <= 20

    def test_weak_market(self):
        """P/R > 20 is a weak cashflow market."""
        # $400k home, $1,500/mo → P/R = 22.22
        result = calculate_price_to_rent_ratio(
            Decimal("400000"), Decimal("1500")
        )
        assert result > 20

    def test_zero_price_raises(self):
        with pytest.raises(ValueError, match="median_home_price"):
            calculate_price_to_rent_ratio(Decimal("0"), Decimal("1500"))

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="median_home_price"):
            calculate_price_to_rent_ratio(Decimal("-100000"), Decimal("1500"))

    def test_zero_rent_raises(self):
        with pytest.raises(ValueError, match="median_monthly_rent"):
            calculate_price_to_rent_ratio(Decimal("200000"), Decimal("0"))

    def test_negative_rent_raises(self):
        with pytest.raises(ValueError, match="median_monthly_rent"):
            calculate_price_to_rent_ratio(Decimal("200000"), Decimal("-1500"))

    def test_returns_decimal(self):
        result = calculate_price_to_rent_ratio(
            Decimal("200000"), Decimal("1500")
        )
        assert isinstance(result, Decimal)


# ── score_market ──────────────────────────────────────────────────────────────


@pytest.fixture
def zip_78702(db):
    """Create a MarketSnapshot for ZIP 78702."""
    return MarketSnapshot.objects.create(
        area_type="zip",
        zip_code="78702",
        city="Austin",
        state="TX",
        population=100000,
        population_growth_pct_5yr=Decimal("0.0250"),
        unemployment_rate=Decimal("0.0350"),
        median_household_income=Decimal("75000"),
        fetched_at=timezone.now(),
    )


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(username="market_test", password="pass")


@pytest.fixture
def properties_in_zip(db, user, zip_78702):
    """Create properties in ZIP 78702 with known prices and rents."""
    props = []
    for i, (price, rent) in enumerate([
        (Decimal("200000"), Decimal("1500")),
        (Decimal("250000"), Decimal("1800")),
        (Decimal("180000"), Decimal("1400")),
    ]):
        props.append(Property.objects.create(
            user=user,
            address=f"{100 + i} Market St",
            city="Austin",
            state="TX",
            zip_code="78702",
            purchase_price=price,
            monthly_rent_gross=rent,
            property_taxes_annual=Decimal("2400"),
            insurance_annual=Decimal("1200"),
        ))
    return props


class TestScoreMarket:
    """score_market returns a dict with all required keys."""

    def test_returns_dict(self, zip_78702):
        result = score_market("78702")
        assert isinstance(result, dict)

    def test_has_all_keys(self, zip_78702):
        result = score_market("78702")
        expected_keys = {
            "zip_code",
            "price_to_rent_ratio",
            "price_to_rent_verdict",
            "unemployment_rate",
            "population_growth_pct_5yr",
            "overall_score",
            "data_freshness_days",
        }
        assert expected_keys == set(result.keys())

    def test_zip_code_populated(self, zip_78702):
        result = score_market("78702")
        assert result["zip_code"] == "78702"

    def test_unemployment_from_snapshot(self, zip_78702):
        result = score_market("78702")
        assert result["unemployment_rate"] == Decimal("0.0350")

    def test_population_growth_from_snapshot(self, zip_78702):
        result = score_market("78702")
        assert result["population_growth_pct_5yr"] == Decimal("0.0250")

    def test_data_freshness(self, zip_78702):
        result = score_market("78702")
        assert result["data_freshness_days"] == 0

    def test_overall_score_range(self, zip_78702):
        result = score_market("78702")
        assert 0 <= result["overall_score"] <= 100

    def test_computes_pr_from_properties(self, zip_78702, properties_in_zip):
        """When properties exist, P/R is computed from their averages."""
        result = score_market("78702")
        assert result["price_to_rent_ratio"] is not None
        assert result["price_to_rent_verdict"] != "Unknown"

    def test_pr_verdict_is_correct_band(self, zip_78702, properties_in_zip):
        """Average of ($200k/$1500, $250k/$1800, $180k/$1400) should be moderate."""
        result = score_market("78702")
        # avg price = 210000, avg rent = 1566.67
        # P/R = 210000 / (1566.67 * 12) ≈ 11.16 → Strong
        assert result["price_to_rent_verdict"] in ("Strong", "Moderate")


class TestScoreMarketMissingData:
    """Gracefully handle missing data."""

    def test_unknown_zip_returns_zero_score(self, db):
        result = score_market("99999")
        assert result["overall_score"] == 0
        assert result["price_to_rent_verdict"] == "Unknown"
        assert result["price_to_rent_ratio"] is None
        assert result["unemployment_rate"] is None
        assert result["population_growth_pct_5yr"] is None
        assert result["data_freshness_days"] is None

    def test_snapshot_without_fetched_at(self, db):
        """Snapshot with no fetched_at — freshness is None."""
        MarketSnapshot.objects.create(
            area_type="zip",
            zip_code="11111",
            fetched_at=None,
        )
        result = score_market("11111")
        assert result["data_freshness_days"] is None

    def test_snapshot_without_unemployment(self, db):
        """Snapshot with no unemployment — score still computed."""
        MarketSnapshot.objects.create(
            area_type="zip",
            zip_code="22222",
            fetched_at=timezone.now(),
            unemployment_rate=None,
        )
        result = score_market("22222")
        assert result["unemployment_rate"] is None
        # Score should still be computed from other available data
        assert isinstance(result["overall_score"], int)


class TestScoreMarketVerdictBands:
    """Verify all four verdict bands are reachable."""

    def _make_snapshot_and_score(self, db, **kwargs):
        snap = MarketSnapshot.objects.create(
            area_type="zip",
            fetched_at=timezone.now(),
            **kwargs,
        )
        return score_market(snap.zip_code)

    def test_strong_band(self, db):
        """P/R < 12 → Strong."""
        # Create a property that gives P/R < 12
        user = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.create_user(
            username="strong_test", password="pass"
        )
        Property.objects.create(
            user=user,
            address="Strong St",
            city="Austin",
            state="TX",
            zip_code="33333",
            purchase_price=Decimal("100000"),
            monthly_rent_gross=Decimal("1200"),
            property_taxes_annual=Decimal("1000"),
            insurance_annual=Decimal("500"),
        )
        MarketSnapshot.objects.create(
            area_type="zip",
            zip_code="33333",
            fetched_at=timezone.now(),
        )
        result = score_market("33333")
        assert result["price_to_rent_verdict"] == "Strong"

    def test_moderate_band(self, db):
        """P/R 12–16 → Moderate."""
        user = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.create_user(
            username="moderate_test", password="pass"
        )
        Property.objects.create(
            user=user,
            address="Moderate St",
            city="Austin",
            state="TX",
            zip_code="44444",
            purchase_price=Decimal("200000"),
            monthly_rent_gross=Decimal("1300"),
            property_taxes_annual=Decimal("2000"),
            insurance_annual=Decimal("1000"),
        )
        MarketSnapshot.objects.create(
            area_type="zip",
            zip_code="44444",
            fetched_at=timezone.now(),
        )
        result = score_market("44444")
        assert result["price_to_rent_verdict"] == "Moderate"

    def test_borderline_band(self, db):
        """P/R 16–20 → Borderline."""
        user = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.create_user(
            username="borderline_test", password="pass"
        )
        Property.objects.create(
            user=user,
            address="Borderline Blvd",
            city="Austin",
            state="TX",
            zip_code="55555",
            purchase_price=Decimal("300000"),
            monthly_rent_gross=Decimal("1400"),
            property_taxes_annual=Decimal("3000"),
            insurance_annual=Decimal("1500"),
        )
        MarketSnapshot.objects.create(
            area_type="zip",
            zip_code="55555",
            fetched_at=timezone.now(),
        )
        result = score_market("55555")
        assert result["price_to_rent_verdict"] == "Borderline"

    def test_weak_band(self, db):
        """P/R > 20 → Weak."""
        user = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model().objects.create_user(
            username="weak_test", password="pass"
        )
        Property.objects.create(
            user=user,
            address="Weak Way",
            city="Austin",
            state="TX",
            zip_code="66666",
            purchase_price=Decimal("500000"),
            monthly_rent_gross=Decimal("1500"),
            property_taxes_annual=Decimal("5000"),
            insurance_annual=Decimal("2500"),
        )
        MarketSnapshot.objects.create(
            area_type="zip",
            zip_code="66666",
            fetched_at=timezone.now(),
        )
        result = score_market("66666")
        assert result["price_to_rent_verdict"] == "Weak"
