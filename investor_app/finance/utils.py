from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, Sequence

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


def irr(cashflows: Iterable[float | int | Decimal]) -> Decimal:
    cf = np.array([float(c) for c in cashflows], dtype=float)
    try:
        value = float(npf.irr(cf))
        if np.isnan(value) or np.isinf(value):
            return Decimal("0")
        return to_decimal(value)
    except Exception:
        return Decimal("0")


def score_listing_v1(listing: Listing) -> Decimal:
    """Basic Phase 1 scoring using price per sq ft and freshness.

    Higher score is better. This is a simple heuristic for MVP.

    Deprecated: use score_listing_v2 for passive investing use cases.
    Will be removed after all callers are migrated.
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
    monthly_payment = calculate_monthly_mortgage(
        loan_amount, interest_rate, loan_term_years
    )

    # Calculate remaining balance at start of year
    # Uses standard amortization formula: B = P * [(1+r)^(n-k) - 1] / [(1+r)^n - 1]
    # where B=balance, P=principal, r=rate, n=total payments, k=payments made
    payments_before = (year_num - 1) * 12
    if payments_before > 0:
        num_payments = loan_term_years * 12
        remaining_factor = (Decimal(1) + monthly_rate) ** Decimal(
            num_payments - payments_before
        )
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
    monthly_mortgage = calculate_monthly_mortgage(
        loan_amount, interest_rate, loan_term_years
    )
    annual_property_tax = calculate_property_tax(purchase_price, property_tax_rate)
    monthly_property_tax = annual_property_tax / Decimal(12)

    if insurance_annual is None:
        annual_insurance = estimate_insurance(purchase_price, property_type, year_built)
    else:
        annual_insurance = to_decimal(insurance_annual)
    monthly_insurance = annual_insurance / Decimal(12)

    monthly_holding_costs = (
        monthly_mortgage
        + monthly_property_tax
        + monthly_insurance
        + to_decimal(utilities_monthly)
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
        net_sale_proceeds - remaining_loan - total_holding_costs - total_investment
    )

    # ROI
    if total_investment > 0:
        roi_percent = net_profit / total_investment * Decimal(100)
        # Annualized return
        years = Decimal(holding_period_months) / Decimal(12)
        if years > 0 and roi_percent > Decimal("-100"):
            annualized_return = (
                (Decimal(1) + roi_percent / Decimal(100)) ** (Decimal(1) / years)
                - Decimal(1)
            ) * Decimal(100)
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
        roi_percent = total_gain / total_investment * Decimal(100)
        annualized_return = (
            (Decimal(1) + roi_percent / Decimal(100))
            ** (Decimal(1) / Decimal(holding_period_years))
            - Decimal(1)
        ) * Decimal(100)
    else:
        roi_percent = Decimal("0")
        annualized_return = Decimal("0")

    return {
        "totalInvestment": total_investment.quantize(Decimal("0.01")),
        "year1CashFlow": to_decimal(annual_cash_flow).quantize(Decimal("0.01")),
        f"year{holding_period_years}CashFlow": to_decimal(annual_cash_flow).quantize(
            Decimal("0.01")
        ),  # Simplified
        f"totalCashFlow{holding_period_years}Years": total_cash_flow.quantize(
            Decimal("0.01")
        ),
        f"equityBuildup{holding_period_years}Years": equity_buildup.quantize(
            Decimal("0.01")
        ),
        f"appreciation{holding_period_years}Years": appreciation.quantize(
            Decimal("0.01")
        ),
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
    avg_stay_length_nights: int = 3,  # Typical vacation rental stay length
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
        avg_stay_length_nights: Average length of stay in nights (default 3)

    Returns:
        Dictionary with vacation rental strategy analysis
    """
    total_investment = to_decimal(down_payment) + to_decimal(closing_costs)

    # Calculate annual income
    nights_per_year = Decimal(365)
    occupied_nights = nights_per_year * to_decimal(avg_occupancy_rate) / Decimal(100)

    # Calculate number of stays based on average stay length
    avg_stay_length = Decimal(avg_stay_length_nights)
    num_stays = occupied_nights / avg_stay_length

    annual_rental_income = occupied_nights * to_decimal(
        avg_nightly_rate
    ) + num_stays * to_decimal(cleaning_fee_per_stay)

    # Annual expenses
    monthly_mortgage = calculate_monthly_mortgage(
        loan_amount, interest_rate, loan_term_years
    )
    annual_debt_service = monthly_mortgage * Decimal(12)
    annual_operating_expenses = to_decimal(monthly_operating_expenses) * Decimal(12)

    # Cash flow
    annual_cash_flow = (
        annual_rental_income - annual_debt_service - annual_operating_expenses
    )

    # Calculate year 1 CoC
    if total_investment > 0:
        coc_return = annual_cash_flow / total_investment * Decimal(100)
    else:
        coc_return = Decimal("0")

    # 5-year projection (simplified)
    total_cash_flow = annual_cash_flow * Decimal(holding_period_years)

    # Equity buildup
    equity_buildup = calculate_principal_paydown(
        loan_amount, interest_rate, loan_term_years, holding_period_years
    )

    # Appreciation (3% default)
    appreciation = calculate_appreciation(
        purchase_price, Decimal("3.0"), holding_period_years
    )

    total_gain = total_cash_flow + equity_buildup + appreciation

    if total_investment > 0:
        roi_percent = total_gain / total_investment * Decimal(100)
        annualized_return = (
            (Decimal(1) + roi_percent / Decimal(100))
            ** (Decimal(1) / Decimal(holding_period_years))
            - Decimal(1)
        ) * Decimal(100)
    else:
        roi_percent = Decimal("0")
        annualized_return = Decimal("0")

    return {
        "totalInvestment": total_investment.quantize(Decimal("0.01")),
        "avgMonthlyIncome": (annual_rental_income / Decimal(12)).quantize(
            Decimal("0.01")
        ),
        "avgMonthlyExpenses": (
            (annual_debt_service + annual_operating_expenses) / Decimal(12)
        ).quantize(Decimal("0.01")),
        "netCashFlowYear1": annual_cash_flow.quantize(Decimal("0.01")),
        "cocReturn": coc_return.quantize(Decimal("0.1")),
        "roi": roi_percent.quantize(Decimal("0.1")),
        "timeframe": f"{holding_period_years} years",
        "annualizedReturn": annualized_return.quantize(Decimal("0.1")),
        "seasonalityImpact": (
            "High - Occupancy varies by season"
            if avg_occupancy_rate < 75
            else "Moderate"
        ),
    }


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


