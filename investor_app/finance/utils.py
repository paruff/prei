"""Core finance math for investment KPIs.

This module intentionally holds only the low-level primitives and the
Django-coupled analysis function. Specialized math lives in sibling modules:

- ``mortgage`` — monthly mortgage, carrying costs, break-even rent, paydown, appreciation, ROI components
- ``taxes`` — depreciation, after-tax cash flow / IRR, hold-period projections, sale proceeds
- ``scoring`` — 1% rule, GRM, price-to-rent and market normalization helpers
- ``strategies`` — flip, buy-and-hold, vacation rental, BRRRR
"""

from __future__ import annotations

from decimal import Decimal
import logging

import numpy as np
import numpy_financial as npf

from core.models import InvestmentAnalysis, Property

logger = logging.getLogger(__name__)


def to_decimal(value: Decimal | float | int) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def noi(
    monthly_income: Decimal,
    monthly_expenses: Decimal,
    capex_reserve: Decimal | None = None,
) -> Decimal:
    """Calculate annual Net Operating Income (NOI).

    NOI = (Monthly Income - Monthly Expenses - CapEx Reserve) x 12

    Args:
        monthly_income: Gross monthly income (rent + other income).
        monthly_expenses: Monthly operating expenses (excludes debt service).
        capex_reserve: Optional monthly CapEx reserve amount. If provided,
            this is subtracted from net monthly income before annualizing.

    Returns:
        Annual NOI as a Decimal.
    """
    income = to_decimal(monthly_income)
    expenses = to_decimal(monthly_expenses)
    capex = to_decimal(capex_reserve) if capex_reserve is not None else Decimal("0")
    return (income - expenses - capex) * Decimal(12)


def cap_rate(annual_noi: Decimal, purchase_price: Decimal) -> Decimal:
    """Calculate the Capitalization Rate (Cap Rate).

    Cap Rate = Annual NOI / Purchase Price

    Args:
        annual_noi: Annual Net Operating Income.
        purchase_price: Total purchase price of the property.

    Returns:
        Cap rate as a Decimal (e.g. 0.06 for 6%). Returns Decimal("0")
        when purchase_price is zero.
    """
    if to_decimal(purchase_price) == 0:
        return Decimal("0")
    return to_decimal(annual_noi) / to_decimal(purchase_price)


def cash_on_cash(annual_cash_flow: Decimal, total_cash_invested: Decimal) -> Decimal:
    """Calculate Cash-on-Cash (CoC) Return.

    CoC = Annual Cash Flow / Total Cash Invested

    Args:
        annual_cash_flow: Annual cash flow after debt service.
        total_cash_invested: Total cash invested by the investor (down
            payment + closing costs + any rehab).

    Returns:
        Cash-on-cash return as a Decimal (e.g. 0.12 for 12%). Returns
        Decimal("0") when total_cash_invested is zero.
    """
    if to_decimal(total_cash_invested) == 0:
        return Decimal("0")
    return to_decimal(annual_cash_flow) / to_decimal(total_cash_invested)


def dscr(annual_noi: Decimal, annual_debt_service: Decimal) -> Decimal:
    """Calculate the Debt Service Coverage Ratio (DSCR).

    DSCR = Annual NOI / Annual Debt Service

    Args:
        annual_noi: Annual Net Operating Income.
        annual_debt_service: Total annual mortgage payments (P&I).

    Returns:
        DSCR as a Decimal (e.g. 1.25 means NOI covers debt service
        1.25x). Returns Decimal("0") when annual_debt_service is zero.
    """
    if to_decimal(annual_debt_service) == 0:
        return Decimal("0")
    return to_decimal(annual_noi) / to_decimal(annual_debt_service)


def irr(cashflows: list[Decimal]) -> Decimal:
    """Calculate the Internal Rate of Return (IRR) for a cashflow series.

    IRR is the discount rate r solving NPV(r) = 0.

    Args:
        cashflows: Cashflow series; cashflows[0] is the initial outflow
            (negative), subsequent entries are periodic net cashflows,
            typically ending with a period that includes sale proceeds.

    Returns:
        IRR as a Decimal (e.g. 0.15 for 15%). Returns Decimal("0") if
        the solver fails to converge or returns a non-finite value.
    """
    cf = np.array([float(c) for c in cashflows], dtype=float)
    try:
        value = float(npf.irr(cf))
        if np.isnan(value) or np.isinf(value):
            logger.warning(
                "irr: numpy_financial.irr returned non-finite value; returning 0"
            )
            return Decimal("0")
        return to_decimal(value)
    except Exception:
        logger.warning("irr: numpy_financial.irr raised; returning 0", exc_info=True)
        return Decimal("0")


