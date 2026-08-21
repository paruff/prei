from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

# Playwright sync API (used by tests/e2e/) starts an asyncio event loop;
# Django 6 blocks sync DB ops when it detects one. This is safe because
# Playwright drives the browser in its own thread and all DB writes happen
# on the pytest main thread.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import InvestmentAnalysis, OperatingExpense, Property, RentalIncome

User = get_user_model()

QUARANTINE_FILE = Path(__file__).parent / "tests" / ".flaky_quarantine.txt"


def pytest_configure(config) -> None:  # noqa: ARG001
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings_test")


@pytest.fixture(autouse=True)
def _clear_django_cache():
    """Django's cache (rate limiting, Rentometer/Walk Score/etc.) is process-
    global — without this, state from one test leaks into the next.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def pytest_collection_modifyitems(config, items) -> None:  # noqa: ARG001
    """Auto-assign test-layer markers and quarantine flaky tests.

    Markers are assigned by file path so that CI can filter via -m.
    Explicit pytestmark overrides these; files without an explicit
    marker default to ``integration`` (safe — always passes with DB).
    """
    # ── Quarantine flaky tests ──
    if QUARANTINE_FILE.exists():
        quarantined = {
            line.strip()
            for line in QUARANTINE_FILE.read_text().splitlines()
            if line.strip()
        }
        if quarantined:
            q_marker = pytest.mark.xfail(
                reason="quarantined: flaky, see docs/quality/flaky_tests.json",
                strict=False,
            )
            for item in items:
                if item.nodeid in quarantined:
                    item.add_marker(q_marker)

    # ── Auto-assign layer markers by file path ──
    _ACCEPTANCE_DIR = "tests/acceptance/"
    _SMOKE_FILES = {"test_container_startup.py", "test_docker_e2e.py"}
    _LIVE_FILES = {
        "test_live_sources.py",
        "test_integration_attom.py",
        "test_integration_fred.py",
    }
    _BDD_DIR = "tests_bdd/"
    _E2E_SUFFIX = "_e2e.py"

    for item in items:
        fpath = item.fspath.strpath

        # Already has an explicit marker — leave it alone
        already_marked = any(
            m.name in ("unit", "integration", "smoke", "acceptance", "e2e", "live")
            for m in item.iter_markers()
        )
        if already_marked:
            continue

        # Acceptance tests
        if _ACCEPTANCE_DIR in fpath:
            item.add_marker(pytest.mark.acceptance)
            continue

        # Smoke tests
        fname = item.fspath.purebasename
        if fname in _SMOKE_FILES:
            item.add_marker(pytest.mark.smoke)
            continue

        # Live API tests
        if fname in _LIVE_FILES:
            item.add_marker(pytest.mark.live)
            continue

        # BDD — e2e
        if _BDD_DIR in fpath:
            item.add_marker(pytest.mark.e2e)
            continue

        # Files ending in _e2e.py
        if fname.endswith("_e2e"):
            item.add_marker(pytest.mark.e2e)
            continue

        # Default: integration (DB-backed) — safest fallback for Django apps
        item.add_marker(pytest.mark.integration)


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="fixture_user",
        email="fixture_user@example.com",
        password="fixture-pass-123",
    )


@pytest.fixture
def second_user(db):
    return User.objects.create_user(
        username="fixture_user_2",
        email="fixture_user_2@example.com",
        password="fixture-pass-456",
    )


@pytest.fixture
def make_property(db):
    def _make_property(**overrides):
        data = {
            "user": overrides.pop("user", None),
            "address": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "purchase_price": Decimal("325000.00"),
            "units": 1,
            "sqft": 1650,
            "notes": "Fixture property",
        }
        data.update(overrides)
        if data["user"] is None:
            raise ValueError("make_property requires a user")
        return Property.objects.create(**data)

    return _make_property


@pytest.fixture
def make_rental_income(db):
    def _make_rental_income(**overrides):
        data = {
            "property": overrides.pop("property", None),
            "monthly_rent": Decimal("2400.00"),
            "effective_date": timezone.now().date(),
            "vacancy_rate": Decimal("0.0500"),
        }
        data.update(overrides)
        if data["property"] is None:
            raise ValueError("make_rental_income requires a property")
        return RentalIncome.objects.create(**data)

    return _make_rental_income


@pytest.fixture
def make_expense(db):
    def _make_expense(**overrides):
        data = {
            "property": overrides.pop("property", None),
            "category": "maintenance",
            "amount": Decimal("200.00"),
            "frequency": OperatingExpense.Frequency.MONTHLY,
            "effective_date": timezone.now().date(),
        }
        data.update(overrides)
        if data["property"] is None:
            raise ValueError("make_expense requires a property")
        return OperatingExpense.objects.create(**data)

    return _make_expense


@pytest.fixture
def property_sfr(user, make_property):
    return make_property(
        user=user,
        address="2209 East 6th St",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("325000.00"),
        monthly_rent_gross=Decimal("2400.00"),
        units=1,
        sqft=1725,
        notes="Austin SFR fixture",
    )


@pytest.fixture
def property_duplex(user, make_property):
    return make_property(
        user=user,
        address="5512 Manor Rd",
        city="Austin",
        state="TX",
        zip_code="78723",
        purchase_price=Decimal("410000.00"),
        units=2,
        sqft=2440,
        notes="Austin duplex fixture",
    )


@pytest.fixture
def property_auction(user, make_property):
    return make_property(
        user=user,
        address="9804 Drowsy Willow Trl",
        city="Austin",
        state="TX",
        zip_code="78748",
        purchase_price=Decimal("129900.00"),
        units=1,
        sqft=1380,
        notes="Distressed auction candidate",
    )


@pytest.fixture
def property_owned_by_second_user(second_user, make_property):
    return make_property(
        user=second_user,
        address="702 Lakeview Dr",
        city="Round Rock",
        state="TX",
        zip_code="78664",
        purchase_price=Decimal("295000.00"),
        units=1,
        sqft=1610,
        notes="Ownership isolation fixture",
    )


@pytest.fixture
def rental_income_sfr(property_sfr, make_rental_income):
    return make_rental_income(
        property=property_sfr,
        monthly_rent=Decimal("2400.00"),
        vacancy_rate=Decimal("0.0500"),
    )


@pytest.fixture
def rental_income_zero_vacancy(property_sfr, make_rental_income):
    return make_rental_income(
        property=property_sfr,
        monthly_rent=Decimal("2400.00"),
        vacancy_rate=Decimal("0.0000"),
    )


@pytest.fixture
def rental_income_high_vacancy(property_sfr, make_rental_income):
    return make_rental_income(
        property=property_sfr,
        monthly_rent=Decimal("2400.00"),
        vacancy_rate=Decimal("0.2500"),
    )


@pytest.fixture
def expense_property_tax_annual(property_sfr, make_expense):
    return make_expense(
        property=property_sfr,
        category="property_tax",
        amount=Decimal("3900.00"),
        frequency=OperatingExpense.Frequency.ANNUAL,
    )


@pytest.fixture
def expense_insurance_annual(property_sfr, make_expense):
    return make_expense(
        property=property_sfr,
        category="insurance",
        amount=Decimal("1400.00"),
        frequency=OperatingExpense.Frequency.ANNUAL,
    )


@pytest.fixture
def expense_maintenance_monthly(property_sfr, make_expense):
    return make_expense(
        property=property_sfr,
        category="maintenance",
        amount=Decimal("200.00"),
        frequency=OperatingExpense.Frequency.MONTHLY,
    )


@pytest.fixture
def expense_management_monthly(property_sfr, make_expense):
    return make_expense(
        property=property_sfr,
        category="management",
        amount=Decimal("192.00"),
        frequency=OperatingExpense.Frequency.MONTHLY,
    )


@pytest.fixture
def expense_capex_reserve_monthly(property_sfr, make_expense):
    return make_expense(
        property=property_sfr,
        category="capex_reserve",
        amount=Decimal("120.00"),
        frequency=OperatingExpense.Frequency.MONTHLY,
    )


@pytest.fixture
def analysis_sfr(property_sfr):
    return InvestmentAnalysis.objects.create(
        property=property_sfr,
        noi=Decimal("17016.00"),
        cap_rate=Decimal("0.0524"),
        cash_on_cash=Decimal("0.0850"),
        irr=Decimal("0.1130"),
        dscr=Decimal("1.2800"),
    )


@pytest.fixture
def analysis_with_financing(property_duplex):
    return InvestmentAnalysis.objects.create(
        property=property_duplex,
        noi=Decimal("7200.00"),
        cap_rate=Decimal("0.0176"),
        cash_on_cash=Decimal("-0.0310"),
        irr=Decimal("-0.0120"),
        dscr=Decimal("0.8700"),
    )


@pytest.fixture
def full_sfr(
    property_sfr,
    rental_income_sfr,
    expense_property_tax_annual,
    expense_insurance_annual,
    expense_maintenance_monthly,
    expense_management_monthly,
    expense_capex_reserve_monthly,
    analysis_sfr,
):
    return {
        "property": property_sfr,
        "rental_income": rental_income_sfr,
        "expenses": [
            expense_property_tax_annual,
            expense_insurance_annual,
            expense_maintenance_monthly,
            expense_management_monthly,
            expense_capex_reserve_monthly,
        ],
        "analysis": analysis_sfr,
    }


@pytest.fixture
def portfolio(
    property_sfr,
    property_duplex,
    property_auction,
    property_owned_by_second_user,
):
    return {
        "primary_user_properties": [property_sfr, property_duplex, property_auction],
        "other_user_property": property_owned_by_second_user,
    }
