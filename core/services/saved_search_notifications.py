"""Saved Search Notifications Service.

Checks new listings against user saved searches and creates notifications
when matching properties are found.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import SavedSearch, User

logger = logging.getLogger(__name__)


def get_saved_search_matches(
    saved_search: SavedSearch,
    listings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Get listings that match a saved search criteria.

    Args:
        saved_search: SavedSearch model instance with filter criteria
        listings: List of listing dictionaries with price, state, zip_code

    Returns:
        List of matching listings
    """
    matches = []

    for listing in listings:
        # Check price range
        price = listing.get("price")
        if saved_search.min_price and price and price < saved_search.min_price:
            continue
        if saved_search.max_price and price and price > saved_search.max_price:
            continue

        # Check state
        if saved_search.state and listing.get("state") != saved_search.state:
            continue

        # Check zip code
        if saved_search.zip_code and listing.get("zip_code") != saved_search.zip_code:
            continue

        matches.append(listing)

    return matches


def create_notification_for_match(
    saved_search: SavedSearch,
    listing: Dict[str, Any],
) -> Any:
    """Create a notification for a saved search match.

    Args:
        saved_search: The saved search that found a match
        listing: The listing that matched

    Returns:
        Created notification object or None
    """
    from core.models import Notification

    # Create in-app notification
    notification = Notification.objects.create(
        user=saved_search.user,
        notification_type="saved_search_match",
        title=f"New listing matches '{saved_search.name}'",
        body=f"{listing.get('address', 'Unknown address')} - ${listing.get('price', 0)}",
        data={
            "saved_search_id": saved_search.id,
            "listing": {k: str(v) if isinstance(v, Decimal) else v for k, v in listing.items()},
        },
    )

    return notification


def check_listings_against_saved_searches() -> Dict[str, Any]:
    """Check new listings against all active saved searches.

    Returns:
        Dictionary with statistics about the check
    """
    # Get all active saved searches
    saved_searches = SavedSearch.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)  # Last 30 days
    )

    stats = {
        "searches_checked": 0,
        "matches_found": 0,
        "notifications_created": 0,
    }

    # Fetch new listings (this would normally call an external API)
    listings = fetch_new_listings()

    for saved_search in saved_searches:
        matches = get_saved_search_matches(saved_search, listings)
        if matches:
            for match in matches:
                notification = create_notification_for_match(saved_search, match)
                if notification:
                    stats["notifications_created"] += 1
            stats["matches_found"] += len(matches)

        stats["searches_checked"] += 1

    return stats


def fetch_new_listings() -> List[Dict[str, Any]]:
    """Fetch new listings from external data sources.

    In production, this would call the RESO Web API, ATTOM, or other
    data sources to get new listings. For now, returns empty list.

    Returns:
        List of new listing dictionaries
    """
    # Placeholder implementation - in production would call RESO Web API
    # or other data sources
    return []