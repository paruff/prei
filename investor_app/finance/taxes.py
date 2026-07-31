"""Depreciation, tax benefits, hold-period projections, and exit/sale analysis."""

from __future__ import annotations

from decimal import Decimal
import logging
from typing import Dict, Sequence

import numpy as np
import numpy_financial as npf

from investor_app.finance.utils import to_decimal

logger = logging.getLogger(__name__)


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
    from investor_app.finance.mortgage import calculate_monthly_mortgage

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
        apply this amount for years 1-27 (full deduction), half this amount for year 28
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

    Formula: (NOI - debt_service) + (depreciation x tax_rate)

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

    Each period's cash flow is increased by ``depreciation * marginal_tax_rate``.
    The first cash flow (index 0) is assumed to be the initial investment (negative)
    and is not adjusted -- depreciation tax shields begin in period 1.

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

    Raises:
        ValueError: If gross_rent_year1 or operating_expense_year1 or
            annual_debt_service is negative.
        ValueError: If hold_years is outside [1, 50].
        ValueError: If rent_growth_rate or expense_growth_rate is outside
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
        value = purchase_price * (1 + appreciation_rate)^hold_years

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
        ValueError: If purchase_price <= 0.
        ValueError: If appreciation_rate < -1.
        ValueError: If hold_years is outside [1, 50].

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
    1. Agent commissions: sale_price * agent_commission_rate
    2. Closing costs: sale_price * closing_cost_rate
    3. Loan payoff: outstanding_loan_balance
    4. Capital gains tax: max(sale_price - original_purchase_price, 0) * long_term_cg_rate
    5. Depreciation recapture: accumulated_depreciation * depreciation_recapture_rate

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
        Net cash proceeds to investor as a Decimal.

    Raises:
        ValueError: If outstanding_loan_balance < 0.
        ValueError: If accumulated_depreciation < 0.
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
    metrics.

    Args:
        purchase_price: Original acquisition price of the property.
        down_payment: Equity invested at purchase (positive value; used as the
            year-0 outflow).
        annual_cash_flows: List of annual after-debt-service cash flows from
            ``project_annual_cash_flows()``.  Must have at least 1 element.
        net_sale_proceeds_amount: Net cash to investor upon sale from
            ``net_sale_proceeds()``.

    Returns:
        Dictionary with keys: purchase_price, total_cash_flow, net_sale_proceeds,
        total_return, total_return_on_equity, annualized_irr.

    Raises:
        ValueError: If annual_cash_flows is empty.
        ValueError: If down_payment < 0.

    Example:
        >>> summary = total_return_summary(
        ...     Decimal("300000"), Decimal("60000"),
        ...     [Decimal("6000")] * 10, Decimal("120000"),
        ... )
        >>> summary["total_cash_flow"]
        Decimal("60000")
    """
    from investor_app.finance.utils import irr

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
    rate of 25% when the property is sold.

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


def calculate_annual_depreciation(
    purchase_price: Decimal,
    land_value_pct: Decimal = Decimal("0.20"),
) -> Decimal:
    """Calculate annual straight-line depreciation for residential real estate.

    Uses the 27.5-year straight-line schedule on the improvement value
    (purchase price minus land).

    Args:
        purchase_price: Total purchase price of the property (must be > 0).
        land_value_pct: Fraction of purchase price attributable to land,
            expressed as a decimal (e.g. 0.20 for 20%).
            Must be in the range [0, 1).  Default 0.20.

    Returns:
        Annual depreciation deduction as a Decimal.

    Raises:
        ValueError: If purchase_price <= 0.
        ValueError: If land_value_pct is outside [0, 1).

    Example:
        >>> calculate_annual_depreciation(Decimal("200000"), Decimal("0.20"))
        Decimal("5818.181818181818181818181818")
    """
    pp = to_decimal(purchase_price)
    lvp = to_decimal(land_value_pct)

    if pp <= Decimal("0"):
        raise ValueError(
            f"purchase_price must be greater than zero (received {purchase_price})"
        )
    if lvp < Decimal("0") or lvp >= Decimal("1"):
        raise ValueError(
            f"land_value_pct must be in [0, 1) (received {land_value_pct})"
        )

    improvement_value = pp * (Decimal("1") - lvp)
    return improvement_value / Decimal("27.5")


def calculate_after_tax_cashflow(
    pre_tax_annual_cashflow: Decimal,
    annual_depreciation: Decimal,
    marginal_tax_rate: Decimal,
) -> Decimal:
    """Calculate after-tax cash flow including the depreciation tax shield.

    As simplified model — does not account for passive activity loss (PAL) rules,
    cost segregation, or other advanced tax strategies.
    A UI disclaimer should note this limitation.

    Formula:
        taxable_income = pre_tax_annual_cashflow - annual_depreciation
        if taxable_income < 0:
            tax_savings = abs(taxable_income) * marginal_tax_rate
            after_tax = pre_tax_annual_cashflow + tax_savings
        else:
            tax_owed = taxable_income * marginal_tax_rate
            after_tax = pre_tax_annual_cashflow - tax_owed

    Args:
        pre_tax_annual_cashflow: Annual pre-tax cash flow from the property.
            Can be negative.
        annual_depreciation: Annual depreciation deduction (built-in from
            ``calculate_annual_depreciation``).
        marginal_tax_rate: Investor's marginal income-tax rate as a decimal
            in [0, 1] (e.g., 0.32 for 32%).

    Returns:
        After-tax annual cash flow as a Decimal.

    Raises:
        ValueError: If marginal_tax_rate is outside [0, 1].

    Example:
        >>> calculate_after_tax_cashflow(
        ...     Decimal("6000"), Decimal("5818"), Decimal("0.32")
        ... )
        Decimal("5941.76")
    """
    cashflow = to_decimal(pre_tax_annual_cashflow)
    depreciation = to_decimal(annual_depreciation)
    rate = to_decimal(marginal_tax_rate)

    if rate < Decimal("0") or rate > Decimal("1"):
        raise ValueError(
            f"marginal_tax_rate must be in [0, 1] (received {marginal_tax_rate})"
        )

    taxable_income = cashflow - depreciation

    if taxable_income < 0:
        tax_savings = abs(taxable_income) * rate
        return cashflow + tax_savings
    tax_owed = taxable_income * rate
    return cashflow - tax_owed