# ── Convenience aliases with calculate_ prefix ─────────────────────────────────
# These satisfy the Jumpstart requirement for explicitly-named calculate_* functions.


def calculate_noi(
    gross_income: Decimal,
    operating_expenses: Decimal,
) -> Decimal:
    """Calculate Net Operating Income (NOI).

    NOI = Gross Income - Operating Expenses

    Args:
        gross_income: Total annual rental and other income from the property.
        operating_expenses: Total annual operating expenses (excluding debt service).

    Returns:
        Net Operating Income as a Decimal.
    """
    return to_decimal(gross_income) - to_decimal(operating_expenses)


def calculate_cap_rate(
    annual_noi: Decimal,
    property_value: Decimal,
) -> Decimal:
    """Calculate Capitalization Rate.

    Cap Rate = NOI / Property Value

    Args:
        annual_noi: Net Operating Income.
        property_value: Current market value or purchase price of the property.

    Returns:
        Capitalization rate as a Decimal (e.g., 0.08 for 8%).

    Raises:
        ValueError: If property_value is zero.
    """
    pv = to_decimal(property_value)
    if pv == Decimal("0"):
        raise ValueError("Property value cannot be zero")
    return (to_decimal(annual_noi) / pv).quantize(Decimal("0.0001"))


def calculate_cash_on_cash(
    annual_cash_flow: Decimal,
    total_cash_invested: Decimal,
) -> Decimal:
    """Calculate Cash-on-Cash Return.

    Cash-on-Cash = Annual Cash Flow / Total Cash Invested

    Args:
        annual_cash_flow: Annual pre-tax cash flow from the investment.
        total_cash_invested: Total cash invested (down payment + closing costs).

    Returns:
        Cash-on-cash return as a Decimal (e.g., 0.10 for 10%).

    Raises:
        ValueError: If total_cash_invested is zero.
    """
    tci = to_decimal(total_cash_invested)
    if tci == Decimal("0"):
        raise ValueError("Total cash invested cannot be zero")
    return (to_decimal(annual_cash_flow) / tci).quantize(Decimal("0.0001"))


def calculate_irr(cash_flows: Sequence[float | int | Decimal]) -> Decimal:
    """Calculate Internal Rate of Return (IRR).

    Args:
        cash_flows: Sequence of cash flows, starting with the initial investment
            (typically negative) followed by periodic returns. Accepts int, float,
            or Decimal values; each value is coerced to float internally for
            numpy-financial.

    Returns:
        IRR as a Decimal (e.g., 0.15 for 15%).

    Raises:
        ValueError: If fewer than 2 cash flows are supplied or IRR cannot be computed.
    """
    if len(cash_flows) < 2:
        raise ValueError("At least 2 cash flows are required to calculate IRR")
    result = irr(cash_flows)
    if result == Decimal("0") and all(float(cf) >= 0 for cf in cash_flows):
        raise ValueError("IRR could not be computed for the given cash flows")
    return result


