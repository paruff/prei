from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable

import numpy as np
import numpy_financial as npf

# removed unused 'settings' import

from core.models import InvestmentAnalysis, Listing, Property


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
    monthly_payment = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)

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


def calculate_tax_benefits(
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    property_value: Decimal,
    tax_bracket: Decimal = Decimal("24"),
    year_num: int = 1,
) -> Decimal:
    """Calculate tax benefits from mortgage interest deduction and depreciation.

    Args:
        loan_amount: Mortgage loan amount
        interest_rate: Annual interest rate as percentage
        loan_term_years: Loan term in years
        property_value: Property value (for depreciation calculation)
        tax_bracket: Marginal tax bracket as percentage (default 24%)
        year_num: Which year to calculate benefits for (default 1)

    Returns:
        Total tax benefit amount for the specified year
    """
    if loan_amount == 0:
        # All cash - only depreciation benefit
        # Residential property: 27.5 year straight-line depreciation on 80% of value
        building_value = to_decimal(property_value) * Decimal("0.80")
        annual_depreciation = building_value / Decimal("27.5")
        tax_savings = annual_depreciation * (to_decimal(tax_bracket) / Decimal(100))
        return tax_savings.quantize(Decimal("0.01"))

    # Calculate interest paid in specific year
    loan_amt = to_decimal(loan_amount)
    rate = to_decimal(interest_rate)
    monthly_rate = rate / Decimal(100) / Decimal(12)
    monthly_payment = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)

    # Calculate remaining balance at start of year
    payments_before = (year_num - 1) * 12
    if payments_before > 0:
        num_payments = loan_term_years * 12
        remaining_factor = (Decimal(1) + monthly_rate) ** Decimal(num_payments - payments_before)
        payment_factor = (Decimal(1) + monthly_rate) ** Decimal(num_payments)
        balance_start = loan_amt * (
            (remaining_factor - Decimal(1)) / (payment_factor - Decimal(1))
        )
    else:
        balance_start = loan_amt

    # Calculate interest for each month of the year
    total_interest = Decimal("0")
    balance = balance_start
    for _ in range(12):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        total_interest += interest_payment
        balance -= principal_payment
        if balance <= 0:
            break

    # Add depreciation
    building_value = to_decimal(property_value) * Decimal("0.80")
    annual_depreciation = building_value / Decimal("27.5")

    # Total deductions
    total_deductions = total_interest + annual_depreciation

    # Tax savings
    tax_savings = total_deductions * (to_decimal(tax_bracket) / Decimal(100))

    return tax_savings.quantize(Decimal("0.01"))


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
        year1_cash_flow + year1_principal_paydown + year1_appreciation + year1_tax_benefits
    )

    if total_cash_invested > 0:
        year1_roi = (year1_total_return / to_decimal(total_cash_invested) * Decimal(100))
    else:
        year1_roi = Decimal("0")

    # Multi-year calculations
    total_cash_flow = year1_cash_flow * Decimal(num_years)  # Simplified: assumes constant
    total_principal_paydown = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, num_years
    )
    total_appreciation = calculate_appreciation(purchase_price, appreciation_rate, num_years)
    
    # Sum tax benefits for each year
    total_tax_benefits = Decimal("0")
    for year in range(1, num_years + 1):
        total_tax_benefits += calculate_tax_benefits(
            loan_amount, interest_rate, loan_term_years, purchase_price, tax_bracket, year
        )

    total_return = (
        total_cash_flow + total_principal_paydown + total_appreciation + total_tax_benefits
    )

    if total_cash_invested > 0:
        multi_year_roi = (total_return / to_decimal(total_cash_invested) * Decimal(100))
        # Annualized return
        annualized_roi = (
            ((Decimal(1) + multi_year_roi / Decimal(100)) ** (Decimal(1) / Decimal(num_years)) - Decimal(1))
            * Decimal(100)
        )
    else:
        multi_year_roi = Decimal("0")
        annualized_roi = Decimal("0")

    # Component percentages for year 1
    if year1_total_return > 0:
        cash_flow_pct = (year1_cash_flow / year1_total_return * Decimal(100))
        appreciation_pct = (year1_appreciation / year1_total_return * Decimal(100))
        equity_pct = (year1_principal_paydown / year1_total_return * Decimal(100))
        tax_pct = (year1_tax_benefits / year1_total_return * Decimal(100))
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


