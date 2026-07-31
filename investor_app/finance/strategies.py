"""Investment strategy calculations: fix-and-flip, buy-and-hold, vacation rental, BRRRR."""

from __future__ import annotations

from decimal import Decimal
import logging
from statistics import median
from typing import Any, Dict

from investor_app.finance.utils import to_decimal

logger = logging.getLogger(__name__)


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
    from investor_app.finance.mortgage import (
        calculate_monthly_mortgage,
        calculate_principal_paydown,
        calculate_property_tax,
        estimate_insurance,
    )

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
    from investor_app.finance.mortgage import (
        calculate_appreciation,
        calculate_principal_paydown,
    )

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
    from investor_app.finance.mortgage import (
        calculate_appreciation,
        calculate_monthly_mortgage,
        calculate_principal_paydown,
    )

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


# ── BRRRR ──────────────────────────────────────────────────────────────────────


def estimate_arv(
    comparable_sales: list[tuple[Decimal, Decimal]],
    subject_sqft: Decimal,
) -> Decimal:
    """Estimate After-Repair Value (ARV) from comparable sales.

    Args:
        comparable_sales: List of ``(price, sqft)`` tuples, one per comparable
            sale.  Both ``price`` and ``sqft`` must be positive.
        subject_sqft: Square footage of the subject property (must be > 0).

    Returns:
        Estimated ARV as a Decimal.

    Raises:
        ValueError: If ``comparable_sales`` is empty.
        ValueError: If any comparable has ``price <= 0`` or ``sqft <= 0``.
        ValueError: If ``subject_sqft <= 0``.
    """
    if not comparable_sales:
        raise ValueError("comparable_sales must not be empty")

    subject = to_decimal(subject_sqft)
    if subject <= Decimal("0"):
        raise ValueError(
            f"subject_sqft must be greater than zero (received {subject_sqft})"
        )

    ppsf_values: list[Decimal] = []
    for idx, (price, sqft) in enumerate(comparable_sales):
        p = to_decimal(price)
        s = to_decimal(sqft)
        if p <= Decimal("0"):
            raise ValueError(
                f"comparable_sales[{idx}]: price must be greater than zero (received {price})"
            )
        if s <= Decimal("0"):
            raise ValueError(
                f"comparable_sales[{idx}]: sqft must be greater than zero (received {sqft})"
            )
        ppsf_values.append(p / s)

    median_ppsf = to_decimal(median(ppsf_values))
    return median_ppsf * subject


def estimate_rehab_cost(
    sqft: Decimal,
    renovation_level: str,
    cost_per_sqft: dict[str, Decimal],
) -> Decimal:
    """Estimate total rehab cost for a property.

    Args:
        sqft: Square footage of the property (must be > 0).
        renovation_level: Scope of renovation.  Must be one of the keys present
            in ``cost_per_sqft`` (typically ``"cosmetic"``, ``"moderate"``, or
            ``"full_gut"``).
        cost_per_sqft: Mapping from renovation level to cost per square foot.
            Supply ``settings.REHAB_COST_PER_SQFT`` from the service layer to
            keep this function Django-free.

    Returns:
        Estimated rehab cost as a Decimal.

    Raises:
        ValueError: If ``renovation_level`` is not a key in ``cost_per_sqft``.
        ValueError: If ``sqft <= 0``.
    """
    valid_levels = set(cost_per_sqft.keys())
    if renovation_level not in valid_levels:
        raise ValueError(
            f"renovation_level must be one of {sorted(valid_levels)} "
            f"(received {renovation_level!r})"
        )
    s = to_decimal(sqft)
    if s <= Decimal("0"):
        raise ValueError(f"sqft must be greater than zero (received {sqft})")

    rate = to_decimal(cost_per_sqft[renovation_level])
    return rate * s


def max_refinance_loan(
    arv: Decimal,
    ltv_ratio: Decimal = Decimal("0.75"),
) -> Decimal:
    """Calculate the maximum cash-out refinance loan amount at a given LTV.

    Args:
        arv: After-Repair Value of the property (must be > 0).
        ltv_ratio: Loan-to-value ratio expressed as a decimal strictly between
            0 and 1 (e.g., ``Decimal("0.75")`` for 75 %).

    Returns:
        Maximum refinance loan amount as a Decimal.

    Raises:
        ValueError: If ``arv <= 0``.
        ValueError: If ``ltv_ratio`` is not strictly in ``(0, 1)``.
    """
    a = to_decimal(arv)
    ltv = to_decimal(ltv_ratio)

    if a <= Decimal("0"):
        raise ValueError(f"arv must be greater than zero (received {arv})")
    if ltv <= Decimal("0") or ltv >= Decimal("1"):
        raise ValueError(
            f"ltv_ratio must be strictly between 0 and 1 (received {ltv_ratio})"
        )

    return a * ltv


def cash_left_in_deal(
    purchase_price: Decimal,
    rehab_cost: Decimal,
    cash_out_refi_amount: Decimal,
    closing_costs: Decimal = Decimal("0"),
) -> Decimal:
    """Calculate the investor's remaining cash deployed after a cash-out refinance.

    Formula::

        cash_left = purchase_price + rehab_cost + closing_costs - cash_out_refi_amount

    A negative or zero result means the investor has recouped all invested capital
    (the "infinite CoC" scenario in BRRRR terminology).

    Args:
        purchase_price: Purchase price of the property.
        rehab_cost: Total rehabilitation cost.
        cash_out_refi_amount: Proceeds from the cash-out refinance.
        closing_costs: Total closing costs (purchase + refi combined).  Defaults
            to ``Decimal("0")``.

    Returns:
        Cash left in the deal as a Decimal.  Negative or zero => infinite CoC.
    """
    return (
        to_decimal(purchase_price)
        + to_decimal(rehab_cost)
        + to_decimal(closing_costs)
        - to_decimal(cash_out_refi_amount)
    )


def brrrr_coc_return(
    annual_net_cash_flow: Decimal,
    cash_left_in_deal: Decimal,
) -> Decimal:
    """Calculate Cash-on-Cash return for a BRRRR deal.

    Handles the "infinite CoC" scenario where the investor has recouped all
    (or more than all) of their capital.

    Rules:
    * ``cash_left_in_deal <= 0`` -> returns ``Decimal("Infinity")`` regardless
      of cash flow (investor has no capital remaining in the deal).
    * ``cash_left_in_deal > 0`` and ``annual_net_cash_flow == 0`` -> returns
      ``Decimal("0")`` (no return on remaining capital).
    * Otherwise -> returns ``annual_net_cash_flow / cash_left_in_deal``.

    Args:
        annual_net_cash_flow: Annual after-debt-service cash flow (can be
            negative for a losing deal).
        cash_left_in_deal: Capital still deployed after the cash-out refi
            (from ``cash_left_in_deal()``).

    Returns:
        CoC return as a Decimal.  ``Decimal("Infinity")`` signals infinite CoC.
    """
    left = to_decimal(cash_left_in_deal)
    flow = to_decimal(annual_net_cash_flow)

    if left <= Decimal("0"):
        return Decimal("Infinity")
    if flow == Decimal("0"):
        return Decimal("0")
    return flow / left
