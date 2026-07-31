"""Mortgage, carrying costs, break-even rent, and ROI component calculations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import logging
from typing import Any, Dict

from investor_app.finance.utils import to_decimal

logger = logging.getLogger(__name__)


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
    divisor = (Decimal(1) - vacancy) * (Decimal(1) - mgmt)
    if divisor == 0:
        return {
            "monthly": Decimal("0"),
            "annual": Decimal("0"),
        }
    break_even = costs / divisor

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


def calculate_principal_paydown(
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    num_years: int = 1,
) -> Decimal:
    """Calculate total principal paid down over specified number of years.

    Args:
        loan_amount: Initial loan amount
        interest_rate: Annual interest rate as percentage (e.g., 7.5 for 7.5%)
        loan_term_years: Total loan term in years
        num_years: Number of years to calculate paydown for (default 1)

    Returns:
        Total principal paid down over the specified period
    """
    if loan_amount == 0 or num_years == 0:
        return Decimal("0")

    loan_amt = to_decimal(loan_amount)
    rate = to_decimal(interest_rate)

    if rate == 0:
        # No interest - equal principal payments
        monthly_principal = loan_amt / Decimal(loan_term_years * 12)
        return monthly_principal * Decimal(num_years * 12)

    monthly_rate = rate / Decimal(100) / Decimal(12)
    monthly_payment = calculate_monthly_mortgage(
        loan_amount, interest_rate, loan_term_years
    )

    # Calculate principal paid by simulating each payment
    remaining_balance = loan_amt
    total_principal_paid = Decimal("0")

    for month in range(num_years * 12):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        total_principal_paid += principal_payment
        remaining_balance -= principal_payment

        if remaining_balance <= 0:
            break

    return total_principal_paid.quantize(Decimal("0.01"))


def calculate_appreciation(
    property_value: Decimal,
    appreciation_rate: Decimal,
    num_years: int = 1,
) -> Decimal:
    """Calculate property appreciation over specified number of years.

    Args:
        property_value: Current property value
        appreciation_rate: Annual appreciation rate as percentage (e.g., 3.0 for 3%)
        num_years: Number of years to project (default 1)

    Returns:
        Total appreciation amount
    """
    value = to_decimal(property_value)
    rate = to_decimal(appreciation_rate) / Decimal(100)

    future_value = value * ((Decimal(1) + rate) ** Decimal(num_years))
    appreciation = future_value - value

    return appreciation.quantize(Decimal("0.01"))


def calculate_roi_components(
    purchase_price: Decimal,
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    total_cash_invested: Decimal,
    annual_cash_flow: Decimal,
    appreciation_rate: Decimal = Decimal("3.0"),
    tax_bracket: Decimal = Decimal("24"),
    num_years: int = 5,
) -> Dict[str, Any]:
    """Calculate comprehensive ROI with all components over multiple years.

    Args:
        purchase_price: Property purchase price
        loan_amount: Mortgage loan amount
        interest_rate: Annual interest rate as percentage
        loan_term_years: Loan term in years
        total_cash_invested: Total cash invested (down payment + closing costs)
        annual_cash_flow: Annual pre-tax cash flow
        appreciation_rate: Annual appreciation rate as percentage (default 3%)
        tax_bracket: Marginal tax bracket as percentage (default 24%)
        num_years: Number of years to project (default 5)

    Returns:
        Dictionary with ROI components and projections
    """
    from investor_app.finance.taxes import calculate_tax_benefits

    # Year 1 calculations
    year1_cash_flow = to_decimal(annual_cash_flow)
    year1_principal_paydown = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, 1
    )
    year1_appreciation = calculate_appreciation(purchase_price, appreciation_rate, 1)
    year1_tax_benefits = calculate_tax_benefits(
        loan_amount, interest_rate, loan_term_years, purchase_price, tax_bracket, 1
    )

    year1_total_return = (
        year1_cash_flow
        + year1_principal_paydown
        + year1_appreciation
        + year1_tax_benefits
    )

    if total_cash_invested > 0:
        year1_roi = year1_total_return / to_decimal(total_cash_invested) * Decimal(100)
    else:
        year1_roi = Decimal("0")

    # Multi-year calculations
    total_cash_flow = year1_cash_flow * Decimal(
        num_years
    )  # Simplified: assumes constant
    total_principal_paydown = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, num_years
    )
    total_appreciation = calculate_appreciation(
        purchase_price, appreciation_rate, num_years
    )

    # Sum tax benefits for each year
    total_tax_benefits = Decimal("0")
    for year in range(1, num_years + 1):
        total_tax_benefits += calculate_tax_benefits(
            loan_amount,
            interest_rate,
            loan_term_years,
            purchase_price,
            tax_bracket,
            year,
        )

    total_return = (
        total_cash_flow
        + total_principal_paydown
        + total_appreciation
        + total_tax_benefits
    )

    if total_cash_invested > 0:
        multi_year_roi = total_return / to_decimal(total_cash_invested) * Decimal(100)
        # Annualized return
        annualized_roi = (
            (Decimal(1) + multi_year_roi / Decimal(100))
            ** (Decimal(1) / Decimal(num_years))
            - Decimal(1)
        ) * Decimal(100)
    else:
        multi_year_roi = Decimal("0")
        annualized_roi = Decimal("0")

    # Component percentages for year 1
    if year1_total_return > 0:
        cash_flow_pct = year1_cash_flow / year1_total_return * Decimal(100)
        appreciation_pct = year1_appreciation / year1_total_return * Decimal(100)
        equity_pct = year1_principal_paydown / year1_total_return * Decimal(100)
        tax_pct = year1_tax_benefits / year1_total_return * Decimal(100)
    else:
        cash_flow_pct = appreciation_pct = equity_pct = tax_pct = Decimal("0")

    return {
        "year1": {
            "roi": year1_roi.quantize(Decimal("0.1")),
            "totalReturn": year1_total_return.quantize(Decimal("0.01")),
            "cashFlow": year1_cash_flow.quantize(Decimal("0.01")),
            "principalPaydown": year1_principal_paydown.quantize(Decimal("0.01")),
            "appreciation": year1_appreciation.quantize(Decimal("0.01")),
            "taxBenefits": year1_tax_benefits.quantize(Decimal("0.01")),
        },
        f"year{num_years}Projected": {
            "roi": multi_year_roi.quantize(Decimal("0.1")),
            "annualizedRoi": annualized_roi.quantize(Decimal("0.1")),
            "totalReturn": total_return.quantize(Decimal("0.01")),
            "totalCashFlow": total_cash_flow.quantize(Decimal("0.01")),
            "totalPrincipalPaydown": total_principal_paydown.quantize(Decimal("0.01")),
            "totalAppreciation": total_appreciation.quantize(Decimal("0.01")),
            "totalTaxBenefits": total_tax_benefits.quantize(Decimal("0.01")),
        },
        "components": {
            "cashFlowReturn": cash_flow_pct.quantize(Decimal("0.1")),
            "appreciationReturn": appreciation_pct.quantize(Decimal("0.1")),
            "equityBuildupReturn": equity_pct.quantize(Decimal("0.1")),
            "taxBenefitsReturn": tax_pct.quantize(Decimal("0.1")),
        },
    }
