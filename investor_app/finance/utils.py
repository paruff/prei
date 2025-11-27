"""Finance utility functions for real estate investment analysis.

All functions use Decimal for precision in financial calculations.
Functions that require numpy_financial convert to float internally.
"""

from decimal import Decimal
from typing import List

import numpy_financial as npf


def calculate_noi(
    gross_income: Decimal,
    operating_expenses: Decimal
) -> Decimal:
    """Calculate Net Operating Income (NOI).

    NOI = Gross Income - Operating Expenses

    Args:
        gross_income: Total rental and other income from the property.
        operating_expenses: Total operating expenses (excluding debt service).

    Returns:
        Net Operating Income as a Decimal.
    """
    return gross_income - operating_expenses


def calculate_cap_rate(
    noi: Decimal,
    property_value: Decimal
) -> Decimal:
    """Calculate Capitalization Rate.

    Cap Rate = NOI / Property Value

    Args:
        noi: Net Operating Income.
        property_value: Current market value or purchase price of the property.

    Returns:
        Capitalization rate as a Decimal (e.g., 0.08 for 8%).

    Raises:
        ValueError: If property_value is zero.
    """
    if property_value == Decimal("0"):
        raise ValueError("Property value cannot be zero")
    return noi / property_value


def calculate_cash_on_cash(
    annual_cash_flow: Decimal,
    total_cash_invested: Decimal
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
    if total_cash_invested == Decimal("0"):
        raise ValueError("Total cash invested cannot be zero")
    return annual_cash_flow / total_cash_invested


def calculate_irr(cash_flows: List[Decimal]) -> Decimal:
    """Calculate Internal Rate of Return (IRR).

    Args:
        cash_flows: List of cash flows, starting with initial investment
                   (typically negative) followed by periodic returns.

    Returns:
        IRR as a Decimal (e.g., 0.15 for 15%).

    Raises:
        ValueError: If cash_flows has fewer than 2 elements or IRR cannot be computed.
    """
    if len(cash_flows) < 2:
        raise ValueError("At least 2 cash flows are required to calculate IRR")

    # Convert Decimal to float for numpy_financial
    float_cash_flows = [float(cf) for cf in cash_flows]

    irr_result = npf.irr(float_cash_flows)

    # Handle case where IRR cannot be computed (returns nan)
    if irr_result != irr_result:  # nan check
        raise ValueError("IRR could not be computed for the given cash flows")

    return Decimal(str(irr_result))
