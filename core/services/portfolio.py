from datetime import date
from decimal import Decimal
from typing import Dict, List

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from core.models import OperatingExpense, Property, RentalIncome
from investor_app.finance.utils import (
    compute_analysis_for_property,
    to_decimal,
)

MONTHS_PER_YEAR = Decimal("12")


def _month_starts(base: date, count: int) -> List[date]:
    """Return ``count`` first-of-month dates ending at ``base``'s month, oldest first."""
    months = []
    total = base.year * 12 + base.month - 1
    for offset in range(count - 1, -1, -1):
        t = total - offset
        y, m = divmod(t, 12)
        months.append(date(y, m + 1, 1))
    return months


def monthly_income_series(user, months: int = 12) -> List[Dict[str, object]]:
    """Return monthly income/expense/NOI for the last ``months`` calendar months.

    Args:
        user: Django User instance.
        months: Number of trailing calendar months to include (default 12).

    Returns:
        List of dicts ``{"month": "YYYY-MM", "gross_income": Decimal,
        "expenses": Decimal, "noi": Decimal}``, oldest first.
        Returns an empty list when the user has no properties.
    """
    if months < 1:
        raise ValueError("months must be a positive integer")

    prop_ids = list(Property.objects.filter(user=user).values_list("id", flat=True))
    if not prop_ids:
        return []

    today = date.today()
    month_list = _month_starts(today, months)
    range_start = month_list[0]

    # Annotate each record with its truncated month for grouping in Python.
    rental_incomes = (
        RentalIncome.objects.filter(
            property_id__in=prop_ids,
            effective_date__gte=range_start,
            effective_date__lte=today,
        )
        .annotate(trunc_month=TruncMonth("effective_date"))
        .order_by("trunc_month")
    )

    operating_expenses = (
        OperatingExpense.objects.filter(
            property_id__in=prop_ids,
            effective_date__gte=range_start,
            effective_date__lte=today,
        )
        .annotate(trunc_month=TruncMonth("effective_date"))
        .order_by("trunc_month")
    )

    # Group income by "YYYY-MM" month key.
    income_by_month: Dict[str, Decimal] = {}
    for ri in rental_incomes:
        key: str = ri.trunc_month.strftime("%Y-%m")
        income_by_month[key] = (
            income_by_month.get(key, Decimal("0")) + ri.effective_gross_income()
        )

    # Group expenses by "YYYY-MM" month key; monthly_amount() handles frequency proration.
    expense_by_month: Dict[str, Decimal] = {}
    for oe in operating_expenses:
        key = oe.trunc_month.strftime("%Y-%m")
        expense_by_month[key] = (
            expense_by_month.get(key, Decimal("0")) + oe.monthly_amount()
        )

    result: List[Dict[str, object]] = []
    for m_start in month_list:
        label = m_start.strftime("%Y-%m")
        gross = income_by_month.get(label, Decimal("0"))
        exp = expense_by_month.get(label, Decimal("0"))
        result.append(
            {
                "month": label,
                "gross_income": gross,
                "expenses": exp,
                "noi": gross - exp,
            }
        )

    return result


def portfolio_trend_summary(user) -> Dict[str, Decimal]:
    """Return percentage change in NOI and cap rate over the 12-month series.

    Args:
        user: Django User instance.

    Returns:
        Dict ``{"trend_noi": Decimal, "trend_cap_rate": Decimal}`` as
        percentage changes from the oldest to the newest month.
        Returns zeroes when there is insufficient data or the oldest
        month has zero values (guards against divide-by-zero).
    """
    series = monthly_income_series(user)

    if len(series) <= 1:
        return {"trend_noi": Decimal("0"), "trend_cap_rate": Decimal("0")}

    oldest_noi: Decimal = series[0]["noi"]  # type: ignore[assignment]
    newest_noi: Decimal = series[-1]["noi"]  # type: ignore[assignment]

    trend_noi = (
        (newest_noi - oldest_noi) / oldest_noi * Decimal("100")
        if oldest_noi != Decimal("0")
        else Decimal("0")
    )

    # Cap-rate trend: annualise monthly NOI and divide by total purchase price.
    total_price = Property.objects.filter(user=user).aggregate(
        total=Sum("purchase_price")
    )["total"] or Decimal("0")
    total_price = Decimal(str(total_price))

    if total_price == Decimal("0"):
        trend_cap_rate = Decimal("0")
    else:
        oldest_cap_rate = oldest_noi * Decimal("12") / total_price
        newest_cap_rate = newest_noi * Decimal("12") / total_price
        trend_cap_rate = (
            (newest_cap_rate - oldest_cap_rate) / oldest_cap_rate * Decimal("100")
            if oldest_cap_rate != Decimal("0")
            else Decimal("0")
        )

    return {
        "trend_noi": trend_noi.quantize(Decimal("0.01")),
        "trend_cap_rate": trend_cap_rate.quantize(Decimal("0.01")),
    }


def aggregate_portfolio(user) -> Dict[str, Decimal]:
    """Aggregate KPIs across a user's properties.

    Returns totals/averages for NOI, cap rate, cash-on-cash.
    """
    props = Property.objects.filter(user=user)
    total_noi = Decimal("0")
    cap_rates = []
    cocs = []
    for p in props:
        analysis = compute_analysis_for_property(p)
        total_noi += to_decimal(analysis.noi)
        cap_rates.append(to_decimal(analysis.cap_rate))
        cocs.append(to_decimal(analysis.cash_on_cash))

    avg_cap_rate = (
        sum(cap_rates, Decimal("0")) / Decimal(len(cap_rates))
        if cap_rates
        else Decimal("0")
    )
    avg_coc = sum(cocs, Decimal("0")) / Decimal(len(cocs)) if cocs else Decimal("0")
    return {
        "total_noi": total_noi,
        "avg_cap_rate": avg_cap_rate,
        "avg_coc": avg_coc,
    }


def compute_portfolio_summary(user) -> Dict[str, Decimal | int]:
    """Compute portfolio-level aggregate metrics for dashboard rendering.

    Args:
        user: Django User instance.

    Returns:
        Dict with total property count, total invested capital, total annual NOI,
        weighted average cap rate, and total monthly cash flow.
    """
    properties = Property.objects.filter(user=user)
    total_properties = properties.count()
    total_capital_invested = properties.aggregate(total=Sum("purchase_price"))["total"]
    total_annual_noi = properties.aggregate(total=Sum("analysis__noi"))["total"]

    total_capital_invested_decimal = to_decimal(total_capital_invested or Decimal("0"))
    total_annual_noi_decimal = to_decimal(total_annual_noi or Decimal("0"))

    weighted_average_cap_rate = (
        total_annual_noi_decimal / total_capital_invested_decimal
        if total_capital_invested_decimal != Decimal("0")
        else Decimal("0")
    )
    total_monthly_cash_flow = total_annual_noi_decimal / MONTHS_PER_YEAR

    return {
        "total_properties": total_properties,
        "total_capital_invested": total_capital_invested_decimal,
        "total_annual_noi": total_annual_noi_decimal,
        "weighted_average_cap_rate": weighted_average_cap_rate,
        "total_monthly_cash_flow": total_monthly_cash_flow,
    }
