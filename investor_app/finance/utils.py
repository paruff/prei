from decimal import Decimal
from typing import Iterable, Dict, Any

import numpy as np
import numpy_financial as npf

# removed unused 'settings' import

from core.models import Property, InvestmentAnalysis, Listing


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


def score_listing_v1(listing: Listing) -> Decimal:
    """Basic Phase 1 scoring using price per sq ft and freshness.

    Higher score is better. This is a simple heuristic for MVP.
    """
    price = to_decimal(listing.price) if listing.price is not None else Decimal("0")
    sq_ft = Decimal(listing.sq_ft or 0)
    # price per square foot (lower is better)
    ppsf = (price / sq_ft) if sq_ft > 0 else Decimal("0")
    # freshness boost: recent postings get a bump
    from django.utils import timezone

    now = timezone.now()
    age_hours = Decimal(max(1, (now - listing.posted_at).total_seconds() / 3600))
    freshness = Decimal(1) / age_hours

    # Combine with weights
    # To avoid division by zero or extreme values, clamp ppsf
    ppsf_clamped = ppsf if ppsf > 0 else Decimal("1000000")
    score = (Decimal(1000000) / ppsf_clamped) + (freshness * Decimal(10))
    return score


def calculate_monthly_mortgage(
    loan_amount: Decimal, interest_rate: Decimal, loan_term_years: int
) -> Decimal:
    """Calculate monthly mortgage payment (principal and interest).

    Args:
        loan_amount: Total loan amount
        interest_rate: Annual interest rate as percentage (e.g., 7.5 for 7.5%)
        loan_term_years: Loan term in years

    Returns:
        Monthly payment amount
    """
    loan_amt = to_decimal(loan_amount)
    rate = to_decimal(interest_rate)

    if loan_amt == 0:
        return Decimal("0")

    if rate == 0:
        # No interest - simple division
        return loan_amt / Decimal(loan_term_years * 12)

    monthly_rate = rate / Decimal(100) / Decimal(12)
    num_payments = Decimal(loan_term_years * 12)

    # Standard amortization formula: M = P[r(1+r)^n]/[(1+r)^n-1]
    factor = (Decimal(1) + monthly_rate) ** num_payments
    monthly_payment = loan_amt * (monthly_rate * factor) / (factor - Decimal(1))

    return monthly_payment.quantize(Decimal("0.01"))


def calculate_property_tax(
    property_value: Decimal, tax_rate_percent: Decimal
) -> Decimal:
    """Calculate annual property tax.

    Args:
        property_value: Property value/assessed value
        tax_rate_percent: Property tax rate as percentage (e.g., 2.1 for 2.1%)

    Returns:
        Annual property tax amount
    """
    return (
        to_decimal(property_value) * to_decimal(tax_rate_percent) / Decimal(100)
    ).quantize(Decimal("0.01"))


def estimate_insurance(
    property_value: Decimal,
    property_type: str = "single-family",
    year_built: int = 2000,
) -> Decimal:
    """Estimate annual insurance cost.

    Args:
        property_value: Property value
        property_type: Type of property (single-family, condo, multi-family)
        year_built: Year property was built

    Returns:
        Estimated annual insurance premium
    """
    base_rate = Decimal("1200")  # National average for $250k home

    # Adjust for property value
    value_factor = to_decimal(property_value) / Decimal("250000")

    # Adjust for property type
    type_factors = {
        "single-family": Decimal("1.0"),
        "condo": Decimal("0.7"),
        "multi-family": Decimal("1.3"),
        "commercial": Decimal("1.5"),
    }
    type_factor = type_factors.get(property_type, Decimal("1.0"))

    # Adjust for age
    from datetime import datetime

    current_year = datetime.now().year
    age = max(0, current_year - year_built)
    age_factor = Decimal("1.0") + (Decimal(age) / Decimal(50))

    annual_insurance = base_rate * value_factor * type_factor * age_factor
    return annual_insurance.quantize(Decimal("0.01"))


def calculate_maintenance_reserve(
    property_value: Decimal,
    year_built: int = 2000,
    annual_percent: Decimal = Decimal("1.0"),
) -> Decimal:
    """Calculate annual maintenance reserve (1% rule with age adjustment).

    Args:
        property_value: Property value
        year_built: Year property was built
        annual_percent: Base annual percentage of property value (default 1%)

    Returns:
        Annual maintenance reserve amount
    """
    base_maintenance = (
        to_decimal(property_value) * to_decimal(annual_percent) / Decimal(100)
    )

    # Adjust for age
    if year_built < 1980:
        age_factor = Decimal("1.5")
    elif year_built < 2000:
        age_factor = Decimal("1.2")
    else:
        age_factor = Decimal("1.0")

    return (base_maintenance * age_factor).quantize(Decimal("0.01"))


