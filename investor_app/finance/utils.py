"""Financial utility functions for real estate investment analysis.

This module provides core financial calculations for analyzing real estate
investments, including NOI, Cap Rate, Cash-on-Cash returns, and IRR.
"""

from decimal import Decimal
from typing import Sequence

import numpy_financial as npf


def calculate_noi(gross_income: Decimal, operating_expenses: Decimal) -> Decimal:
    """Calculate Net Operating Income (NOI).

    Args:
        gross_income: Total rental income before expenses.
        operating_expenses: Total operating expenses (excluding debt service).

    Returns:
        Net Operating Income as a Decimal.
    """
    return gross_income - operating_expenses


def calculate_cap_rate(noi: Decimal, purchase_price: Decimal) -> Decimal:
    """Calculate Capitalization Rate (Cap Rate).

    Args:
        noi: Net Operating Income.
        purchase_price: Property purchase price or market value.

    Returns:
        Cap Rate as a Decimal (e.g., 0.06 for 6%).

    Raises:
        ValueError: If purchase_price is zero.
    """
    if purchase_price == Decimal("0"):
        raise ValueError("Purchase price cannot be zero")
    result = noi / purchase_price
    return result.quantize(Decimal("0.0001"))


def calculate_cash_on_cash(
    annual_cash_flow: Decimal, cash_invested: Decimal
) -> Decimal:
    """Calculate Cash-on-Cash Return.

    Args:
        annual_cash_flow: Annual pre-tax cash flow from the investment.
        cash_invested: Total cash invested (down payment, closing costs, etc.).

    Returns:
        Cash-on-Cash return as a Decimal (e.g., 0.15 for 15%).

    Raises:
        ValueError: If cash_invested is zero.
    """
    if cash_invested == Decimal("0"):
        raise ValueError("Cash invested cannot be zero")
    result = annual_cash_flow / cash_invested
    return result.quantize(Decimal("0.0001"))


def calculate_irr(cash_flows: Sequence[float]) -> Decimal:
    """Calculate Internal Rate of Return (IRR).

    Args:
        cash_flows: Sequence of cash flows. The first value is typically
            negative (initial investment), followed by periodic returns.

    Returns:
        IRR as a Decimal.

    Raises:
        ValueError: If IRR cannot be computed (e.g., all zeros or no solution).
    """
    # Check for all zeros case
    if all(cf == 0 for cf in cash_flows):
        raise ValueError("Cannot calculate IRR for all-zero cash flows")

    irr_result = npf.irr(cash_flows)

    # npf.irr returns nan if no solution found
    if irr_result != irr_result:  # NaN check
        raise ValueError("Cannot calculate IRR: no solution found")

    return Decimal(str(irr_result)).quantize(Decimal("0.0001"))
