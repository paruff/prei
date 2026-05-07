from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import Listing, SavedSearch
from core.services.recommendations import explain_recommendation, recommend_listings


class _SavedSearchList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_by_called_with = None

    def order_by(self, *_args):
        self.order_by_called_with = _args
        return self


def _create_listing(
    *,
    address: str,
    state: str = "AZ",
    zip_code: str = "85001",
    price: str = "150000",
    sq_ft: int = 1000,
) -> Listing:
    return Listing.objects.create(
        source="dummy",
        address=address,
        city="Phoenix",
        state=state,
        zip_code=zip_code,
        price=Decimal(price),
        beds=3,
        baths=Decimal("2.0"),
        sq_ft=sq_ft,
        property_type="SFH",
        url=f"https://example.com/{address.lower().replace(' ', '-')}",
        posted_at=timezone.now(),
    )


@pytest.mark.django_db
def test_recommend_listings_returns_empty_without_saved_searches(user, monkeypatch):
    saved_searches = _SavedSearchList()
    monkeypatch.setattr(
        SavedSearch.objects,
        "filter",
        lambda **_kwargs: saved_searches,
    )
    _create_listing(address="100 Main St")

    assert recommend_listings(user) == []
    assert saved_searches.order_by_called_with == ("-created_at",)


@pytest.mark.django_db
def test_recommend_listings_returns_matches_sorted_by_score(user, monkeypatch):
    saved_searches = _SavedSearchList(
        [SavedSearch(user=user, name="AZ Deals", state="AZ", query="", zip_code="")]
    )
    monkeypatch.setattr(SavedSearch.objects, "filter", lambda **_kwargs: saved_searches)

    lower_score = _create_listing(
        address="200 Main St", state="AZ", price="200000", sq_ft=1000
    )
    higher_score = _create_listing(
        address="300 Main St", state="AZ", price="180000", sq_ft=1200
    )

    recommendations = recommend_listings(user)

    assert [item["obj"].id for item in recommendations] == [
        higher_score.id,
        lower_score.id,
    ]


@pytest.mark.django_db
def test_recommend_listings_deduplicates_matches_from_multiple_saved_searches(
    user, monkeypatch
):
    saved_searches = _SavedSearchList(
        [
            SavedSearch(user=user, name="AZ", state="AZ", query="", zip_code=""),
            SavedSearch(
                user=user, name="Phoenix Zip", state="", query="", zip_code="85001"
            ),
        ]
    )
    monkeypatch.setattr(SavedSearch.objects, "filter", lambda **_kwargs: saved_searches)

    listing = _create_listing(address="400 Main St", state="AZ", zip_code="85001")

    recommendations = recommend_listings(user)

    assert len(recommendations) == 1
    assert recommendations[0]["obj"].id == listing.id


@pytest.mark.django_db
def test_recommend_listings_respects_limit(user, monkeypatch):
    saved_searches = _SavedSearchList(
        [SavedSearch(user=user, name="AZ Deals", state="AZ", query="", zip_code="")]
    )
    monkeypatch.setattr(SavedSearch.objects, "filter", lambda **_kwargs: saved_searches)

    _create_listing(address="500 Main St", state="AZ")
    _create_listing(address="600 Main St", state="AZ")
    _create_listing(address="700 Main St", state="AZ")

    recommendations = recommend_listings(user, limit=2)

    assert len(recommendations) == 2


@pytest.mark.django_db
def test_explain_recommendation_contains_saved_search_name(user):
    saved_search = SavedSearch(user=user, name="Downtown Flips", state="AZ")
    listing = _create_listing(address="800 Main St", state="AZ", price="150000")

    explanation = explain_recommendation(listing, saved_search)

    assert explanation
    assert saved_search.name in explanation
