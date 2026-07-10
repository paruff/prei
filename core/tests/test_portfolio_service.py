"""Tests for the portfolio service (core/services/portfolio.py).

Covers:
  - aggregate_portfolio: total NOI, avg cap rate, avg CoC
  - compute_portfolio_summary: total properties, capital, NOI, cap rate, cash flow
  - check_flag_for_attention: threshold flags by property
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import Property
from core.services.portfolio import (
    aggregate_portfolio,
    check_flag_for_attention,
    compute_portfolio_summary,
)


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="portuser", password="testpass1234"
    )


@pytest.fixture
def owned_property(user) -> Property:
    return Property.objects.create(
        user=user,
        address="123 Portfolio St",
        purchase_price=Decimal("200000"),
        monthly_rent_gross=Decimal("2000"),
        bedrooms=3,
        property_type="SFR",
    )


@pytest.fixture
def second_property(user) -> Property:
    return Property.objects.create(
        user=user,
        address="456 Equity Ave",
        purchase_price=Decimal("150000"),
        monthly_rent_gross=Decimal("1500"),
        bedrooms=2,
        property_type="CONDO",
    )


# ── aggregate_portfolio ──────────────────────────────────────────────


class TestAggregatePortfolio:
    def test_empty_portfolio(self, user) -> None:
        """No properties returns zeroed metrics."""
        result = aggregate_portfolio(user)
        assert result["total_noi"] == Decimal("0")
        assert result["avg_cap_rate"] == Decimal("0")
        assert result["avg_coc"] == Decimal("0")

    def test_single_property(self, user, owned_property: Property) -> None:
        """Single property returns metrics (NOI may be > 0)."""
        result = aggregate_portfolio(user)
        assert isinstance(result["total_noi"], Decimal)
        assert isinstance(result["avg_cap_rate"], Decimal)

    def test_multiple_properties(
        self, user, owned_property: Property, second_property: Property
    ) -> None:
        """Multiple properties are aggregated."""
        result = aggregate_portfolio(user)
        assert isinstance(result["total_noi"], Decimal)
        assert isinstance(result["avg_cap_rate"], Decimal)


# ── compute_portfolio_summary ───────────────────────────────────────


class TestComputePortfolioSummary:
    def test_empty_summary(self, user) -> None:
        """No properties returns zero for all KPIs."""
        summary = compute_portfolio_summary(user)
        assert summary["total_properties"] == 0
        assert summary["total_capital_invested"] == Decimal("0")
        assert summary["total_annual_noi"] == Decimal("0")

    def test_summary_with_property(
        self, user, owned_property: Property
    ) -> None:
        """Single property produces a valid summary."""
        summary = compute_portfolio_summary(user)
        assert summary["total_properties"] == 1
        assert summary["total_capital_invested"] > Decimal("0")

    def test_summary_total_capital_invested(
        self, user, owned_property: Property, second_property: Property
    ) -> None:
        """Total capital invested sums purchase prices."""
        summary = compute_portfolio_summary(user)
        assert summary["total_properties"] == 2
        assert summary["total_capital_invested"] == Decimal("350000")


# ── check_flag_for_attention ─────────────────────────────────────────


class TestCheckFlagForAttention:
    def test_no_flag_when_healthy(self, user, owned_property: Property) -> None:
        """Property with no variance is not flagged."""
        flagged = check_flag_for_attention(owned_property)
        assert flagged is False

    def test_returns_bool(self, user, owned_property: Property) -> None:
        """Return value is a boolean."""
        flagged = check_flag_for_attention(owned_property)
        assert isinstance(flagged, bool)
