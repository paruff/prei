import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone

from core.models import MarketSnapshot, Listing


@pytest.mark.django_db
def test_growth_areas_renders_with_seeded_snapshots(client):
    MarketSnapshot.objects.create(area_type="zip", zip_code="78701", state="TX", rent_index=Decimal("1800"), price_trend=Decimal("0.14"))
    MarketSnapshot.objects.create(area_type="zip", zip_code="80203", state="CO", rent_index=Decimal("1600"), price_trend=Decimal("0.10"))
    resp = client.get(reverse("growth_areas"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "78701" in html
    assert "80203" in html


@pytest.mark.django_db
def test_growth_areas_shows_undervalued_listings(client):
    Listing.objects.create(
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
        url="https://example.com/ga-a",
        posted_at=timezone.now(),
    )
    Listing.objects.create(
        source="dummy",
        address="B",
        city="X",
        state="TX",
        zip_code="00000",
        price=Decimal("300000"),
        beds=3,
        baths=Decimal("2.0"),
        sq_ft=1500,
        property_type="SFH",
        url="https://example.com/ga-b",
        posted_at=timezone.now(),
    )
    resp = client.get(reverse("growth_areas"))
    assert resp.status_code == 200
    assert "Undervalued Listings" in resp.content.decode()
