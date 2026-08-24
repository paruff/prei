"""Tests for saved searches with email/in-app notifications."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

from core.models.growth import SavedSearch
from core.services.saved_search_notifications import (
    check_listings_against_saved_searches,
    get_saved_search_matches,
    create_notification_for_match,
)


class TestSavedSearchMatches:
    """Tests for checking listings against saved searches."""

    def test_get_saved_search_matches(self) -> None:
        """Test that saved search returns matching listings."""
        from core.services.saved_search_notifications import get_saved_search_matches

        saved_search = SavedSearch(
            name="Test Search",
            state="TX",
            zip_code="78701",
            min_price=Decimal("300000"),
            max_price=Decimal("500000"),
        )

        # Mock listings data (would normally come from external API)
        listings = [
            {"price": Decimal("350000"), "state": "TX", "zip_code": "78701"},
            {"price": Decimal("450000"), "state": "TX", "zip_code": "78701"},
            {"price": Decimal("250000"), "state": "TX", "zip_code": "78701"},  # Below min_price
            {"price": Decimal("550000"), "state": "TX", "zip_code": "78701"},  # Above max_price
        ]

        matches = get_saved_search_matches(saved_search, listings)

        # Should only match listings within price range
        assert len(matches) == 2

    def test_get_saved_search_matches_empty(self) -> None:
        """Test that no matches returns empty list."""
        from core.services.saved_search_notifications import get_saved_search_matches

        saved_search = SavedSearch(
            name="Test Search",
            state="TX",
            zip_code="78701",
            min_price=Decimal("300000"),
            max_price=Decimal("500000"),
        )

        listings = [
            {"price": Decimal("250000"), "state": "TX", "zip_code": "78701"},
            {"price": Decimal("550000"), "state": "TX", "zip_code": "78701"},
        ]

        matches = get_saved_search_matches(saved_search, listings)
        assert len(matches) == 0


@pytest.mark.django_db
class TestNotificationCreation:
    """Tests for creating notifications for matches."""

    def test_create_notification_for_match(self) -> None:
        """Test that notification is created for a match."""
        from core.services.saved_search_notifications import create_notification_for_match
        from core.models import User

        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        saved_search = SavedSearch.objects.create(
            user=user,
            name="Downtown Search",
            state="TX",
            zip_code="78701",
            min_price=Decimal("300000"),
            max_price=Decimal("500000"),
        )

        listing = {
            "price": Decimal("350000"),
            "state": "TX",
            "zip_code": "78701",
            "address": "123 Main St",
        }

        notification = create_notification_for_match(saved_search, listing)

        assert notification is not None
        assert notification.user == user
        assert "Downtown Search" in notification.title


@pytest.mark.django_db
class TestCheckListings:
    """Tests for checking listings against saved searches."""

    def test_check_listings_creates_notifications(self) -> None:
        """Test that checking listings creates notifications for matches."""
        from core.services.saved_search_notifications import check_listings_against_saved_searches
        from core.models import User
        from unittest.mock import patch

        user = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123"
        )

        saved_search = SavedSearch.objects.create(
            user=user,
            name="Test Search",
            state="TX",
            zip_code="78701",
            min_price=Decimal("300000"),
            max_price=Decimal("500000"),
        )

        # Mock the listings data
        mock_listings = [
            {"price": Decimal("350000"), "state": "TX", "zip_code": "78701"},
            {"price": Decimal("450000"), "state": "TX", "zip_code": "78701"},
        ]

        with patch("core.services.saved_search_notifications.fetch_new_listings", return_value=mock_listings):
            result = check_listings_against_saved_searches()

        assert result["searches_checked"] >= 1
        assert result["matches_found"] >= 2


class TestSavedSearchAdmin:
    """Tests for saved search admin configuration."""

    def test_saved_search_admin_fields(self) -> None:
        """Test that SavedSearchAdmin has correct fields."""
        from core.admin import SavedSearchAdmin

        assert "user" in SavedSearchAdmin.list_display
        assert "name" in SavedSearchAdmin.list_display
        assert "state" in SavedSearchAdmin.list_display
        assert "zip_code" in SavedSearchAdmin.list_display
        assert "min_price" in SavedSearchAdmin.list_display
        assert "max_price" in SavedSearchAdmin.list_display
        assert "created_at" in SavedSearchAdmin.list_display