# ── Depreciation & Tax Modeling ────────────────────────────────────────────────


def annual_depreciation(purchase_price: Decimal, land_value: Decimal) -> Decimal:
    """Calculate the annual straight-line depreciation for a residential rental property.

    The IRS allows 27.5-year straight-line depreciation on the building portion
    (purchase price minus land value) of residential rental property.

    Args:
        purchase_price: Total purchase price of the property (must be > 0).
        land_value: Estimated value of the land component (must be >= 0 and
            < purchase_price). Land is not depreciable.

    Returns:
        Annual depreciation deduction as a Decimal representing the fixed deduction
        for a full year. Year-by-year schedule handling is the caller's responsibility:
        apply this amount for years 1–27 (full deduction), half this amount for year 28
        (remaining half-year fraction), and no deduction for years beyond year 28.

    Raises:
        ValueError: If purchase_price <= 0.
        ValueError: If land_value < 0.
        ValueError: If land_value >= purchase_price (no depreciable basis).

    Example:
        >>> annual_depreciation(Decimal("300000"), Decimal("50000"))
        Decimal("9090.909090909090909090909091")
    """
    pp = to_decimal(purchase_price)
    lv = to_decimal(land_value)

    if pp <= Decimal("0"):
        raise ValueError("purchase_price must be greater than zero")
    if lv < Decimal("0"):
        raise ValueError("land_value must be zero or greater")
    if lv >= pp:
        raise ValueError(
            "land_value must be less than purchase_price; land is not depreciable"
        )

    depreciable_basis = pp - lv
    return depreciable_basis / Decimal("27.5")


def after_tax_cash_flow(
    noi: Decimal,
    annual_debt_service: Decimal,
    depreciation_deduction: Decimal,
    marginal_tax_rate: Decimal,
) -> Decimal:
    """Calculate after-tax cash flow including the depreciation tax shield.

    Formula: (NOI - debt_service) + (depreciation × tax_rate)

    The depreciation tax shield represents the tax savings from the paper loss of
    depreciation, which reduces taxable income without a cash outflow.

    Args:
        noi: Net Operating Income (annual).
        annual_debt_service: Total annual mortgage payments (principal + interest).
        depreciation_deduction: Annual depreciation deduction (e.g., from
            ``annual_depreciation()``).
        marginal_tax_rate: Investor's marginal income tax rate as a decimal in [0, 1]
            (e.g., 0.24 for 24%).

    Returns:
        After-tax cash flow as a Decimal. A positive value indicates net cash benefit.

    Raises:
        ValueError: If marginal_tax_rate is outside the range [0, 1].

    Example:
        >>> after_tax_cash_flow(
        ...     Decimal("24000"), Decimal("18000"), Decimal("9091"), Decimal("0.24")
        ... )
        Decimal("8181.84")
    """
    rate = to_decimal(marginal_tax_rate)
    if rate < Decimal("0") or rate > Decimal("1"):
        raise ValueError(
            "marginal_tax_rate must be between 0 and 1 inclusive "
            f"(received {marginal_tax_rate})"
        )

    pre_tax_cf = to_decimal(noi) - to_decimal(annual_debt_service)
    tax_shield = to_decimal(depreciation_deduction) * rate
    return pre_tax_cf + tax_shield


