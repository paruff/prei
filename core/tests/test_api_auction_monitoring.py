from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    AuctionAlert,
    ForeclosureProperty,
    Notification,
    NotificationPreference,
    UserWatchlist,
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def authenticated_client(api_client, user):
    """Create authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def foreclosure_property(db):
    """Create a test foreclosure property."""
    return ForeclosureProperty.objects.create(
        property_id="TEST001",
        data_source="test",
        data_timestamp=timezone.now(),
        street="123 Test St",
        city="Test City",
        state="CA",
        zip_code="90210",
        foreclosure_status="auction",
        auction_date=timezone.now().date() + timedelta(days=7),
        opening_bid=Decimal("250000.00"),
    )


class TestWatchlistAPI:
    """Test watchlist API endpoints."""

    def test_get_watchlist_unauthenticated(self, api_client):
        """Test getting watchlist requires authentication."""
        response = api_client.get("/api/v1/watchlist")
        assert response.status_code == 401

    def test_get_empty_watchlist(self, authenticated_client):
        """Test getting empty watchlist."""
        response = authenticated_client.get("/api/v1/watchlist")
        assert response.status_code == 200
        assert response.json()["watchlist"] == []

    def test_get_watchlist_with_items(
        self, authenticated_client, user, foreclosure_property
    ):
        """Test getting watchlist with items."""
        UserWatchlist.objects.create(
            user=user, property=foreclosure_property, notes="Test note"
        )

        response = authenticated_client.get("/api/v1/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert len(data["watchlist"]) == 1
        assert data["watchlist"][0]["propertyId"] == "TEST001"
        assert data["watchlist"][0]["notes"] == "Test note"

    def test_add_to_watchlist(self, authenticated_client, foreclosure_property):
        """Test adding property to watchlist."""
        response = authenticated_client.post(
            "/api/v1/watchlist",
            {"propertyId": str(foreclosure_property.id), "notes": "Interesting"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["propertyId"] == "TEST001"
        assert response.json()["notes"] == "Interesting"

        # Verify in database
        assert UserWatchlist.objects.filter(property=foreclosure_property).exists()

    def test_add_to_watchlist_duplicate(
        self, authenticated_client, user, foreclosure_property
    ):
        """Test adding duplicate property to watchlist."""
        UserWatchlist.objects.create(user=user, property=foreclosure_property)

        response = authenticated_client.post(
            "/api/v1/watchlist",
            {"propertyId": str(foreclosure_property.id)},
            format="json",
        )
        assert response.status_code == 409

    def test_add_to_watchlist_invalid_property(self, authenticated_client):
        """Test adding invalid property to watchlist."""
        response = authenticated_client.post(
            "/api/v1/watchlist", {"propertyId": "99999"}, format="json"
        )
        assert response.status_code == 404

    def test_remove_from_watchlist(
        self, authenticated_client, user, foreclosure_property
    ):
        """Test removing property from watchlist."""
        watchlist_item = UserWatchlist.objects.create(
            user=user, property=foreclosure_property
        )

        response = authenticated_client.delete(f"/api/v1/watchlist/{watchlist_item.id}")
        assert response.status_code == 204

        # Verify removed from database
        assert not UserWatchlist.objects.filter(id=watchlist_item.id).exists()

    def test_remove_from_watchlist_not_found(self, authenticated_client):
        """Test removing non-existent watchlist item."""
        response = authenticated_client.delete("/api/v1/watchlist/99999")
        assert response.status_code == 404


class TestAlertsAPI:
    """Test alerts API endpoints."""

    def test_get_alerts_unauthenticated(self, api_client):
        """Test getting alerts requires authentication."""
        response = api_client.get("/api/v1/alerts")
        assert response.status_code == 401

    def test_get_empty_alerts(self, authenticated_client):
        """Test getting empty alerts list."""
        response = authenticated_client.get("/api/v1/alerts")
        assert response.status_code == 200
        assert response.json()["alerts"] == []

    def test_create_alert(self, authenticated_client, user):
        """Test creating new alert."""
        alert_data = {
            "name": "California Auctions",
            "alertType": "new_auction",
            "isActive": True,
            "states": ["CA", "NV"],
            "minOpeningBid": "200000.00",
            "maxOpeningBid": "500000.00",
        }

        response = authenticated_client.post("/api/v1/alerts", alert_data, format="json")
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "California Auctions"
        assert data["alertType"] == "new_auction"
        assert data["states"] == ["CA", "NV"]

        # Verify in database
        alert = AuctionAlert.objects.filter(user=user).first()
        assert alert is not None
        assert alert.name == "California Auctions"

    def test_get_alert_detail(self, authenticated_client, user):
        """Test getting specific alert."""
        alert = AuctionAlert.objects.create(
            user=user,
            name="Test Alert",
            alert_type="status_change",
            states=["CA"],
        )

        response = authenticated_client.get(f"/api/v1/alerts/{alert.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Alert"
        assert data["alertType"] == "status_change"

    def test_update_alert(self, authenticated_client, user):
        """Test updating alert."""
        alert = AuctionAlert.objects.create(
            user=user,
            name="Original Name",
            alert_type="new_auction",
            is_active=True,
        )

        update_data = {"name": "Updated Name", "isActive": False}

        response = authenticated_client.put(
            f"/api/v1/alerts/{alert.id}", update_data, format="json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["isActive"] is False

        # Verify in database
        alert.refresh_from_db()
        assert alert.name == "Updated Name"
        assert alert.is_active is False

    def test_delete_alert(self, authenticated_client, user):
        """Test deleting alert."""
        alert = AuctionAlert.objects.create(
            user=user, name="Delete Me", alert_type="reminder"
        )

        response = authenticated_client.delete(f"/api/v1/alerts/{alert.id}")
        assert response.status_code == 204

        # Verify removed from database
        assert not AuctionAlert.objects.filter(id=alert.id).exists()

    def test_alert_isolation_between_users(self, authenticated_client, user):
        """Test users can't access other users' alerts."""
        other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )
        other_alert = AuctionAlert.objects.create(
            user=other_user, name="Other Alert", alert_type="new_auction"
        )

        # Try to access other user's alert
        response = authenticated_client.get(f"/api/v1/alerts/{other_alert.id}")
        assert response.status_code == 404


class TestNotificationsAPI:
    """Test notifications API endpoints."""

    def test_get_notifications_unauthenticated(self, api_client):
        """Test getting notifications requires authentication."""
        response = api_client.get("/api/v1/notifications")
        assert response.status_code == 401

    def test_get_empty_notifications(self, authenticated_client):
        """Test getting empty notifications list."""
        response = authenticated_client.get("/api/v1/notifications")
        assert response.status_code == 200
        assert response.json()["notifications"] == []

    def test_get_notifications(self, authenticated_client, user, foreclosure_property):
        """Test getting user's notifications."""
        Notification.objects.create(
            user=user,
            notification_type="auction_update",
            priority="high",
            title="Test Notification",
            body="Test body",
            property=foreclosure_property,
        )

        response = authenticated_client.get("/api/v1/notifications")
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["title"] == "Test Notification"
        assert data["notifications"][0]["priority"] == "high"

    def test_filter_notifications_by_read_status(
        self, authenticated_client, user, foreclosure_property
    ):
        """Test filtering notifications by read status."""
        # Create read and unread notifications
        Notification.objects.create(
            user=user,
            notification_type="auction_update",
            priority="medium",
            title="Unread",
            body="Body",
            property=foreclosure_property,
            is_read=False,
        )
        read_notif = Notification.objects.create(
            user=user,
            notification_type="reminder",
            priority="low",
            title="Read",
            body="Body",
            property=foreclosure_property,
            is_read=True,
        )

        # Get only unread
        response = authenticated_client.get("/api/v1/notifications?isRead=false")
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["title"] == "Unread"

        # Get only read
        response = authenticated_client.get("/api/v1/notifications?isRead=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["title"] == "Read"

    def test_mark_notification_read(self, authenticated_client, user, foreclosure_property):
        """Test marking notification as read."""
        notification = Notification.objects.create(
            user=user,
            notification_type="auction_update",
            priority="medium",
            title="Test",
            body="Body",
            property=foreclosure_property,
        )

        response = authenticated_client.post(
            f"/api/v1/notifications/{notification.id}/read"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["isRead"] is True
        assert data["readAt"] is not None

        # Verify in database
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_dismiss_notification(self, authenticated_client, user, foreclosure_property):
        """Test dismissing notification."""
        notification = Notification.objects.create(
            user=user,
            notification_type="auction_update",
            priority="medium",
            title="Test",
            body="Body",
            property=foreclosure_property,
        )

        response = authenticated_client.post(
            f"/api/v1/notifications/{notification.id}/dismiss"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["isDismissed"] is True
        assert data["dismissedAt"] is not None

        # Verify in database
        notification.refresh_from_db()
        assert notification.is_dismissed is True


class TestNotificationPreferencesAPI:
    """Test notification preferences API endpoints."""

    def test_get_preferences_creates_if_not_exists(self, authenticated_client, user):
        """Test getting preferences creates them if they don't exist."""
        response = authenticated_client.get("/api/v1/notification-preferences")
        assert response.status_code == 200

        # Verify created in database
        assert NotificationPreference.objects.filter(user=user).exists()

    def test_update_preferences(self, authenticated_client, user):
        """Test updating notification preferences."""
        prefs = NotificationPreference.objects.create(user=user)

        update_data = {
            "notifyEmail": True,
            "notifySms": True,
            "notifyPush": False,
            "email": "test@example.com",
            "phone": "+1234567890",
            "quietHoursStart": "22:00:00",
            "quietHoursEnd": "08:00:00",
        }

        response = authenticated_client.put(
            "/api/v1/notification-preferences", update_data, format="json"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notifyEmail"] is True
        assert data["notifySms"] is True
        assert data["notifyPush"] is False
        assert data["email"] == "test@example.com"

        # Verify in database
        prefs.refresh_from_db()
        assert prefs.notify_email is True
        assert prefs.notify_sms is True
        assert prefs.email == "test@example.com"
