"""Hold-period projections and exit analysis for investment properties."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, List

import numpy as np
import numpy_financial as npf

from investor_app.finance.utils import (
    calculate_after_tax_cashflow,
    calculate_annual_depreciation,
    calculate_monthly_mortgage,
    to_decimal,
)

if TYPE_CHECKING:
    from core.models import Property

logger = logging.getLogger(__name__)


@dataclass
class YearlyProjection:
    """One year of projected cash flow and equity data."""

    year: int
    gross_rent: Decimal
    operating_expenses: Decimal
    noi: Decimal
    mortgage_payment_annual: Decimal
    pre_tax_cashflow: Decimal
    after_tax_cashflow: Decimal
    loan_balance: Decimal
    property_value: Decimal
    equity: Decimal
    cumulative_cashflow: Decimal


@dataclass
class ExitAnalysis:
    """Summary of projected returns at disposition."""

    gross_sale_price: Decimal
    selling_costs: Decimal  # default 6% (agent + closing)
    loan_payoff: Decimal
    net_proceeds_before_tax: Decimal
    estimated_capital_gains_tax: Decimal  # simple: gains * 0.20 (long-term rate)
    net_proceeds_after_tax: Decimal
    total_return: Decimal  # net_proceeds + cumulative_cashflow - initial_investment
    annualized_irr: Decimal


def _annual_mortgage_payment(
    loan_amount: Decimal, interest_rate_pct: Decimal, loan_term_years: int
) -> Decimal:
    """Annual principal + interest mortgage payment."""
    monthly = calculate_monthly_mortgage(
        loan_amount, interest_rate_pct, loan_term_years
    )
    return (monthly * Decimal("12")).quantize(Decimal("0.01"))


def _remaining_balance_after_year(
    loan_amount: Decimal,
    interest_rate_pct: Decimal,
    loan_term_years: int,
    years_elapsed: int,
) -> Decimal:
    """Standard amortization: remaining balance after *years_elapsed* years."""
    loan_amt = to_decimal(loan_amount)
    rate = to_decimal(interest_rate_pct)

    if loan_amt <= 0 or years_elapsed <= 0:
        return loan_amt

    if rate == 0:
        monthly_principal = loan_amt / Decimal(loan_term_years * 12)
        paid = monthly_principal * Decimal(years_elapsed * 12)
        return max(loan_amt - paid, Decimal("0")).quantize(Decimal("0.01"))

    monthly_rate = rate / Decimal("100") / Decimal("12")
    num_payments = Decimal(loan_term_years * 12)
    payments_made = Decimal(years_elapsed * 12)

    # B = P * [(1+r)^n - (1+r)^k] / [(1+r)^n - 1]
    factor_n = (Decimal("1") + monthly_rate) ** num_payments
    factor_k = (Decimal("1") + monthly_rate) ** payments_made
    balance = loan_amt * (factor_n - factor_k) / (factor_n - Decimal("1"))

    return max(balance, Decimal("0")).quantize(Decimal("0.01"))


def project_hold_period(
    property: Property,
    hold_years: int = 10,
    annual_rent_growth_pct: Decimal = Decimal("0.03"),
    annual_appreciation_pct: Decimal = Decimal("0.03"),
    annual_expense_inflation_pct: Decimal = Decimal("0.02"),
    marginal_tax_rate: Decimal = Decimal("0.24"),
    selling_costs_pct: Decimal = Decimal("0.06"),
) -> tuple[List[YearlyProjection], ExitAnalysis]:
    """Return year-by-year projections and exit analysis.

    Rent grows by *annual_rent_growth_pct* each year.
    Expenses grow by *annual_expense_inflation_pct* each year (mortgage is fixed).
    Property value grows by *annual_appreciation_pct* each year.
    Loan balance decreases via standard amortization each year.

    Args:
        property: A ``Property`` instance with financial fields populated.
        hold_years: Number of years to project (1–50).
        annual_rent_growth_pct: Annual rent growth as a fraction (e.g. 0.03 = 3 %).
        annual_appreciation_pct: Annual appreciation as a fraction.
        annual_expense_inflation_pct: Annual expense inflation as a fraction.
        marginal_tax_rate: Investor's marginal tax rate as a fraction [0, 1].
        selling_costs_pct: Selling costs as a fraction of sale price (default 6 %).

    Returns:
        A tuple of (yearly_projections, exit_analysis).

    Raises:
        ValueError: If hold_years is outside [1, 50].
    """
    if hold_years < 1 or hold_years > 50:
        raise ValueError(f"hold_years must be between 1 and 50 (received {hold_years})")

    pp = to_decimal(property.purchase_price)
    dp_pct = to_decimal(property.down_payment_pct)
    rate_pct = to_decimal(property.interest_rate)
    loan_term = int(property.loan_term_years)

    # Initial values
    down_payment = (pp * dp_pct).quantize(Decimal("0.01"))
    loan_amount = pp - down_payment
    initial_investment = down_payment  # cash invested at close

    # Year-1 operating figures
    monthly_rent = to_decimal(property.monthly_rent_gross)
    other_monthly = to_decimal(property.other_monthly_income)
    vacancy = to_decimal(property.vacancy_rate)
    mgmt_fee_pct = to_decimal(property.mgmt_fee_pct)
    taxes_annual = to_decimal(property.property_taxes_annual)
    insurance_annual = to_decimal(property.insurance_annual)
    hoa_monthly = to_decimal(property.hoa_monthly)
    maintenance_monthly = to_decimal(property.maintenance_monthly)
    capex_monthly = to_decimal(property.capex_monthly)

    # Fixed annual mortgage payment
    mortgage_annual = _annual_mortgage_payment(loan_amount, rate_pct, loan_term)

    # Annual depreciation for tax shield
    annual_depr = calculate_annual_depreciation(pp)

    projections: List[YearlyProjection] = []
    cumulative_cf = Decimal("0")
    one = Decimal("1")

    for year in range(1, hold_years + 1):
        # --- Income ---
        growth_factor_rent = (one + to_decimal(annual_rent_growth_pct)) ** (year - 1)
        gross_rent = (monthly_rent * Decimal("12") * growth_factor_rent).quantize(
            Decimal("0.01")
        )
        other_income = (other_monthly * Decimal("12") * growth_factor_rent).quantize(
            Decimal("0.01")
        )
        potential_income = gross_rent + other_income
        vacancy_loss = (potential_income * vacancy).quantize(Decimal("0.01"))
        effective_income = potential_income - vacancy_loss

        # --- Expenses (inflation-adjusted, except mortgage) ---
        expense_factor = (one + to_decimal(annual_expense_inflation_pct)) ** (year - 1)
        inflated_taxes = (taxes_annual * expense_factor).quantize(Decimal("0.01"))
        inflated_insurance = (insurance_annual * expense_factor).quantize(
            Decimal("0.01")
        )
        inflated_hoa = (hoa_monthly * Decimal("12") * expense_factor).quantize(
            Decimal("0.01")
        )
        inflated_maintenance = (
            maintenance_monthly * Decimal("12") * expense_factor
        ).quantize(Decimal("0.01"))
        inflated_capex = (capex_monthly * Decimal("12") * expense_factor).quantize(
            Decimal("0.01")
        )
        management_fee = (effective_income * mgmt_fee_pct).quantize(Decimal("0.01"))

        operating_expenses = (
            inflated_taxes
            + inflated_insurance
            + inflated_hoa
            + inflated_maintenance
            + inflated_capex
            + management_fee
        )

        # --- NOI ---
        noi = effective_income - operating_expenses

        # --- Cash flow ---
        pre_tax_cf = noi - mortgage_annual
        after_tax_cf = calculate_after_tax_cashflow(
            pre_tax_cf, annual_depr, marginal_tax_rate
        )
        cumulative_cf += after_tax_cf

        # --- Equity ---
        prop_value = (
            pp * ((one + to_decimal(annual_appreciation_pct)) ** year)
        ).quantize(Decimal("0.01"))
        loan_bal = _remaining_balance_after_year(loan_amount, rate_pct, loan_term, year)
        equity = prop_value - loan_bal

        projections.append(
            YearlyProjection(
                year=year,
                gross_rent=gross_rent,
                operating_expenses=operating_expenses,
                noi=noi.quantize(Decimal("0.01")),
                mortgage_payment_annual=mortgage_annual,
                pre_tax_cashflow=pre_tax_cf.quantize(Decimal("0.01")),
                after_tax_cashflow=after_tax_cf.quantize(Decimal("0.01")),
                loan_balance=loan_bal,
                property_value=prop_value,
                equity=equity.quantize(Decimal("0.01")),
                cumulative_cashflow=cumulative_cf.quantize(Decimal("0.01")),
            )
        )

    # --- Exit analysis ---
    final_value = projections[-1].property_value
    selling_costs = (final_value * to_decimal(selling_costs_pct)).quantize(
        Decimal("0.01")
    )
    loan_payoff = projections[-1].loan_balance
    net_before_tax = final_value - selling_costs - loan_payoff

    # Capital gains tax (simplified: 20 % long-term rate on appreciation)
    total_appreciation = final_value - pp
    cap_gains_tax = (
        (total_appreciation * Decimal("0.20")).quantize(Decimal("0.01"))
        if total_appreciation > 0
        else Decimal("0")
    )
    net_after_tax = net_before_tax - cap_gains_tax

    total_return = net_after_tax + cumulative_cf - initial_investment

    # --- IRR ---
    cashflows = [-initial_investment]
    for i, proj in enumerate(projections):
        cf = proj.after_tax_cashflow
        if i == len(projections) - 1:
            cf += net_after_tax  # add exit proceeds to final year
        cashflows.append(cf)

    cf_array = np.array([float(c) for c in cashflows], dtype=float)
    try:
        irr_value = float(npf.irr(cf_array))
        if np.isnan(irr_value) or np.isinf(irr_value):
            annualized_irr = Decimal("0")
        else:
            annualized_irr = to_decimal(irr_value)
    except Exception:
        logger.warning("IRR computation failed; returning 0", exc_info=True)
        annualized_irr = Decimal("0")

    exit_analysis = ExitAnalysis(
        gross_sale_price=final_value,
        selling_costs=selling_costs,
        loan_payoff=loan_payoff,
        net_proceeds_before_tax=net_before_tax.quantize(Decimal("0.01")),
        estimated_capital_gains_tax=cap_gains_tax,
        net_proceeds_after_tax=net_after_tax.quantize(Decimal("0.01")),
        total_return=total_return.quantize(Decimal("0.01")),
        annualized_irr=annualized_irr.quantize(Decimal("0.0001")),
    )

    return projections, exit_analysis
