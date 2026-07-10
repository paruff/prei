"""Tests for the underwriting scoring service (core/services/scoring.py)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from core.models import Property
from core.services.scoring import score_listing_v2


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
