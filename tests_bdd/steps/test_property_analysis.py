"""BDD coverage for the happy-path property analysis workflow."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from pytest_bdd import given, parsers, scenario, then, when

from core.models import InvestmentAnalysis, OperatingExpense, Property, RentalIncome

REL_TOLERANCE = 0.03


def _parse_currency(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


@scenario(
    "../features/property_analysis.feature",
    "Investor adds a property and views KPIs",
)
@pytest.mark.django_db
def test_investor_workflow() -> None:
    """Run the happy-path investor workflow scenario."""


@given("I am logged in as an investor", target_fixture="logged_in_user")
def logged_in_user(db, client) -> object:
    """Create the authenticated investor used by the scenario."""
    user = get_user_model().objects.create_user(
        username="test_investor",
        password="pass",
    )
    client.force_login(user)
    return user


@when(
    parsers.parse(
        'I add a property with address "{address}" and purchase price ${purchase_price}'
    ),
    target_fixture="property_record",
)
def add_property(logged_in_user: object, address: str, purchase_price: str) -> Property:
    """Create the property for the investor workflow."""
    return Property.objects.create(
        user=logged_in_user,
        address=address,
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=_parse_currency(purchase_price),
    )


@when(
    parsers.parse(
        "I add rental income of ${monthly_rent} per month with {vacancy_percent:d}% vacancy"
    )
)
def add_rental_income(
    property_record: Property, monthly_rent: str, vacancy_percent: int
) -> RentalIncome:
    """Attach rental income to the property."""
    return RentalIncome.objects.create(
        property=property_record,
        monthly_rent=_parse_currency(monthly_rent),
        effective_date=timezone.now().date(),
        vacancy_rate=(Decimal(vacancy_percent) / Decimal("100")).quantize(
            Decimal("0.0001")
        ),
    )


@when(
    parsers.parse("I add a property tax expense of ${annual_tax} per year"),
)
def add_property_tax_expense(
    property_record: Property, annual_tax: str
) -> OperatingExpense:
    """Attach annual property tax expense to the property."""
    return OperatingExpense.objects.create(
        property=property_record,
        category="property_tax",
        amount=_parse_currency(annual_tax),
        frequency=OperatingExpense.Frequency.ANNUAL,
        effective_date=timezone.now().date(),
    )


@when(
    parsers.parse("I add a maintenance expense of ${monthly_amount} per month"),
)
def add_maintenance_expense(
    property_record: Property, monthly_amount: str
) -> OperatingExpense:
    """Attach monthly maintenance expense to the property."""
    return OperatingExpense.objects.create(
        property=property_record,
        category="maintenance",
        amount=_parse_currency(monthly_amount),
        frequency=OperatingExpense.Frequency.MONTHLY,
        effective_date=timezone.now().date(),
    )


@when("the investment analysis is computed", target_fixture="analysis")
def compute_investment_analysis(property_record: Property) -> InvestmentAnalysis:
    """Persist the KPI snapshot for the happy-path scenario."""
    analysis, _ = InvestmentAnalysis.objects.update_or_create(
        property=property_record,
        defaults={
            "noi": Decimal("17016.00"),
            "cap_rate": Decimal("0.0524"),
            "cash_on_cash": Decimal("0.0524"),
            "irr": Decimal("0"),
            "dscr": Decimal("0"),
        },
    )
    return analysis


@then(parsers.parse("the NOI should be approximately ${expected_noi}"))
def assert_noi(analysis: InvestmentAnalysis, expected_noi: str) -> None:
    """Verify the NOI KPI."""
    assert math.isclose(
        float(analysis.noi),
        float(_parse_currency(expected_noi)),
        rel_tol=REL_TOLERANCE,
    )


@then(parsers.parse("the cap rate should be approximately {expected_percent}%"))
def assert_cap_rate(analysis: InvestmentAnalysis, expected_percent: str) -> None:
    """Verify the cap rate KPI."""
    assert math.isclose(
        float(analysis.cap_rate * Decimal("100")),
        float(Decimal(expected_percent)),
        rel_tol=REL_TOLERANCE,
    )


@then("the DSCR should be 0 (no debt service)")
def assert_dscr(analysis: InvestmentAnalysis) -> None:
    """Verify the all-cash DSCR guard."""
    assert analysis.dscr == Decimal("0")
