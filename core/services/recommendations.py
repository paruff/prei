"""Personalized listing recommendation service."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, TypedDict

from django.contrib.auth.models import AbstractBaseUser

from core.models import Listing, SavedSearch
from investor_app.finance.utils import score_listing_v1

logger = logging.getLogger(__name__)
THOUSANDS_DIVISOR = Decimal("1000")


class RankedListing(TypedDict):
    obj: Listing
    score: Decimal


class Recommendation(TypedDict):
    obj: Listing
    score: Decimal
    explanation: str


def _search_queryset(saved_search: SavedSearch):
    qs = Listing.objects.all()
    if saved_search.query:
        qs = qs.filter(address__icontains=saved_search.query)
    if saved_search.zip_code:
        qs = qs.filter(zip_code__iexact=saved_search.zip_code)
    if saved_search.state:
        qs = qs.filter(state__iexact=saved_search.state)
    if saved_search.min_price is not None:
        qs = qs.filter(price__gte=saved_search.min_price)
    if saved_search.max_price is not None:
        qs = qs.filter(price__lte=saved_search.max_price)
    return qs


def _normalize_ranked_results(ranked: Any) -> list[RankedListing]:
    normalized: list[RankedListing] = []
    if not isinstance(ranked, list):
        return normalized

    for item in ranked:
        if isinstance(item, Listing):
            normalized.append({"obj": item, "score": score_listing_v1(item)})
            continue

        if not isinstance(item, dict):
            continue

        listing = item.get("obj") or item.get("listing")
        if not isinstance(listing, Listing):
            continue

        raw_score = item.get("score", item.get("composite_score"))
        if raw_score is None:
            score = score_listing_v1(listing)
        else:
            try:
                score = Decimal(str(raw_score))
            except (InvalidOperation, ValueError, TypeError):
                score = score_listing_v1(listing)

        normalized.append({"obj": listing, "score": score})

    return normalized


def _rank_listings(listings: list[Listing]) -> list[RankedListing]:
    try:
        from core.services.ranking import rank_listings  # type: ignore

        ranked = _normalize_ranked_results(rank_listings(listings))
        if ranked:
            return ranked
    except Exception:
        logger.exception(
            "recommend_listings: rank_listings unavailable, using fallback"
        )

    scored: list[RankedListing] = [
        {"obj": listing, "score": score_listing_v1(listing)} for listing in listings
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def recommend_listings(user: AbstractBaseUser, limit: int = 10) -> list[Recommendation]:
    """Recommend listings for a user based on saved searches."""
    if not getattr(user, "is_authenticated", False):
        return []

    try:
        safe_limit = int(limit)
    except (TypeError, ValueError):
        safe_limit = 0
    if safe_limit <= 0:
        return []

    user_id = getattr(user, "id", None)
    if not isinstance(user_id, int):
        return []

    saved_searches = list(
        SavedSearch.objects.filter(user_id=user_id).order_by("-created_at")
    )
    if not saved_searches:
        return []

    combined_qs = Listing.objects.none()
    search_by_listing_id: dict[int, SavedSearch] = {}
    for saved_search in saved_searches:
        search_qs = _search_queryset(saved_search)
        combined_qs = combined_qs | search_qs
        for listing_id in search_qs.values_list("id", flat=True):
            search_by_listing_id.setdefault(listing_id, saved_search)

    ranked = _rank_listings(list(combined_qs.distinct()))

    recommendations: list[Recommendation] = []
    for item in ranked:
        listing = item["obj"]
        matching_search = search_by_listing_id.get(listing.id)
        if matching_search is None:
            continue
        recommendations.append(
            {
                "obj": listing,
                "score": item["score"],
                "explanation": explain_recommendation(listing, matching_search),
            }
        )
        if len(recommendations) >= safe_limit:
            break

    return recommendations


def explain_recommendation(listing: Listing, saved_search: SavedSearch) -> str:
    """Return a human-readable recommendation reason."""
    location = listing.state or saved_search.state or "your area"
    beds_text = f" with {listing.beds} beds" if listing.beds is not None else ""
    price_in_thousands = (listing.price / THOUSANDS_DIVISOR).quantize(Decimal("1"))
    return (
        f"Matches your search '{saved_search.name}': "
        f"${price_in_thousands}k in {location}{beds_text}"
    )
