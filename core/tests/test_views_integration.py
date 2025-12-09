import pytest
from django.urls import reverse
from decimal import Decimal
from django.utils import timezone

from core.models import Property, Listing


@pytest.mark.django_db
def test_dashboard_shows_analyze_link(client, user):
    p = Property.objects.create(
        user=user,
        address="1 Test Rd",
        city="Testville",
        state="TX",
        zip_code="00000",
        purchase_price=Decimal("100000"),
    )
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert f"/analyze/{p.id}/" in resp.content.decode()


@pytest.mark.django_db
def test_search_listings_filters_by_state_and_zip(client):
    Listing.objects.create(
        source="dummy",
        address="123 Main",
        city="Austin",
        state="TX",
        zip_code="78701",
        price=Decimal("300000"),
        beds=3,
        baths=Decimal("2.0"),
        sq_ft=1500,
        property_type="SFH",
        url="https://example.com/tx",
        posted_at=timezone.now(),
    )
    Listing.objects.create(
        source="dummy",
        address="55 Pine",
        city="Denver",
        state="CO",
        zip_code="80203",
        price=Decimal("500000"),
        beds=4,
        baths=Decimal("2.5"),
        sq_ft=2000,
        property_type="SFH",
        url="https://example.com/co",
        posted_at=timezone.now(),
    )

    resp = client.get(reverse("search_listings"), {"state": "TX", "zip": "78701"})
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Austin" in html
    assert "Denver" not in html
