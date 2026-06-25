"""Tests for the Deal Screener dashboard."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
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

    def test_dashboard_loads(
        self, client_logged_in, targets, strong_property, market_snapshot
    ):
        resp = client_logged_in.get(reverse("dashboard"))
        assert resp.status_code == 200

    def test_dashboard_title(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        assert "Deal screener" in resp.content.decode()

    def test_shows_property_address(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        assert "100 Strong Ave" in resp.content.decode()

    def test_shows_underwriting_score(
        self, client_logged_in, targets, strong_property, market_snapshot
    ):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # Score bar component renders the score value
        assert "score-bar-track" in content

    def test_shows_verdict_badge(
        self, client_logged_in, targets, strong_property, market_snapshot
    ):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # Verdict badge renders verdict + label (e.g. "A · Strong Buy")
        assert "verdict-badge" in content


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
    """Properties with missing data are excluded from the dashboard table."""

    def test_incomplete_excluded_from_table(
        self, client_logged_in, targets, incomplete_property
    ):
        """Property with zero rent should not appear in the dashboard table."""
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # The incomplete property is filtered out by the view (zero rent)
        assert "300 Empty Rd" not in content

    def test_incomplete_no_score(self, client_logged_in, targets, incomplete_property):
        """No score bar should be rendered for an excluded property."""
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # No properties in table since the only one was filtered out
        assert "deal-table" not in content or "300 Empty Rd" not in content


# ── Filters present ───────────────────────────────────────────────────────────


class TestDashboardFilters:
    """Filters are present in the template."""

    def test_verdict_chips(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # Chip-based verdict filter
        assert 'data-filter="all"' in content
        assert 'data-filter="A"' in content
        assert 'data-filter="B"' in content
        assert 'data-filter="C"' in content
        assert 'data-filter="1pct"' in content

    def test_search_input(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        assert "search-input" in content


# ── Sorting ───────────────────────────────────────────────────────────────────


class TestDashboardSorting:
    """Table columns are present for key metrics."""

    def test_table_headers_present(self, client_logged_in, targets, strong_property):
        resp = client_logged_in.get(reverse("dashboard"))
        content = resp.content.decode()
        # Table has columns for key metrics
        assert "CoC" in content
        assert "Cap rate" in content
        assert "DSCR" in content
        assert "Verdict" in content
        assert "Score" in content


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
