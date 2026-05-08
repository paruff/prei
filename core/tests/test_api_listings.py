"""Integration tests for listing and portfolio analytics API endpoints."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Listing, MarketSnapshot, Property


def _make_listing(**kwargs) -> Listing:
    defaults = {
        "source": "external",
        "address": "123 Main St",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "price": Decimal("300000.00"),
        "beds": 3,
        "baths": Decimal("2.0"),
        "sq_ft": 1500,
        "property_type": "SFH",
        "url": f"https://example.com/listing/{timezone.now().timestamp()}",
        "posted_at": timezone.now(),
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


@pytest.mark.django_db
def test_get_listings_returns_score_field():
    listing = _make_listing()

    url = reverse("api:listings-list")
    response = APIClient().get(url)

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["results"][0]["id"] == listing.id
    assert "score" in data["results"][0]


@pytest.mark.django_db
def test_get_listings_filters_by_state():
    _make_listing(state="TX")
    _make_listing(state="CA", url="https://example.com/listing/ca-1")

    url = reverse("api:listings-list")
    response = APIClient().get(url, {"state": "TX"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert all(item["state"] == "TX" for item in results)


@pytest.mark.django_db
def test_get_listing_detail_returns_market_snapshot_key():
    listing = _make_listing(zip_code="78701")
    MarketSnapshot.objects.create(
        zip_code="78701",
        area_type="zip",
        rent_index=Decimal("1900.00"),
        price_trend=Decimal("0.0200"),
        crime_score=Decimal("3.00"),
        school_rating=Decimal("7.50"),
    )

    url = reverse("api:listings-detail", kwargs={"pk": listing.id})
    response = APIClient().get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == listing.id
    assert "market_snapshot" in data
    assert data["market_snapshot"] is not None
    assert data["market_snapshot"]["zip_code"] == "78701"


@pytest.mark.django_db
def test_get_portfolio_analytics_unauthenticated_returns_403():
    url = reverse("api:portfolio-analytics")
    response = APIClient().get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_get_portfolio_analytics_authenticated_returns_kpis(django_user_model):
    user = django_user_model.objects.create_user(
        username="investor",
        email="investor@example.com",
        password="test-pass-123",
    )
    Property.objects.create(
        user=user,
        address="111 Elm St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("250000.00"),
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("api:portfolio-analytics")
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "total_noi" in data
    assert "avg_cap_rate" in data
    assert "avg_coc" in data