def after_tax_irr(
    cash_flows: Sequence[Decimal],
    depreciation_schedule: Sequence[Decimal],
    marginal_tax_rate: Decimal,
) -> Decimal:
    """Calculate after-tax IRR by adjusting each period's cash flow by the depreciation tax shield.

    Each period's cash flow is increased by ``depreciation × marginal_tax_rate``.
    The first cash flow (index 0) is assumed to be the initial investment (negative)
    and is not adjusted — depreciation tax shields begin in period 1.

    Args:
        cash_flows: List of periodic cash flows. Index 0 is typically the initial
            investment (negative). Must have at least 2 elements.
        depreciation_schedule: List of annual depreciation amounts aligned to
            cash_flows[1:]. If shorter than cash_flows[1:], missing periods are
            treated as zero depreciation.
        marginal_tax_rate: Investor's marginal income tax rate as a decimal in [0, 1].

    Returns:
        After-tax IRR as a Decimal. Returns Decimal("0") if numpy-financial cannot
        converge (e.g., all non-negative flows or no sign change).

    Raises:
        ValueError: If fewer than 2 cash flows are supplied.
        ValueError: If marginal_tax_rate is outside the range [0, 1].

    Example:
        >>> after_tax_irr(
        ...     [Decimal("-100000"), Decimal("6000"), Decimal("106000")],
        ...     [Decimal("9091"), Decimal("9091")],
        ...     Decimal("0.24"),
        ... )
        Decimal("0.0718")
    """
    import logging

    logger = logging.getLogger(__name__)

    if len(cash_flows) < 2:
        raise ValueError("At least 2 cash flows are required to calculate IRR")

    rate = to_decimal(marginal_tax_rate)
    if rate < Decimal("0") or rate > Decimal("1"):
        raise ValueError(
            "marginal_tax_rate must be between 0 and 1 inclusive "
            f"(received {marginal_tax_rate})"
        )

    # Build adjusted cash flows: index 0 (initial investment) is not adjusted.
    adjusted: list[float] = [float(cash_flows[0])]
    for i, cf in enumerate(cash_flows[1:]):
        dep = (
            depreciation_schedule[i] if i < len(depreciation_schedule) else Decimal("0")
        )
        shield = to_decimal(dep) * rate
        adjusted.append(float(to_decimal(cf) + shield))

    cf_array = np.array(adjusted, dtype=float)
    try:
        value = float(npf.irr(cf_array))
        if np.isnan(value) or np.isinf(value):
            logger.warning(
                "after_tax_irr: numpy_financial.irr returned non-finite value; returning 0"
            )
            return Decimal("0")
        return to_decimal(value)
    except Exception as exc:
        logger.warning("after_tax_irr: numpy_financial.irr raised %s; returning 0", exc)
        return Decimal("0")


# ── Hold Period & Exit Analysis ────────────────────────────────────────────────


def project_annual_cash_flows(
    gross_rent_year1: Decimal,
    operating_expense_year1: Decimal,
    annual_debt_service: Decimal,
    rent_growth_rate: Decimal,
    expense_growth_rate: Decimal,
    hold_years: int,
) -> list[Decimal]:
    """Project year-by-year after-debt-service cash flows over a hold period.

    Each year's gross rent and operating expenses grow independently at their
    respective compound annual growth rates.  Annual debt service is assumed
    constant (fixed-rate mortgage).

    Formula per year ``n`` (1-indexed):
        gross_rent(n)    = gross_rent_year1 × (1 + rent_growth_rate)^(n-1)
        oper_expense(n)  = operating_expense_year1 × (1 + expense_growth_rate)^(n-1)
        NOI(n)           = gross_rent(n) - oper_expense(n)
        cash_flow(n)     = NOI(n) - annual_debt_service

    Args:
        gross_rent_year1: Gross rental income in year 1 (must be >= 0).
        operating_expense_year1: Operating expenses in year 1 (must be >= 0).
        annual_debt_service: Fixed annual mortgage payment (principal + interest;
            must be >= 0).
        rent_growth_rate: Annual rent growth rate as a decimal (e.g., 0.03 for 3%).
            Must be in the range [-0.5, 0.5].
        expense_growth_rate: Annual expense growth rate as a decimal.
            Must be in the range [-0.5, 0.5].
        hold_years: Number of years in the hold period.  Must be in [1, 50].

    Returns:
        List of annual cash-flow Decimals, one entry per year (length == hold_years).
        Negative values indicate years where debt service exceeds NOI.

    Raises:
        ValueError: If ``gross_rent_year1`` or ``operating_expense_year1`` or
            ``annual_debt_service`` is negative.
        ValueError: If ``hold_years`` is outside [1, 50].
        ValueError: If ``rent_growth_rate`` or ``expense_growth_rate`` is outside
            [-0.5, 0.5].

    Example:
        >>> flows = project_annual_cash_flows(
        ...     Decimal("36000"), Decimal("12000"), Decimal("18000"),
        ...     Decimal("0.03"), Decimal("0.02"), 5,
        ... )
        >>> len(flows)
        5
    """
    if hold_years < 1 or hold_years > 50:
        raise ValueError(f"hold_years must be between 1 and 50 (received {hold_years})")

    r_rate = to_decimal(rent_growth_rate)
    e_rate = to_decimal(expense_growth_rate)
    rate_limit = Decimal("0.5")
    if r_rate < -rate_limit or r_rate > rate_limit:
        raise ValueError(
            f"rent_growth_rate must be in [-0.5, 0.5] (received {rent_growth_rate})"
        )
    if e_rate < -rate_limit or e_rate > rate_limit:
        raise ValueError(
            f"expense_growth_rate must be in [-0.5, 0.5] (received {expense_growth_rate})"
        )

    rent = to_decimal(gross_rent_year1)
    expense = to_decimal(operating_expense_year1)
    debt = to_decimal(annual_debt_service)

    if rent < Decimal("0"):
        raise ValueError(
            f"gross_rent_year1 must be zero or greater (received {gross_rent_year1})"
        )
    if expense < Decimal("0"):
        raise ValueError(
            f"operating_expense_year1 must be zero or greater (received {operating_expense_year1})"
        )
    if debt < Decimal("0"):
        raise ValueError(
            f"annual_debt_service must be zero or greater (received {annual_debt_service})"
        )

    cash_flows: list[Decimal] = []
    one = Decimal("1")
    for year in range(1, hold_years + 1):
        exponent = year - 1
        gross = rent * (one + r_rate) ** exponent
        opex = expense * (one + e_rate) ** exponent
        annual_noi = gross - opex
        cash_flows.append(annual_noi - debt)

    return cash_flows