def build_cashflows(
    purchase_price: Decimal,
    monthly_noi: Decimal,
    hold_years: int,
    exit_cap_rate: Decimal,
) -> list[Decimal]:
    if hold_years < 1:
        raise ValueError("hold_years must be at least 1")

    if exit_cap_rate <= Decimal("0"):
        raise ValueError("exit_cap_rate must be greater than 0")

    annual_noi = to_decimal(monthly_noi) * Decimal("12")
    exit_value = annual_noi / to_decimal(exit_cap_rate)
    total_months = hold_years * 12

    return (
        [to_decimal(purchase_price) * Decimal("-1")]
        + [to_decimal(monthly_noi)] * (total_months - 1)
        + [to_decimal(monthly_noi) + exit_value]
    )


def compute_analysis_for_property(prop: Property) -> InvestmentAnalysis:
    """Compute and persist the full investment analysis for a property."""
    from core.services.capex import calculate_capex_reserve_for_property

    incomes = prop.rental_incomes.all()
    expenses = prop.operating_expenses.all()

    monthly_income = sum((ri.effective_gross_income() for ri in incomes), Decimal(0))
    monthly_expense = sum((oe.monthly_amount() for oe in expenses), Decimal(0))

    # Include CapEx reserve in NOI calculation
    capex_reserve = calculate_capex_reserve_for_property(prop)
    annual_noi = noi(monthly_income, monthly_expense, capex_reserve)

    # Placeholder values for total cash invested and debt service; refine as data model expands
    total_cash_invested = to_decimal(prop.purchase_price)
    annual_cash_flow = annual_noi  # assumes no debt service for MVP
    annual_debt_service = Decimal("0")

    analysis, _ = InvestmentAnalysis.objects.get_or_create(property=prop)
    hold_years = analysis.hold_years
    exit_cap_rate = analysis.exit_cap_rate

    analysis.noi = annual_noi.quantize(Decimal("0.01"))
    analysis.cap_rate = cap_rate(annual_noi, to_decimal(prop.purchase_price)).quantize(
        Decimal("0.0001")
    )
    analysis.cash_on_cash = cash_on_cash(
        annual_cash_flow, total_cash_invested
    ).quantize(Decimal("0.0001"))
    analysis.dscr = dscr(annual_noi, annual_debt_service).quantize(Decimal("0.0001"))

    monthly_noi = annual_noi / Decimal(12)
    cashflows = build_cashflows(
        purchase_price=to_decimal(prop.purchase_price),
        monthly_noi=monthly_noi,
        hold_years=hold_years,
        exit_cap_rate=to_decimal(exit_cap_rate),
    )
    monthly_irr = irr(cashflows)
    # build_cashflows produces monthly cash flows, so irr() returns a monthly
    # rate.  Annualise it so the stored value matches real-estate conventions.
    if monthly_irr > 0:
        annual_irr = ((1 + monthly_irr) ** 12) - 1
    else:
        annual_irr = monthly_irr
    analysis.irr = annual_irr.quantize(Decimal("0.0001"))
    analysis.save()
    return analysis


def calculate_whatif_monthly_cashflow(
    annual_noi: Decimal,
    taxes: Decimal = Decimal("0"),
    insurance: Decimal = Decimal("0"),
    maintenance: Decimal = Decimal("0"),
    management_fees: Decimal = Decimal("0"),
    rehab_estimate: Decimal = Decimal("0"),
) -> Decimal:
    """Calculate projected monthly cash flow from NOI with what-if adjustments.

    Converts annual NOI to a monthly figure and subtracts additional
    user-specified monthly cost inputs and an annualised rehab reserve.

    Args:
        annual_noi: Annual net operating income (Decimal).
        taxes: Additional monthly property tax overrides.
        insurance: Additional monthly insurance cost.
        maintenance: Additional monthly maintenance cost.
        management_fees: Additional monthly management fee.
        rehab_estimate: One-time rehab estimate spread over 12 months.

    Returns:
        Projected monthly cash flow as Decimal.
    """
    monthly_income = to_decimal(annual_noi) / Decimal(12)
    additional_monthly = (
        to_decimal(taxes)
        + to_decimal(insurance)
        + to_decimal(maintenance)
        + to_decimal(management_fees)
    )
    rehab_monthly = (
        to_decimal(rehab_estimate) / Decimal(12) if rehab_estimate else Decimal("0")
    )
    return monthly_income - additional_monthly - rehab_monthly
