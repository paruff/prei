"""
Finance helper utilities for property investment KPIs.

Centralize financial calculations here so they are easy to test and review.
Use Decimal for currency precision when interfacing with persistent storage.
Convert to float only when calling numpy-financial functions which require floats.
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Iterable, List

import numpy_financial as nf

# Increase precision to avoid rounding surprises during intermediate calculations
getcontext().prec = 28

Currency = Decimal


def _to_decimal(value: float | str | Decimal) -> Decimal:
    """Convert common numeric types to Decimal safely."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_currency(value: Decimal, places: int = 2) -> Decimal:
    """Round Decimal to currency places (default 2)."""
    quant = Decimal("0." + "0" * (places - 1) + "1") if places > 0 else Decimal("1")
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def calculate_noi(
    gross_annual_income: Currency, operating_expenses: Currency
) -> Currency:
    """
    Net Operating Income = Gross Annual Income - Operating Expenses
    """
    gross = _to_decimal(gross_annual_income)
    ops = _to_decimal(operating_expenses)
    noi = gross - ops
    return quantize_currency(noi)


def calculate_cap_rate(noi: Currency, purchase_price: Currency) -> Decimal:
    """
    Cap Rate = NOI / Purchase Price
    Returns a Decimal representing the rate (e.g., 0.05 for 5%).
    """
    noi_d = _to_decimal(noi)
    price_d = _to_decimal(purchase_price)
    if price_d == 0:
        raise ZeroDivisionError(
            "purchase_price must be non-zero for cap rate calculation"
        )
    rate = noi_d / price_d
    # Return Decimal without converting to percentage
    return rate.quantize(Decimal("0.0001"))


def calculate_cash_on_cash(
    annual_cash_flow: Currency, total_cash_invested: Currency
) -> Decimal:
    """
    Cash-on-Cash Return = Annual Cash Flow / Total Cash Invested
    """
    flow = _to_decimal(annual_cash_flow)
    invested = _to_decimal(total_cash_invested)
    if invested == 0:
        raise ZeroDivisionError(
            "total_cash_invested must be non-zero for cash-on-cash calculation"
        )
    return (flow / invested).quantize(Decimal("0.0001"))


def calculate_irr(cashflows: Iterable[float | Decimal | str]) -> Decimal:
    """
    Internal Rate of Return for a series of cashflows.
    cashflows: Iterable where the first element is negative (initial investment), followed by net incomes.
    Returns Decimal rate (e.g., 0.12 for 12%).
    """
    # Convert to floats for numpy_financial, preserve Decimal precision for final conversion
    floats: List[float] = [float(_to_decimal(x)) for x in cashflows]
    rate = nf.irr(floats)
    if rate is None:
        # numpy_financial returns nan under some inputs; raise for explicit handling upstream
        raise ValueError("IRR could not be calculated for the provided cashflows")
    # Convert back to Decimal with reasonable precision
    return Decimal(str(rate)).quantize(Decimal("0.0001"))


def npv(rate: float, cashflows: Iterable[float | Decimal | str]) -> Decimal:
    """
    Net Present Value at a given discount rate.
    rate expressed as decimal (e.g., 0.08 for 8%)
    """
    floats: List[float] = [float(_to_decimal(x)) for x in cashflows]
    val = nf.npv(rate, floats)
    return Decimal(str(val)).quantize(Decimal("0.01"))