def project_property_value(
    purchase_price: Decimal,
    appreciation_rate: Decimal,
    hold_years: int,
) -> Decimal:
    """Project the market value of a property at the end of a hold period.

    Uses compound annual growth:
        value = purchase_price × (1 + appreciation_rate)^hold_years

    Supports conservative / base / optimistic scenarios by varying
    ``appreciation_rate`` (e.g., 0%, 3%, 5% for US residential).

    Args:
        purchase_price: Original purchase price of the property (must be > 0).
        appreciation_rate: Expected annual appreciation rate as a decimal.
            Must be >= -1 (a rate of -1 implies a total loss of value; rates
            below -1 are mathematically undefined for this formula).
        hold_years: Number of years to project forward (must be in [1, 50]).

    Returns:
        Projected property value as a Decimal.

    Raises:
        ValueError: If ``purchase_price`` <= 0.
        ValueError: If ``appreciation_rate`` < -1.
        ValueError: If ``hold_years`` is outside [1, 50].

    Example:
        >>> project_property_value(Decimal("300000"), Decimal("0.03"), 10)
        Decimal("403175....")
    """
    pp = to_decimal(purchase_price)
    rate = to_decimal(appreciation_rate)

    if pp <= Decimal("0"):
        raise ValueError(
            f"purchase_price must be greater than zero (received {purchase_price})"
        )
    if rate < Decimal("-1"):
        raise ValueError(
            f"appreciation_rate must be >= -1 (received {appreciation_rate})"
        )
    if hold_years < 1 or hold_years > 50:
        raise ValueError(f"hold_years must be between 1 and 50 (received {hold_years})")

    return pp * (Decimal("1") + rate) ** hold_years


