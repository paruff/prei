"""Integration tests for the listing report view (Phase 2.4)."""
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from core.models import Listing, MarketSnapshot


def _make_listing(**kwargs) -> Listing:
    """Create a minimal Listing with sensible defaults."""
    defaults = dict(
        source="test",
        address="42 Oak Ave",
        city="Austin",
        state="TX",
        zip_code="78701",
        price=Decimal("300000"),
        beds=3,
        baths=Decimal("2.0"),
        sq_ft=1500,
        property_type="SFH",
        url="https://example.com/listing/1",
        posted_at=timezone.now(),
    )
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


@pytest.mark.django_db
def test_report_listing_returns_200(client):
    """GET listing/<id>/report/ returns HTTP 200 for an existing listing."""
    listing = _make_listing()
    url = reverse("report_listing", kwargs={"listing_id": listing.id})
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_report_listing_context_keys_present(client):
    """Context must include score, ppsf, and kpis keys."""
    listing = _make_listing()
    url = reverse("report_listing", kwargs={"listing_id": listing.id})
    resp = client.get(url)
    assert resp.status_code == 200
    assert "score" in resp.context
    assert "ppsf" in resp.context
    assert "kpis" in resp.context
    assert "market_snapshot" in resp.context


@pytest.mark.django_db
def test_report_listing_kpis_keys(client):
    """kpis dict must contain cap_rate, cash_on_cash, dscr, noi."""
    listing = _make_listing()
    url = reverse("report_listing", kwargs={"listing_id": listing.id})
    resp = client.get(url)
    kpis = resp.context["kpis"]
    for key in ("cap_rate", "cash_on_cash", "dscr", "noi"):
        assert key in kpis, f"kpis missing '{key}'"


@pytest.mark.django_db
def test_report_listing_no_market_snapshot_still_200(client):
    """Page loads without error even when no MarketSnapshot exists for the ZIP."""
    listing = _make_listing(zip_code="99999")
    # Ensure no snapshot exists for this ZIP
    MarketSnapshot.objects.filter(zip_code="99999").delete()
    url = reverse("report_listing", kwargs={"listing_id": listing.id})
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["market_snapshot"] is None
    assert "N/A" in resp.content.decode()


@pytest.mark.django_db
def test_report_listing_with_market_snapshot(client):
    """When a MarketSnapshot exists, market data is shown in the response."""
    listing = _make_listing(zip_code="78701")
    MarketSnapshot.objects.create(
        zip_code="78701",
        area_type="zip",
        rent_index=Decimal("1800.00"),
        price_trend=Decimal("0.0333"),
        crime_score=Decimal("2.5"),
        school_rating=Decimal("8.0"),
    )
    url = reverse("report_listing", kwargs={"listing_id": listing.id})
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["market_snapshot"] is not None
    content = resp.content.decode()
    assert "1800" in content  # rent_index displayed


@pytest.mark.django_db
def test_report_listing_404_for_unknown_id(client):
    """GET listing/<nonexistent-id>/report/ returns HTTP 404."""
    url = reverse("report_listing", kwargs={"listing_id": 999999})
    resp = client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_report_listing_kpis_nonzero_for_valid_listing(client):
    """KPIs are non-zero when listing has a valid price."""
    listing = _make_listing(price=Decimal("300000"), sq_ft=1500)
    url = reverse("report_listing", kwargs={"listing_id": listing.id})
    resp = client.get(url)
    kpis = resp.context["kpis"]
    assert kpis["noi"] != Decimal("0"), "NOI should be non-zero for a priced listing"
    assert kpis["cap_rate"] != Decimal("0"), "Cap rate should be non-zero"
