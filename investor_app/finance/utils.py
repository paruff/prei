from decimal import Decimal
from typing import Iterable

import numpy as np
import numpy_financial as npf

# removed unused 'settings' import

from core.models import Property, InvestmentAnalysis


def to_decimal(value: Decimal | float | int) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def noi(monthly_income: Decimal, monthly_expenses: Decimal) -> Decimal:
    return to_decimal(monthly_income) * Decimal(12) - to_decimal(
        monthly_expenses
    ) * Decimal(12)


def cap_rate(annual_noi: Decimal, purchase_price: Decimal) -> Decimal:
    if to_decimal(purchase_price) == 0:
        return Decimal("0")
    return to_decimal(annual_noi) / to_decimal(purchase_price)


def cash_on_cash(annual_cash_flow: Decimal, total_cash_invested: Decimal) -> Decimal:
    if to_decimal(total_cash_invested) == 0:
        return Decimal("0")
    return to_decimal(annual_cash_flow) / to_decimal(total_cash_invested)


def dscr(annual_noi: Decimal, annual_debt_service: Decimal) -> Decimal:
    if to_decimal(annual_debt_service) == 0:
        return Decimal("0")
    return to_decimal(annual_noi) / to_decimal(annual_debt_service)


def irr(cashflows: Iterable[Decimal]) -> Decimal:
    cf = np.array([float(c) for c in cashflows], dtype=float)
    try:
        return to_decimal(npf.irr(cf))
    except Exception:
        return Decimal("0")


def compute_analysis_for_property(prop: Property) -> InvestmentAnalysis:
    incomes = prop.rental_incomes.all()
    expenses = prop.operating_expenses.all()

    monthly_income = sum((ri.effective_gross_income() for ri in incomes), Decimal(0))
    monthly_expense = sum((oe.monthly_amount() for oe in expenses), Decimal(0))
    annual_noi = noi(monthly_income, monthly_expense)

    # Placeholder values for total cash invested and debt service; refine as data model expands
    total_cash_invested = to_decimal(prop.purchase_price)
    annual_cash_flow = annual_noi  # assumes no debt service for MVP
    annual_debt_service = Decimal("0")

    analysis, _ = InvestmentAnalysis.objects.get_or_create(property=prop)
    analysis.noi = annual_noi.quantize(Decimal("0.01"))
    analysis.cap_rate = cap_rate(annual_noi, to_decimal(prop.purchase_price)).quantize(
        Decimal("0.0001")
    )
    analysis.cash_on_cash = cash_on_cash(
        annual_cash_flow, total_cash_invested
    ).quantize(Decimal("0.0001"))
    analysis.dscr = dscr(annual_noi, annual_debt_service).quantize(Decimal("0.0001"))

    # Simple IRR: initial outlay negative, then 12 months of NOI as inflows for one year horizon
    cashflows = [to_decimal(prop.purchase_price) * Decimal(-1)] + [
        annual_noi / Decimal(12)
    ] * 12
    analysis.irr = irr(cashflows).quantize(Decimal("0.0001"))
    analysis.save()
    return analysis