def net_sale_proceeds(
    sale_price: Decimal,
    original_purchase_price: Decimal,
    outstanding_loan_balance: Decimal,
    accumulated_depreciation: Decimal,
    agent_commission_rate: Decimal = Decimal("0.06"),
    closing_cost_rate: Decimal = Decimal("0.01"),
    long_term_cg_rate: Decimal = Decimal("0.15"),
    depreciation_recapture_rate: Decimal = Decimal("0.25"),
) -> Decimal:
    """Calculate net cash to investor after costs and taxes upon property sale.

    Deductions applied in order:
    1. Agent commissions: ``sale_price × agent_commission_rate``
    2. Closing costs: ``sale_price × closing_cost_rate``
    3. Loan payoff: ``outstanding_loan_balance``
    4. Capital gains tax: max(``sale_price - original_purchase_price``, 0) × ``long_term_cg_rate``
       (no capital gains tax if property sold at a loss)
    5. Depreciation recapture: ``accumulated_depreciation × depreciation_recapture_rate``

    Args:
        sale_price: Gross sale price of the property.
        original_purchase_price: Price paid for the property at acquisition.
        outstanding_loan_balance: Remaining mortgage balance at time of sale
            (must be >= 0).
        accumulated_depreciation: Total depreciation taken over the holding period
            (must be >= 0).
        agent_commission_rate: Broker commission as a decimal (default 0.06 = 6%).
        closing_cost_rate: Seller's closing costs as a decimal (default 0.01 = 1%).
        long_term_cg_rate: Federal long-term capital gains tax rate as a decimal
            (default 0.15 = 15%).
        depreciation_recapture_rate: IRS Section 1250 recapture rate as a decimal
            (default 0.25 = 25%).

    Returns:
        Net cash proceeds to investor as a Decimal (may be negative if costs exceed
        gross proceeds).

    Raises:
        ValueError: If ``outstanding_loan_balance`` < 0.
        ValueError: If ``accumulated_depreciation`` < 0.
        ValueError: If any rate parameter is outside [0, 1].

    Example:
        >>> net_sale_proceeds(
        ...     Decimal("400000"), Decimal("300000"), Decimal("200000"),
        ...     Decimal("45000"),
        ... )
        Decimal("...")
    """
    sp = to_decimal(sale_price)
    opp = to_decimal(original_purchase_price)
    loan_bal = to_decimal(outstanding_loan_balance)
    acc_dep = to_decimal(accumulated_depreciation)
    commission_rate = to_decimal(agent_commission_rate)
    cc_rate = to_decimal(closing_cost_rate)
    cg_rate = to_decimal(long_term_cg_rate)
    recapture_rate = to_decimal(depreciation_recapture_rate)

    if loan_bal < Decimal("0"):
        raise ValueError(
            f"outstanding_loan_balance must be zero or greater (received {outstanding_loan_balance})"
        )
    if acc_dep < Decimal("0"):
        raise ValueError(
            f"accumulated_depreciation must be zero or greater (received {accumulated_depreciation})"
        )
    for name, val in [
        ("agent_commission_rate", commission_rate),
        ("closing_cost_rate", cc_rate),
        ("long_term_cg_rate", cg_rate),
        ("depreciation_recapture_rate", recapture_rate),
    ]:
        if val < Decimal("0") or val > Decimal("1"):
            raise ValueError(
                f"{name} must be between 0 and 1 inclusive (received {val})"
            )

    gross_proceeds = sp - sp * commission_rate - sp * cc_rate - loan_bal

    capital_gain = sp - opp
    cg_tax = max(capital_gain, Decimal("0")) * cg_rate

    recapture_tax = acc_dep * recapture_rate

    return gross_proceeds - cg_tax - recapture_tax


def total_return_summary(
    purchase_price: Decimal,
    down_payment: Decimal,
    annual_cash_flows: list[Decimal],
    net_sale_proceeds_amount: Decimal,
) -> Dict[str, Decimal]:
    """Summarise total investment return over the hold period.

    Combines cumulative cash flows and net sale proceeds to compute total return
    metrics.  IRR is computed using the full cash-flow series:
      - Year 0: ``-down_payment`` (initial equity outlay)
      - Years 1…N: ``annual_cash_flows``
      - Year N: ``annual_cash_flows[-1] + net_sale_proceeds_amount`` (exit year)

    Args:
        purchase_price: Original acquisition price of the property.  Included in
            the returned summary dict as ``"purchase_price"`` for caller convenience.
        down_payment: Equity invested at purchase (positive value; used as the
            year-0 outflow).
        annual_cash_flows: List of annual after-debt-service cash flows from
            ``project_annual_cash_flows()``.  Must have at least 1 element.
        net_sale_proceeds_amount: Net cash to investor upon sale from
            ``net_sale_proceeds()``.

    Returns:
        Dictionary with the following keys:

        - ``purchase_price`` (Decimal): The ``purchase_price`` argument.
        - ``total_cash_flow`` (Decimal): Sum of ``annual_cash_flows``.
        - ``net_sale_proceeds`` (Decimal): The ``net_sale_proceeds_amount`` argument.
        - ``total_return`` (Decimal): ``total_cash_flow + net_sale_proceeds``.
        - ``total_return_on_equity`` (Decimal): ``total_return / down_payment``, or
          ``Decimal("0")`` if ``down_payment`` is zero.
        - ``annualized_irr`` (Decimal): IRR computed via ``irr()`` over the full
          cash-flow series.

    Raises:
        ValueError: If ``annual_cash_flows`` is empty.
        ValueError: If ``down_payment`` < 0.

    Example:
        >>> summary = total_return_summary(
        ...     Decimal("300000"), Decimal("60000"),
        ...     [Decimal("6000")] * 10, Decimal("120000"),
        ... )
        >>> summary["total_cash_flow"]
        Decimal("60000")
    """
    if not annual_cash_flows:
        raise ValueError("annual_cash_flows must contain at least one element")

    dp = to_decimal(down_payment)
    if dp < Decimal("0"):
        raise ValueError(
            f"down_payment must be zero or greater (received {down_payment})"
        )

    total_cf = sum(annual_cash_flows, Decimal("0"))
    nsp = to_decimal(net_sale_proceeds_amount)
    total_ret = total_cf + nsp

    if dp == Decimal("0"):
        roe = Decimal("0")
    else:
        roe = total_ret / dp

    # Build IRR cash-flow series: year-0 outflow, annual CFs, exit-year bump
    irr_flows: list[Decimal] = [-dp]
    for i, cf in enumerate(annual_cash_flows):
        if i == len(annual_cash_flows) - 1:
            irr_flows.append(cf + nsp)
        else:
            irr_flows.append(cf)

    annualized = irr(irr_flows)

    return {
        "purchase_price": to_decimal(purchase_price),
        "total_cash_flow": total_cf,
        "net_sale_proceeds": nsp,
        "total_return": total_ret,
        "total_return_on_equity": roe,
        "annualized_irr": annualized,
    }


