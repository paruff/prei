import pytest
from decimal import Decimal
from django.utils import timezone

from core.models import Listing, MarketSnapshot, Property
from core.services.cma import find_undervalued
from core.services.portfolio import aggregate_portfolio


@pytest.mark.django_db
def test_cma_flags_undervalued_listings():
    a = Listing.objects.create(
        source="dummy",
        address="A",
        city="X",
        state="TX",
        zip_code="00000",
        price=Decimal("200000"),
        beds=3,
        baths=Decimal("2.0"),
        sq_ft=2000,
        property_type="SFH",
        url="https://example.com/a",
        posted_at=timezone.now(),
    )
    b = Listing.objects.create(
        source="dummy",
        address="B",
        city="X",
        state="TX",
        zip_code="00000",
        price=Decimal("250000"),
        beds=3,
        baths=Decimal("2.0"),
        sq_ft=1500,
        property_type="SFH",
        url="https://example.com/b",
        posted_at=timezone.now(),
    )
    vals = list(find_undervalued([a, b], threshold=Decimal("0.95")))
    # 'a' has lower PPSF; likely to be flagged
    assert any(item[0].url == a.url for item in vals)


@pytest.mark.django_db
def test_portfolio_aggregation_works(user):
    # Create one property to ensure aggregation runs; KPI values computed by utils
    p = Property.objects.create(
        user=user,
        address="1 Test",
        city="X",
        state="TX",
        zip_code="00000",
        purchase_price=Decimal("100000"),
    )
    agg = aggregate_portfolio(user)
    assert set(agg.keys()) == {"total_noi", "avg_cap_rate", "avg_coc"}


@pytest.mark.django_db
def test_market_snapshot_admin_ready():
    MarketSnapshot.objects.create(
        area_type="zip",
        zip_code="78701",
        state="TX",
        rent_index=Decimal("1500"),
        price_trend=Decimal("0.12"),
        crime_score=Decimal("2.5"),
        school_rating=Decimal("8.5"),
    )
    assert MarketSnapshot.objects.count() == 1
