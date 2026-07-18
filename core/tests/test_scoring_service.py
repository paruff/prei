"""Tests for the underwriting scoring service (core/services/scoring.py)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Listing, Property
from core.services.scoring import score_listing, score_listing_v2


@pytest.fixture
def user(db) -> object:
    return get_user_model().objects.create_user(
        username="scoreuser", password="testpass1234"
    )


@pytest.fixture
def cheap_property(user) -> Property:
    return Property.objects.create(
        user=user,
        address="100 Cashflow Ln",
        purchase_price=Decimal("100000"),
        monthly_rent_gross=Decimal("1800"),
        property_type="SFR",
    )


@pytest.fixture
def expensive_property(user) -> Property:
    return Property.objects.create(
        user=user,
        address="500 Luxury Blvd",
        purchase_price=Decimal("500000"),
        monthly_rent_gross=Decimal("1200"),
        property_type="CONDO",
    )


class TestScoreListingV2:
    def test_returns_score_object(self, cheap_property: Property) -> None:
        from core.models import UserInvestmentTargets

        targets = UserInvestmentTargets.objects.get_or_create(user=cheap_property.user)[
            0
        ]
        score = score_listing_v2(cheap_property, targets)
        assert score.total_score >= 0
        assert score.verdict is not None
        assert score.cash_on_cash is not None
        assert score.cap_rate is not None
        assert score.grm is not None

    def test_strong_cashflow_scores_higher(
        self, cheap_property: Property, expensive_property: Property
    ) -> None:
        from core.models import UserInvestmentTargets

        cheap_targets = UserInvestmentTargets.objects.get_or_create(
            user=cheap_property.user
        )[0]
        expensive_targets = UserInvestmentTargets.objects.get_or_create(
            user=expensive_property.user
        )[0]
        cheap_score = score_listing_v2(cheap_property, cheap_targets)
        expensive_score = score_listing_v2(expensive_property, expensive_targets)
        assert cheap_score.total_score > expensive_score.total_score


class TestScoreListing:
    """Tests for the Listing scoring function (replaces deprecated score_listing_v1)."""

    @pytest.fixture
    def listing(self, db) -> Listing:
        return Listing.objects.create(
            source="dummy",
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
            price=Decimal("300000"),
            sq_ft=1500,
            posted_at=timezone.now(),
            url="https://example.com/listing/1",
        )

    def test_returns_decimal(self, listing: Listing) -> None:
        result = score_listing(listing)
        assert isinstance(result, Decimal)

    def test_higher_score_for_lower_ppsf(self, listing: Listing) -> None:
        """A listing with lower price-per-sqft should score higher."""
        listing.price = Decimal("200000")
        listing.sq_ft = 2000
        cheap = score_listing(listing)
        listing.price = Decimal("500000")
        listing.sq_ft = 1000
        expensive = score_listing(listing)
        assert cheap > expensive

    def test_zero_sq_ft_does_not_crash(self, listing: Listing) -> None:
        """When sq_ft is 0, the function uses 0 and doesn't divide by zero."""
        listing.sq_ft = 0
        result = score_listing(listing)
        assert isinstance(result, Decimal)

    def test_recent_listing_scores_higher(self, listing: Listing) -> None:
        """A listing posted very recently should have a higher freshness bonus."""
        from datetime import timedelta
        from django.utils import timezone as tz

        listing.price = Decimal("300000")
        listing.sq_ft = 1500
        listing.posted_at = tz.now()
        fresh = score_listing(listing)
        listing.posted_at = tz.now() - timedelta(days=30)
        stale = score_listing(listing)
        assert fresh > stale