def depreciation_recapture_tax(
    accumulated_depreciation: Decimal,
    recapture_rate: Decimal = Decimal("0.25"),
) -> Decimal:
    """Calculate the depreciation recapture tax owed upon sale of the property.

    Under IRS Section 1250, accumulated depreciation is recaptured at a maximum
    rate of 25% when the property is sold. This tax is owed regardless of whether
    the property sold at a gain or loss on paper.

    Args:
        accumulated_depreciation: Total depreciation taken over the holding period
            (sum of annual deductions). Must be >= 0.
        recapture_rate: IRS Section 1250 recapture rate as a decimal in [0, 1].
            Defaults to 0.25 (25%).

    Returns:
        Depreciation recapture tax owed as a Decimal.

    Raises:
        ValueError: If accumulated_depreciation < 0.
        ValueError: If recapture_rate is outside [0, 1].

    Example:
        >>> depreciation_recapture_tax(Decimal("45000"))
        Decimal("11250.00")
    """
    acc_dep = to_decimal(accumulated_depreciation)
    rate = to_decimal(recapture_rate)

    if acc_dep < Decimal("0"):
        raise ValueError("accumulated_depreciation must be zero or greater")
    if rate < Decimal("0") or rate > Decimal("1"):
        raise ValueError(
            "recapture_rate must be between 0 and 1 inclusive "
            f"(received {recapture_rate})"
        )

    return acc_dep * rate


# ── Underwriting Score v2 ──────────────────────────────────────────────────────


def one_percent_rule(monthly_rent: Decimal, purchase_price: Decimal) -> bool:
    """Evaluate the 1% Rule for a rental property.

    The 1% Rule is a quick pass/fail filter: monthly rent should be at least
    1% of the purchase price to indicate a potentially viable rental investment.

    Args:
        monthly_rent: Expected gross monthly rental income.
        purchase_price: Total purchase price of the property.

    Returns:
        True if monthly_rent / purchase_price >= 0.01, False otherwise.

    Raises:
        ValueError: If purchase_price is zero or negative.
    """
    pp = to_decimal(purchase_price)
    if pp <= Decimal("0"):
        raise ValueError(
            f"purchase_price must be greater than zero (received {purchase_price})"
        )
    return to_decimal(monthly_rent) / pp >= Decimal("0.01")


def gross_rent_multiplier(purchase_price: Decimal, annual_rent: Decimal) -> Decimal:
    """Calculate Gross Rent Multiplier (GRM).

    GRM = Purchase Price / Annual Rent

    Lower GRM values indicate better value relative to rental income.
    Typical benchmarks: < 10 excellent, 10–15 good, 15–20 fair, > 20 poor.

    Args:
        purchase_price: Total purchase price of the property.
        annual_rent: Expected gross annual rental income.

    Returns:
        GRM as a Decimal.

    Raises:
        ValueError: If annual_rent is zero or negative.
    """
    ar = to_decimal(annual_rent)
    if ar <= Decimal("0"):
        raise ValueError(
            f"annual_rent must be greater than zero (received {annual_rent})"
        )
    return to_decimal(purchase_price) / ar


def _grm_score(grm: Decimal) -> Decimal:
    """Map a GRM value to a 0–100 sub-score using published heuristics.

    Heuristics: GRM < 10 → excellent (100), 10–15 → good (75),
    15–20 → fair (40), > 20 → poor (10).

    Args:
        grm: Gross Rent Multiplier value.

    Returns:
        Sub-score as a Decimal in [0, 100].
    """
    if grm < Decimal("10"):
        return Decimal("100")
    if grm < Decimal("15"):
        return Decimal("75")
    if grm < Decimal("20"):
        return Decimal("40")
    return Decimal("10")