def calculate_flip_strategy(
    purchase_price: Decimal,
    renovation_costs: Decimal,
    holding_period_months: int,
    expected_sale_price: Decimal,
    selling_costs: Decimal,
    down_payment: Decimal,
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    closing_costs: Decimal,
    property_tax_rate: Decimal,
    insurance_annual: Decimal | None = None,
    utilities_monthly: Decimal = Decimal("0"),
    property_type: str = "single-family",
    year_built: int = 2000,
) -> Dict[str, Any]:
    """Calculate fix-and-flip strategy returns.

    Args:
        purchase_price: Property purchase price
        renovation_costs: Total renovation costs
        holding_period_months: How long to hold before selling (3-6 months typical)
        expected_sale_price: Expected sale price after renovation
        selling_costs: Total selling costs (realtor fees, etc.)
        down_payment: Down payment amount
        loan_amount: Mortgage loan amount
        interest_rate: Annual interest rate as percentage
        loan_term_years: Loan term in years
        closing_costs: Closing costs on purchase
        property_tax_rate: Property tax rate as percentage
        insurance_annual: Annual insurance cost
        utilities_monthly: Monthly utility costs while vacant
        property_type: Type of property
        year_built: Year property was built

    Returns:
        Dictionary with flip strategy analysis
    """
    # Calculate holding costs for the period
    monthly_mortgage = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)
    annual_property_tax = calculate_property_tax(purchase_price, property_tax_rate)
    monthly_property_tax = annual_property_tax / Decimal(12)
    
    if insurance_annual is None:
        annual_insurance = estimate_insurance(purchase_price, property_type, year_built)
    else:
        annual_insurance = to_decimal(insurance_annual)
    monthly_insurance = annual_insurance / Decimal(12)

    monthly_holding_costs = (
        monthly_mortgage + monthly_property_tax + monthly_insurance + to_decimal(utilities_monthly)
    )
    
    total_holding_costs = monthly_holding_costs * Decimal(holding_period_months)

    # Total investment
    total_investment = (
        to_decimal(down_payment)
        + to_decimal(closing_costs)
        + to_decimal(renovation_costs)
    )

    # Calculate proceeds
    gross_sale_proceeds = to_decimal(expected_sale_price)
    net_sale_proceeds = gross_sale_proceeds - to_decimal(selling_costs)
    
    # Remaining loan balance after holding period
    principal_paid = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, holding_period_months // 12
    )
    remaining_loan = to_decimal(loan_amount) - principal_paid
    
    # Net profit
    net_profit = (
        net_sale_proceeds
        - remaining_loan
        - total_holding_costs
        - total_investment
    )

    # ROI
    if total_investment > 0:
        roi_percent = (net_profit / total_investment * Decimal(100))
        # Annualized return
        years = Decimal(holding_period_months) / Decimal(12)
        if years > 0 and roi_percent > Decimal("-100"):
            annualized_return = (
                ((Decimal(1) + roi_percent / Decimal(100)) ** (Decimal(1) / years) - Decimal(1))
                * Decimal(100)
            )
        else:
            annualized_return = Decimal("0")
    else:
        roi_percent = Decimal("0")
        annualized_return = Decimal("0")

    return {
        "totalInvestment": total_investment.quantize(Decimal("0.01")),
        "holdingCosts": total_holding_costs.quantize(Decimal("0.01")),
        "renovationCosts": to_decimal(renovation_costs).quantize(Decimal("0.01")),
        "saleProceeds": gross_sale_proceeds.quantize(Decimal("0.01")),
        "sellingCosts": to_decimal(selling_costs).quantize(Decimal("0.01")),
        "netProfit": net_profit.quantize(Decimal("0.01")),
        "roi": roi_percent.quantize(Decimal("0.1")),
        "timeframe": f"{holding_period_months} months",
        "annualizedReturn": annualized_return.quantize(Decimal("0.1")),
    }


def calculate_rental_strategy(
    purchase_price: Decimal,
    down_payment: Decimal,
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    closing_costs: Decimal,
    annual_cash_flow: Decimal,
    appreciation_rate: Decimal = Decimal("3.0"),
    holding_period_years: int = 5,
) -> Dict[str, Any]:
    """Calculate buy-and-hold rental strategy returns.

    Args:
        purchase_price: Property purchase price
        down_payment: Down payment amount
        loan_amount: Mortgage loan amount
        interest_rate: Annual interest rate as percentage
        loan_term_years: Loan term in years
        closing_costs: Closing costs
        annual_cash_flow: Annual cash flow (can be negative)
        appreciation_rate: Annual appreciation rate as percentage
        holding_period_years: How many years to hold

    Returns:
        Dictionary with rental strategy analysis
    """
    total_investment = to_decimal(down_payment) + to_decimal(closing_costs)

    # Simplified: assume constant cash flow (in reality it would improve over time)
    total_cash_flow = to_decimal(annual_cash_flow) * Decimal(holding_period_years)

    # Equity buildup from mortgage paydown
    equity_buildup = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, holding_period_years
    )

    # Appreciation
    appreciation = calculate_appreciation(
        purchase_price, appreciation_rate, holding_period_years
    )

    # Total gain
    total_gain = total_cash_flow + equity_buildup + appreciation

    # ROI
    if total_investment > 0:
        roi_percent = (total_gain / total_investment * Decimal(100))
        annualized_return = (
            ((Decimal(1) + roi_percent / Decimal(100)) ** (Decimal(1) / Decimal(holding_period_years)) - Decimal(1))
            * Decimal(100)
        )
    else:
        roi_percent = Decimal("0")
        annualized_return = Decimal("0")

    return {
        "totalInvestment": total_investment.quantize(Decimal("0.01")),
        "year1CashFlow": to_decimal(annual_cash_flow).quantize(Decimal("0.01")),
        f"year{holding_period_years}CashFlow": to_decimal(annual_cash_flow).quantize(Decimal("0.01")),  # Simplified
        f"totalCashFlow{holding_period_years}Years": total_cash_flow.quantize(Decimal("0.01")),
        f"equityBuildup{holding_period_years}Years": equity_buildup.quantize(Decimal("0.01")),
        f"appreciation{holding_period_years}Years": appreciation.quantize(Decimal("0.01")),
        f"totalGain{holding_period_years}Years": total_gain.quantize(Decimal("0.01")),
        "roi": roi_percent.quantize(Decimal("0.1")),
        "timeframe": f"{holding_period_years} years",
        "annualizedReturn": annualized_return.quantize(Decimal("0.1")),
    }


