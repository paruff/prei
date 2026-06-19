"""Tests for the Deal Screener dashboard."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.models import (
    MarketSnapshot,
    Property,
    UserInvestmentTargets,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="screener", password="pass")


@pytest.fixture
def client_logged_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def targets(db, user):
    return UserInvestmentTargets.objects.create(
        user=user,
        min_coc_pct=Decimal("0.08"),
        min_dscr=Decimal("1.25"),
        max_grm=Decimal("12.00"),
        require_one_pct_rule=True,
        target_hold_years=7,
        marginal_tax_rate=Decimal("0.24"),
    )


@pytest.fixture
def strong_property(db, user):
    return Property.objects.create(
        user=user,
        address="100 Strong Ave",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("200000"),
        monthly_rent_gross=Decimal("2500"),
        property_taxes_annual=Decimal("2400"),
        insurance_annual=Decimal("1200"),
        hoa_monthly=Decimal("0"),
        maintenance_monthly=Decimal("100"),
        capex_monthly=Decimal("50"),
        down_payment_pct=Decimal("0.20"),
        interest_rate=Decimal("0.06"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.05"),
        mgmt_fee_pct=Decimal("0.08"),
    )


@pytest.fixture
def weak_property(db, user):
    return Property.objects.create(
        user=user,
        address="200 Weak Blvd",
        city="Denver",
        state="CO",
        zip_code="80202",
        purchase_price=Decimal("500000"),
        monthly_rent_gross=Decimal("2000"),
        property_taxes_annual=Decimal("6000"),
        insurance_annual=Decimal("2400"),
        hoa_monthly=Decimal("200"),
        maintenance_monthly=Decimal("300"),
        capex_monthly=Decimal("200"),
        down_payment_pct=Decimal("0.25"),
        interest_rate=Decimal("0.07"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.10"),
        mgmt_fee_pct=Decimal("0.10"),
    )


@pytest.fixture
def incomplete_property(db, user):
    """Property with zero rent — should show Incomplete Data badge."""
    return Property.objects.create(
        user=user,
        address="300 Empty Rd",
        city="Dallas",
        state="TX",
        zip_code="75201",
        purchase_price=Decimal("150000"),
        monthly_rent_gross=Decimal("0"),
    )


@pytest.fixture
def market_snapshot(db):
    return MarketSnapshot.objects.create(
        area_type="zip",
        zip_code="78702",
        city="Austin",
        state="TX",
        population=100000,
        population_growth_pct_5yr=Decimal("0.0250"),
        unemployment_rate=Decimal("0.0350"),
    )


# ── Basic rendering ───────────────────────────────────────────────────────────


class TestDashboardRenders:
    """Dashboard loads and shows properties with scores."""

    def test_dashboard_loads(self, client_logged_in, targets, strong_property, market_snapshot):
        resp = client_logged_in.get(reverse("dashboard"))
        assert resp.status_code == 200

    def test_dashboard_title(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        assert "Deal Screener" in resp.content.decode()

    def test_shows_property_address(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        assert "100 Strong Ave" in resp.content.decode()

    def test_shows_underwriting_score(self, client_logged_in, targets, strong_property, market_snapshot):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # Score should be present
        assert "data-score=" in content

    def test_shows_verdict_badge(self, client_logged_in, targets, strong_property, market_snapshot):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "Strong Buy" in content or "Conditional" in content or "Pass" in content


# ── Empty state ───────────────────────────────────────────────────────────────


class TestDashboardEmptyState:
    """Empty state shows helpful message and add property link."""

    def test_empty_state_message(self, client_logged_in):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "No properties yet" in content

    def test_empty_state_has_add_link(self, client_logged_in):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert reverse("property_add") in content


# ── Incomplete data badge ────────────────────────────────────────────────────


class TestIncompleteDataBadge:
    """Properties with missing data show Incomplete Data badge."""

    def test_incomplete_badge_shown(self, client_logged_in, targets, incomplete_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "Incomplete Data" in content

    def test_incomplete_no_score(self, client_logged_in, targets, incomplete_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # Incomplete property should not have a score
        assert "data-score=\"0\"" in content


# ── Filters present ───────────────────────────────────────────────────────────


class TestDashboardFilters:
    """Filters are present in the template."""

    def test_min_score_slider(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "filter-min-score" in content

    def test_verdict_checkboxes(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "filter-verdict" in content
        assert "Strong Buy" in content
        assert "Conditional" in content
        assert "Pass" in content

    def test_state_filter(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "filter-state" in content

    def test_one_pct_toggle(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "filter-one-pct" in content


# ── Sorting ───────────────────────────────────────────────────────────────────


class TestDashboardSorting:
    """Table headers support sorting."""

    def test_sort_headers_present(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert 'data-sort="score"' in content
        assert 'data-sort="coc"' in content
        assert 'data-sort="cap_rate"' in content


# ── Auth required ─────────────────────────────────────────────────────────────


class TestDashboardAuth:
    """Unauthenticated users are redirected to login."""

    def test_unauthenticated_redirect(self, client, db):
        resp = client.get(reverse("dashboard"))
        assert resp.status_code == 302
        assert "login" in resp.url


# ── Multiple properties ───────────────────────────────────────────────────────


class TestDashboardMultipleProperties:
    """Dashboard shows multiple properties with different scores."""

    def test_two_properties_shown(
        self, client_logged_in, targets, strong_property, weak_property, market_snapshot
    ):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "100 Strong Ave" in content
        assert "200 Weak Blvd" in content

    def test_results_count(
        self, client_logged_in, targets, strong_property, weak_property, market_snapshot
    ):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "2 properties" in content or "Showing 2" in content