def score_listing_v2(
    purchase_price: Decimal,
    monthly_rent: Decimal,
    annual_noi: Decimal,
    local_market_cap_rate: Decimal,
    down_payment: Decimal,
    annual_debt_service: Decimal,
) -> dict:
    """Compute an investor-grade multi-signal underwriting score for a rental listing.

    Signals and weights (hardcoded; future versions should read from
    settings.UNDERWRITING_SCORE_WEIGHTS):
        - 1% Rule pass/fail   : 20%
        - Cap rate vs. market : 30%
        - CoC Year 1          : 30%
        - GRM heuristic       : 20%

    A deal that fails the 1% Rule has its composite_score capped at 40.

    Args:
        purchase_price: Total purchase price of the property. Must be > 0.
        monthly_rent: Expected gross monthly rental income. Must be > 0.
        annual_noi: Net Operating Income for Year 1. Must be > 0.
        local_market_cap_rate: Prevailing cap rate for the market as a decimal
            (e.g., Decimal("0.06") for 6%). Must be > 0.
        down_payment: Cash down payment (total cash invested). Must be > 0.
        annual_debt_service: Total annual principal + interest payments. Must be > 0.

    Returns:
        Dict with keys:
            one_percent_rule_pass (bool): True if monthly_rent / purchase_price >= 1%.
            grm (Decimal): Gross Rent Multiplier.
            cap_rate (Decimal): cap rate = annual_noi / purchase_price.
            cap_rate_vs_market (Decimal): cap_rate minus local_market_cap_rate;
                positive means above-market (better).
            coc_year1 (Decimal): Cash-on-Cash return for Year 1.
            composite_score (Decimal): Weighted score in [0, 100].

    Raises:
        ValueError: If any of purchase_price, monthly_rent, annual_noi,
            local_market_cap_rate, down_payment, or annual_debt_service is <= 0.
    """
    # -- Input validation -------------------------------------------------------
    inputs = {
        "purchase_price": purchase_price,
        "monthly_rent": monthly_rent,
        "annual_noi": annual_noi,
        "local_market_cap_rate": local_market_cap_rate,
        "down_payment": down_payment,
        "annual_debt_service": annual_debt_service,
    }
    for name, value in inputs.items():
        if to_decimal(value) <= Decimal("0"):
            raise ValueError(f"{name} must be greater than zero (received {value})")

    # -- Individual signals -----------------------------------------------------
    pp = to_decimal(purchase_price)
    mr = to_decimal(monthly_rent)
    noi_val = to_decimal(annual_noi)
    market_cap = to_decimal(local_market_cap_rate)
    dp = to_decimal(down_payment)
    ads = to_decimal(annual_debt_service)

    one_pct_pass = one_percent_rule(mr, pp)
    grm = gross_rent_multiplier(pp, mr * Decimal("12"))
    property_cap_rate = noi_val / pp
    cap_rate_vs_market = property_cap_rate - market_cap
    annual_cash_flow = noi_val - ads
    coc_year1 = annual_cash_flow / dp

    # -- Sub-scores (each 0–100) ------------------------------------------------
    # 1% Rule: full points if pass, zero if fail
    one_pct_sub = Decimal("100") if one_pct_pass else Decimal("0")

    # Cap rate vs market: scale so +5 pp above market = 100, -5 pp = 0
    # cap_rate_vs_market is a raw decimal difference (e.g. 0.02 = 2 pp above)
    cap_vs_market_sub = (
        (cap_rate_vs_market / Decimal("0.05")) * Decimal("100")
    ).max(Decimal("0")).min(Decimal("100"))

    # CoC Year 1: scale so 20% CoC = 100 points, 0% CoC = 0 points
    coc_sub = (coc_year1 / Decimal("0.20") * Decimal("100")).max(Decimal("0")).min(
        Decimal("100")
    )

    # GRM heuristic sub-score
    grm_sub = _grm_score(grm)

    # -- Composite score --------------------------------------------------------
    # Weights: 1% rule 20%, cap vs market 30%, CoC 30%, GRM 20%
    composite = (
        one_pct_sub * Decimal("0.20")
        + cap_vs_market_sub * Decimal("0.30")
        + coc_sub * Decimal("0.30")
        + grm_sub * Decimal("0.20")
    )

    # Cap at 40 if 1% rule fails
    if not one_pct_pass:
        composite = composite.min(Decimal("40"))

    composite = composite.max(Decimal("0")).min(Decimal("100"))

    return {
        "one_percent_rule_pass": one_pct_pass,
        "grm": grm,
        "cap_rate": property_cap_rate,
        "cap_rate_vs_market": cap_rate_vs_market,
        "coc_year1": coc_year1,
        "composite_score": composite,
    }
