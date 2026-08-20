"""Playwright browser E2E fixtures.

These tests talk to the app through a real headless Chromium browser
against pytest-django's live_server. Seeded data is created in the test
DB (transactionally) and reached over HTTP via live_server.url.
The page fixture holds absolute URLs off live_server; tests may also use
page.goto("/relative/path/") because the page context's base_url is set.
"""

from __future__ import annotations

import os
from typing import Iterator

# Playwright sync API starts an asyncio event loop internally; Django 6
# blocks sync DB operations when it detects one.  This env-var disables
# that guard for the e2e test process only — acceptable because
# Playwright drives the browser in its own thread and all DB writes
# happen on the pytest main thread.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

E2E_USERNAME = "e2e_user"
E2E_PASSWORD = "e2e-password-123"  # noqa: S105 — test fixture, not a real secret


@pytest.fixture()
def browser() -> Iterator[Browser]:
    """Headless Chromium launched per test (function scope avoids finalizer conflicts with reruns)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def page(browser: Browser, live_server) -> Iterator[Page]:
    """A fresh browser context bound to pytest-django's live_server."""
    context = browser.new_context(base_url=live_server.url)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture()
def e2e_user(db):  # type: ignore[no-untyped-def]
    """Create the e2e test user."""
    return User.objects.create_user(
        username=E2E_USERNAME,
        email="e2e@example.com",
        password=E2E_PASSWORD,
    )


@pytest.fixture()
def e2e_login(page: Page, e2e_user):  # type: ignore[no-untyped-def]
    """Log the browser in through the real login form (accounts/login/)."""
    page.goto("/accounts/login/")
    page.fill('input[name="username"]', E2E_USERNAME)
    page.fill('input[name="password"]', E2E_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard/")
    return e2e_user


@pytest.fixture()
def growth_area(db) -> object:  # type: ignore[no-untyped-def]
    from core.models import GrowthArea

    return GrowthArea.objects.create(
        state="TX",
        city_name="Austin",
        metro_area="Austin-Round Rock",
        population_growth_rate=Decimal("0.0214"),
        employment_growth_rate=Decimal("0.0341"),
        median_income_growth=Decimal("0.0187"),
        housing_demand_index=82,
        supply_constraint_index=45,
        data_timestamp=timezone.now(),
        population=978908,
        composite_score=Decimal("75.50"),
        landlord_score=8,
    )


@pytest.fixture()
def discovery_sources(db, growth_area) -> list:  # type: ignore[no-untyped-def]
    """One record per source in Austin, TX so discovery never hits the network.

    The property_discovery view only triggers background scrapers when a
    source table has zero rows for the state; seeding rows short-circuits
    that branch and processes the seeded records synchronously.
    """
    from core.models import (
        CountyForeclosureNotice,
        HudProperty,
        UsdaProperty,
        VrmProperty,
    )

    now = timezone.now()
    vrm = VrmProperty.objects.create(
        vrm_property_id=90001,
        vrm_listing_url="https://www.vrmproperties.com/property/90001",
        address="100 Prime St",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        list_price=Decimal("200000.00"),
        projected_monthly_rent=Decimal("2000.00"),
        bedrooms=3,
        bathrooms=Decimal("2.0"),
        year_built=2001,
        status=VrmProperty.Status.FOR_SALE,
        scraped_at=now,
        last_seen_at=now,
    )
    hud = HudProperty.objects.create(
        hud_case_number="HUD-482-001",
        address="200 Value Ave",
        city="Austin",
        state="TX",
        zip_code="78702",
        county="Travis",
        asking_price=Decimal("85000.00"),
        list_price=Decimal("85000.00"),
        bedrooms=3,
        bathrooms=Decimal("2.0"),
        square_feet=1200,
        status=HudProperty.Status.ACTIVE,
        scraped_at=now,
        last_seen_at=now,
    )
    usda = UsdaProperty.objects.create(
        usda_case_number="USDA-77-001",
        address="300 Rural Ln",
        city="Austin",
        state="TX",
        zip_code="78703",
        county="Travis",
        list_price=Decimal("150000.00"),
        bedrooms=3,
        bathrooms=Decimal("2.0"),
        square_feet=1500,
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=now,
        last_seen_at=now,
    )
    notice = CountyForeclosureNotice.objects.create(
        case_number="TC-2026-0001",
        document_type=CountyForeclosureNotice.DocumentType.NTS,
        address="400 Auction Way",
        city="Austin",
        state="TX",
        zip_code="78704",
        county="Travis",
        filing_date=timezone.now().date(),
        scraped_at=now,
        last_seen_at=now,
    )
    return [vrm, hud, usda, notice]
