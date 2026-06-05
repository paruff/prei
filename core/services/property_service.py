from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from core.models import InvestmentAnalysis, OperatingExpense, Property, RentalIncome
from investor_app.finance.utils import (
    cap_rate,
    cash_on_cash,
    dscr,
    irr,
    build_cashflows,
    noi,
    to_decimal,
)

logger = logging.getLogger(__name__)


def compute_noi(property: Property) -> Decimal:
    """Compute and persist Net Operating Income for a single property.

    Aggregates all rental incomes and operating expenses for the property,
    computes annual NOI, and updates the associated ``InvestmentAnalysis``
    record with NOI and derived KPIs (cap rate, cash-on-cash, DSCR, IRR).

    Args:
        property: The Property instance to analyse.

    Returns:
        The computed annual NOI as a ``Decimal``, quantized to two decimal places.

    Raises:
        ValueError: If the property has no rental incomes or operating expenses.
    """
    incomes = property.rental_incomes.all()
    expenses = property.operating_expenses.all()

    monthly_gross = sum((ri.effective_gross_income() for ri in incomes), Decimal("0"))
    monthly_exp = sum((oe.monthly_amount() for oe in expenses), Decimal("0"))

    if monthly_gross == Decimal("0") and monthly_exp == Decimal("0"):
        raise ValueError(
            f"Property {property.id} has no rental incomes or operating expenses; "
            "cannot compute NOI."
        )

    annual_noi = noi(monthly_gross, monthly_exp)

    _persist_analysis(property, annual_noi, monthly_noi=annual_noi / Decimal("12"))

    return annual_noi.quantize(Decimal("0.01"))


@transaction.atomic
def _persist_analysis(
    property: Property, annual_noi: Decimal, monthly_noi: Decimal
) -> InvestmentAnalysis:
    analysis, _ = InvestmentAnalysis.objects.get_or_create(property=property)

    purchase_price = to_decimal(property.purchase_price)
    annual_debt_service = Decimal("0")
    annual_cash_flow = annual_noi

    cashflows = build_cashflows(
        purchase_price=purchase_price,
        monthly_noi=monthly_noi,
        hold_years=to_decimal(analysis.hold_years),
        exit_cap_rate=to_decimal(analysis.exit_cap_rate),
    )

    analysis.noi = annual_noi.quantize(Decimal("0.01"))
    analysis.cap_rate = cap_rate(annual_noi, purchase_price).quantize(
        Decimal("0.0001")
    )
    analysis.cash_on_cash = cash_on_cash(
        annual_cash_flow, purchase_price
    ).quantize(Decimal("0.0001"))
    analysis.dscr = dscr(annual_noi, annual_debt_service).quantize(Decimal("0.0001"))
    analysis.irr = irr(cashflows).quantize(Decimal("0.0001"))
    analysis.save()

    return analysis


def compute_noi_for_user(user) -> dict[str, Decimal]:
    """Compute aggregate NOI across all of a user's properties.

    Args:
        user: Django User instance.

    Returns:
        Dict with ``total_annual_noi``, ``property_count``, and
        ``average_noi`` (all ``Decimal``).
    """
    properties = Property.objects.filter(user=user)
    total = Decimal("0")
    count = 0

    for prop in properties:
        try:
            annual = compute_noi(prop)
            total += annual
            count += 1
        except ValueError:
            logger.warning("Skipping property %s — insufficient data for NOI", prop.id)

    average = total / Decimal(count) if count else Decimal("0")

    return {
        "total_annual_noi": total.quantize(Decimal("0.01")),
        "property_count": Decimal(count),
        "average_noi": average.quantize(Decimal("0.01")),
    }


def compute_noi_from_amounts(
    monthly_income: Decimal, monthly_expenses: Decimal
) -> Decimal:
    """Calculate annual NOI directly from monthly income and expense amounts.

    This is a pure calculation wrapper that does not touch the database,
    useful for scenario/what-if analysis.

    Args:
        monthly_income: Total monthly gross income (after vacancy).
        monthly_expenses: Total monthly operating expenses.

    Returns:
        Annual NOI as a ``Decimal``, quantized to two decimal places.
    """
    return noi(monthly_income, monthly_expenses).quantize(Decimal("0.01"))


def calculate_noi(
    gross_income: Decimal,
    operating_expenses: Decimal,
) -> Decimal:
    """Calculate annual Net Operating Income (NOI).

    NOI = Gross Income - Operating Expenses

    This is a pure service-layer function that delegates to the finance
    utility layer. It does not touch the database.

    Args:
        gross_income: Total annual gross income from the property.
        operating_expenses: Total annual operating expenses (excluding debt service).

    Returns:
        Annual NOI as a ``Decimal``, quantized to two decimal places.
    """
    return (to_decimal(gross_income) - to_decimal(operating_expenses)).quantize(
        Decimal("0.01")
    )