def calculate_break_even_rent(
    monthly_carrying_costs: Decimal,
    vacancy_rate_percent: Decimal,
    property_management_percent: Decimal = Decimal("10"),
) -> Dict[str, Decimal]:
    """Calculate break-even rent needed to cover carrying costs.

    Args:
        monthly_carrying_costs: Total monthly carrying costs (excluding property management)
        vacancy_rate_percent: Vacancy rate as percentage (e.g., 8 for 8%)
        property_management_percent: Property management fee as percentage of rent

    Returns:
        Dictionary with breakEvenRent and related metrics
    """
    costs = to_decimal(monthly_carrying_costs)
    vacancy = to_decimal(vacancy_rate_percent) / Decimal(100)
    mgmt = to_decimal(property_management_percent) / Decimal(100)

    # Formula: rent * (1 - vacancy) * (1 - mgmt) = costs
    # rent = costs / ((1 - vacancy) * (1 - mgmt))
    break_even = costs / ((Decimal(1) - vacancy) * (Decimal(1) - mgmt))

    return {
        "monthly": break_even.quantize(Decimal("0.01")),
        "annual": (break_even * Decimal(12)).quantize(Decimal("0.01")),
    }


def calculate_carrying_costs(
    purchase_price: Decimal,
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    property_tax_rate: Decimal,
    insurance_annual: Decimal | None = None,
    hoa_monthly: Decimal = Decimal("0"),
    utilities_monthly: Decimal = Decimal("0"),
    maintenance_annual_percent: Decimal = Decimal("1.0"),
    property_type: str = "single-family",
    year_built: int = 2000,
) -> Dict[str, Any]:
    """Calculate complete carrying costs breakdown.

    Args:
        purchase_price: Property purchase price
        loan_amount: Mortgage loan amount
        interest_rate: Annual interest rate as percentage
        loan_term_years: Loan term in years
        property_tax_rate: Property tax rate as percentage
        insurance_annual: Annual insurance cost (if None, will estimate)
        hoa_monthly: Monthly HOA fees
        utilities_monthly: Monthly utility costs
        maintenance_annual_percent: Maintenance as percentage of property value
        property_type: Type of property
        year_built: Year property was built

    Returns:
        Dictionary with detailed carrying cost breakdown
    """
    # Calculate mortgage
    monthly_mortgage = calculate_monthly_mortgage(
        loan_amount, interest_rate, loan_term_years
    )

    # Calculate property tax
    annual_property_tax = calculate_property_tax(purchase_price, property_tax_rate)
    monthly_property_tax = annual_property_tax / Decimal(12)

    # Calculate or use provided insurance
    if insurance_annual is None:
        annual_insurance = estimate_insurance(purchase_price, property_type, year_built)
    else:
        annual_insurance = to_decimal(insurance_annual)
    monthly_insurance = annual_insurance / Decimal(12)

    # Calculate maintenance
    annual_maintenance = calculate_maintenance_reserve(
        purchase_price, year_built, maintenance_annual_percent
    )
    monthly_maintenance = annual_maintenance / Decimal(12)

    # Monthly costs
    monthly_hoa = to_decimal(hoa_monthly)
    monthly_utilities = to_decimal(utilities_monthly)

    # Calculate totals
    monthly_total = (
        monthly_mortgage
        + monthly_property_tax
        + monthly_insurance
        + monthly_hoa
        + monthly_utilities
        + monthly_maintenance
    )

    annual_total = monthly_total * Decimal(12)

    return {
        "monthly": {
            "mortgage": monthly_mortgage.quantize(Decimal("0.01")),
            "propertyTax": monthly_property_tax.quantize(Decimal("0.01")),
            "insurance": monthly_insurance.quantize(Decimal("0.01")),
            "hoa": monthly_hoa.quantize(Decimal("0.01")),
            "utilities": monthly_utilities.quantize(Decimal("0.01")),
            "maintenance": monthly_maintenance.quantize(Decimal("0.01")),
            "total": monthly_total.quantize(Decimal("0.01")),
        },
        "annual": {
            "mortgage": (monthly_mortgage * Decimal(12)).quantize(Decimal("0.01")),
            "propertyTax": annual_property_tax.quantize(Decimal("0.01")),
            "insurance": annual_insurance.quantize(Decimal("0.01")),
            "hoa": (monthly_hoa * Decimal(12)).quantize(Decimal("0.01")),
            "utilities": (monthly_utilities * Decimal(12)).quantize(Decimal("0.01")),
            "maintenance": annual_maintenance.quantize(Decimal("0.01")),
            "total": annual_total.quantize(Decimal("0.01")),
        },
    }


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
