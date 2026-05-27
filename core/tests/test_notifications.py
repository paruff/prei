from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import ForeclosureProperty, Notification


@pytest.fixture
def foreclosure_property(db):
    return ForeclosureProperty.objects.create(
        property_id="NOTICE001",
        data_source="test",
        data_timestamp=timezone.now(),
        street="100 Auction Ave",
        city="Austin",
        state="TX",
        zip_code="78701",
        foreclosure_status="auction",
        auction_date=timezone.now().date() + timedelta(days=3),
        opening_bid=Decimal("200000.00"),
    )


def test_notifications_api_returns_only_user_notifications(
    auth_client, user, second_user, foreclosure_property
):
    Notification.objects.create(
        user=user,
        notification_type="auction_update",
        title="My Auction",
        body="Body",
        property=foreclosure_property,
    )
    Notification.objects.create(
        user=second_user,
        notification_type="auction_update",
        title="Other Auction",
        body="Body",
        property=foreclosure_property,
    )

    response = auth_client.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["title"] == "My Auction"
    assert data["notifications"][0]["propertyAddress"] == "100 Auction Ave, Austin, TX"


def test_mark_notification_read(auth_client, user, foreclosure_property):
    notification = Notification.objects.create(
        user=user,
        notification_type="status_change",
        title="Status changed",
        body="Body",
        property=foreclosure_property,
    )

    response = auth_client.post(f"/api/v1/notifications/{notification.id}/read")
    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.is_read is True


def test_unread_count_decrements_on_read(auth_client, user, foreclosure_property):
    first = Notification.objects.create(
        user=user,
        notification_type="auction_update",
        title="First",
        body="Body",
        property=foreclosure_property,
    )
    Notification.objects.create(
        user=user,
        notification_type="auction_update",
        title="Second",
        body="Body",
        property=foreclosure_property,
    )

    initial = auth_client.get("/api/v1/notifications")
    assert initial.status_code == 200
    assert len(initial.json()["notifications"]) == 2

    read_response = auth_client.post(f"/api/v1/notifications/{first.id}/read")
    assert read_response.status_code == 200

    updated = auth_client.get("/api/v1/notifications")
    assert updated.status_code == 200
    assert len(updated.json()["notifications"]) == 1
    assert updated.json()["notifications"][0]["title"] == "Second"
