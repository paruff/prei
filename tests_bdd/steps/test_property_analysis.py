"""BDD coverage for the happy-path property analysis workflow."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from pytest_bdd import given, parsers, scenario, then, when

from core.models import InvestmentAnalysis, OperatingExpense, Property, RentalIncome
from investor_app.finance.utils import (
    cap_rate,
    cash_on_cash,
    dscr,
    estimate_insurance,
    irr,
    noi,
)

REL_TOLERANCE = 0.03


def _parse_currency(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


def _finance_default_decimal(key: str) -> Decimal:
    try:
        return Decimal(str(settings.FINANCE_DEFAULTS[key]))
    except KeyError as exc:
        raise ValueError(f"Missing FINANCE_DEFAULTS['{key}'] for BDD scenario") from exc
    except Exception as exc:
        raise ValueError(
            f"Invalid FINANCE_DEFAULTS['{key}'] value for BDD scenario"
        ) from exc


@scenario(
    "../features/property_analysis.feature",
    "Investor adds a property and views KPIs",
)
@pytest.mark.django_db
def test_investor_workflow() -> None:
    """Run the happy-path investor workflow scenario."""


@given("I am logged in as an investor", target_fixture="logged_in_user")
def logged_in_user(db, client) -> AbstractUser:
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
def add_property(
    logged_in_user: AbstractUser, address: str, purchase_price: str
) -> Property:
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
    management_fee_rate = _finance_default_decimal("management_fee_rate")
    monthly_rent = sum(
        (
            Decimal(str(income.monthly_rent))
            for income in property_record.rental_incomes.all()
        ),
        Decimal("0"),
    )
    monthly_income = sum(
        (
            income.effective_gross_income()
            for income in property_record.rental_incomes.all()
        ),
        Decimal("0"),
    )
    monthly_expenses = sum(
        (
            expense.monthly_amount()
            for expense in property_record.operating_expenses.all()
        ),
        Decimal("0"),
    )
    monthly_expenses += estimate_insurance(
        property_record.purchase_price,
        year_built=timezone.now().year,
    ) / Decimal("12")
    monthly_expenses += monthly_rent * management_fee_rate
    annual_noi = noi(monthly_income, monthly_expenses)
    annual_debt_service = Decimal("0")
    monthly_cashflow = annual_noi / Decimal("12")

    analysis, _ = InvestmentAnalysis.objects.update_or_create(
        property=property_record,
        defaults={
            "noi": annual_noi.quantize(Decimal("0.01")),
            "cap_rate": cap_rate(
                annual_noi, Decimal(str(property_record.purchase_price))
            ).quantize(Decimal("0.0001")),
            "cash_on_cash": cash_on_cash(
                annual_noi, Decimal(str(property_record.purchase_price))
            ).quantize(Decimal("0.0001")),
            "irr": irr(
                [Decimal(str(property_record.purchase_price)) * Decimal("-1")]
                + [monthly_cashflow] * 12
            ).quantize(Decimal("0.0001")),
            "dscr": dscr(annual_noi, annual_debt_service).quantize(Decimal("0.0001")),
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