def calculate_vacation_rental_strategy(
    purchase_price: Decimal,
    down_payment: Decimal,
    loan_amount: Decimal,
    interest_rate: Decimal,
    loan_term_years: int,
    closing_costs: Decimal,
    avg_nightly_rate: Decimal,
    avg_occupancy_rate: Decimal,  # As percentage (e.g., 65 for 65%)
    cleaning_fee_per_stay: Decimal,
    monthly_operating_expenses: Decimal,
    holding_period_years: int = 5,
) -> Dict[str, Any]:
    """Calculate vacation rental strategy returns.

    Args:
        purchase_price: Property purchase price
        down_payment: Down payment amount
        loan_amount: Mortgage loan amount
        interest_rate: Annual interest rate as percentage
        loan_term_years: Loan term in years
        closing_costs: Closing costs
        avg_nightly_rate: Average nightly rental rate
        avg_occupancy_rate: Average occupancy rate as percentage
        cleaning_fee_per_stay: Cleaning fee per stay
        monthly_operating_expenses: Monthly operating expenses
        holding_period_years: How many years to hold

    Returns:
        Dictionary with vacation rental strategy analysis
    """
    total_investment = to_decimal(down_payment) + to_decimal(closing_costs)

    # Calculate annual income
    nights_per_year = Decimal(365)
    occupied_nights = nights_per_year * to_decimal(avg_occupancy_rate) / Decimal(100)
    
    # Assume average stay is 3 nights
    avg_stay_length = Decimal(3)
    num_stays = occupied_nights / avg_stay_length
    
    annual_rental_income = (
        occupied_nights * to_decimal(avg_nightly_rate)
        + num_stays * to_decimal(cleaning_fee_per_stay)
    )
    
    # Annual expenses
    monthly_mortgage = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)
    annual_debt_service = monthly_mortgage * Decimal(12)
    annual_operating_expenses = to_decimal(monthly_operating_expenses) * Decimal(12)
    
    # Cash flow
    annual_cash_flow = annual_rental_income - annual_debt_service - annual_operating_expenses
    
    # Calculate year 1 CoC
    if total_investment > 0:
        coc_return = (annual_cash_flow / total_investment * Decimal(100))
    else:
        coc_return = Decimal("0")

    # 5-year projection (simplified)
    total_cash_flow = annual_cash_flow * Decimal(holding_period_years)
    
    # Equity buildup
    equity_buildup = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, holding_period_years
    )
    
    # Appreciation (3% default)
    appreciation = calculate_appreciation(purchase_price, Decimal("3.0"), holding_period_years)
    
    total_gain = total_cash_flow + equity_buildup + appreciation
    
    if total_investment > 0:
        roi_percent = (total_gain / total_investment * Decimal(100))
        annualized_return = (
            ((Decimal(1) + roi_percent / Decimal(100)) ** (Decimal(1) / Decimal(holding_period_years)) - Decimal(1))
            * Decimal(100)
        )
    else:
        roi_percent = Decimal("0")
        annualized_return = Decimal("0")

    return {
        "totalInvestment": total_investment.quantize(Decimal("0.01")),
        "avgMonthlyIncome": (annual_rental_income / Decimal(12)).quantize(Decimal("0.01")),
        "avgMonthlyExpenses": (
            (annual_debt_service + annual_operating_expenses) / Decimal(12)
        ).quantize(Decimal("0.01")),
        "netCashFlowYear1": annual_cash_flow.quantize(Decimal("0.01")),
        "cocReturn": coc_return.quantize(Decimal("0.1")),
        "roi": roi_percent.quantize(Decimal("0.1")),
        "timeframe": f"{holding_period_years} years",
        "annualizedReturn": annualized_return.quantize(Decimal("0.1")),
        "seasonalityImpact": "High - Occupancy varies by season" if avg_occupancy_rate < 75 else "Moderate",
    }
