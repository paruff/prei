from datetime import date
from decimal import Decimal
from typing import Dict, List

from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import TruncMonth

from core.models import MonthlyActuals, OperatingExpense, Property, RentalIncome
from investor_app.finance.utils import (
    compute_analysis_for_property,
    to_decimal,
)

MONTHS_PER_YEAR = Decimal("12")
DAYS_PER_MONTH = Decimal("30")


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


def compute_portfolio_summary(user: User) -> Dict[str, Decimal | int]:
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
    # MONTHS_PER_YEAR is constant 12, so divide-by-zero is not possible.
    # This metric follows issue acceptance criteria: monthly value derived from NOI.
    total_monthly_cash_flow = total_annual_noi_decimal / MONTHS_PER_YEAR

    return {
        "total_properties": total_properties,
        "total_capital_invested": total_capital_invested_decimal,
        "total_annual_noi": total_annual_noi_decimal,
        "weighted_average_cap_rate": weighted_average_cap_rate,
        "total_monthly_cash_flow": total_monthly_cash_flow,
    }


# ---------------------------------------------------------------------------
# Variance Analysis (ISSUE 4-A)
# ---------------------------------------------------------------------------


def _safe_decimal(value) -> Decimal:
    """Convert a value to Decimal, returning Decimal('0') for None."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def calculate_coc_variance(
    actual_rent: Decimal,
    actual_vacancy_days: int,
    actual_expenses: Decimal,
    actual_maintenance: Decimal,
    underwritten_coc: Decimal,
    annual_debt_service: Decimal,
    total_invested: Decimal,
) -> Decimal:
    """Calculate variance between actual and underwritten cash-on-cash return.

    Variance = actual CoC - underwritten CoC (positive = better than expected).

    Args:
        actual_rent: Actual rent collected for the month.
        actual_vacancy_days: Number of vacant days in the month.
        actual_expenses: Actual operating expenses for the month.
        actual_maintenance: Actual maintenance costs for the month.
        underwritten_coc: Underwritten annual cash-on-cash as a fraction.
        annual_debt_service: Annual mortgage payment.
        total_invested: Total capital invested (down payment + closing + rehab).

    Returns:
        Variance as a decimal fraction (e.g., 0.02 means 2% better than expected).
    """
    if total_invested == Decimal("0"):
        return Decimal("0")

    # Calculate actual monthly NOI
    vacancy_loss = actual_rent * Decimal(str(actual_vacancy_days)) / DAYS_PER_MONTH
    effective_rent = actual_rent - vacancy_loss
    monthly_noi = effective_rent - actual_expenses - actual_maintenance

    # Annualize and subtract debt service
    annual_noi = monthly_noi * MONTHS_PER_YEAR
    actual_annual_cashflow = annual_noi - annual_debt_service

    # Actual CoC
    actual_coc = actual_annual_cashflow / total_invested

    # Variance (positive = better than expected)
    return (actual_coc - underwritten_coc).quantize(Decimal("0.0001"))


def calculate_vacancy_variance(
    actual_vacancy_days: int,
    underwritten_vacancy_rate: Decimal,
) -> Decimal:
    """Calculate variance between actual and underwritten vacancy rate.

    Variance = underwritten vacancy - actual vacancy (positive = better).

    Args:
        actual_vacancy_days: Number of vacant days in the month.
        underwritten_vacancy_rate: Underwritten vacancy as a fraction.

    Returns:
        Variance as a decimal fraction.
    """
    actual_vacancy_rate = Decimal(str(actual_vacancy_days)) / DAYS_PER_MONTH
    return (underwritten_vacancy_rate - actual_vacancy_rate).quantize(Decimal("0.0001"))


def calculate_expense_variance(
    actual_expenses: Decimal,
    actual_maintenance: Decimal,
    underwritten_monthly_expenses: Decimal,
) -> Decimal:
    """Calculate variance between actual and underwritten expenses.

    Variance = budgeted - actual (positive = under budget).

    Args:
        actual_expenses: Actual operating expenses for the month.
        actual_maintenance: Actual maintenance costs for the month.
        underwritten_monthly_expenses: Underwritten monthly expenses.

    Returns:
        Variance as a decimal amount.
    """
    total_actual = actual_expenses + actual_maintenance
    return (underwritten_monthly_expenses - total_actual).quantize(Decimal("0.01"))


def calculate_ytd_cashflow(
    property_obj: Property,
    year: int,
) -> Dict[str, Decimal]:
    """Calculate year-to-date cashflow for a property.

    Args:
        property_obj: Property instance.
        year: Year to calculate for (e.g., 2026).

    Returns:
        Dict with 'ytd_actual', 'ytd_projected', 'variance' keys.
    """
    # Get all actuals for this property and year
    actuals = MonthlyActuals.objects.filter(
        prop=property_obj,
        month__year=year,
    ).order_by("month")

    # Get underwritten analysis
    analysis = getattr(property_obj, "analysis", None)
    monthly_projected_noi = (
        Decimal(str(analysis.noi)) / MONTHS_PER_YEAR if analysis else Decimal("0")
    )
    monthly_debt_service = _get_annual_debt_service(property_obj) / MONTHS_PER_YEAR
    monthly_projected_cashflow = monthly_projected_noi - monthly_debt_service

    ytd_actual = Decimal("0")
    ytd_projected = Decimal("0")
    months_counted = 0

    for actual in actuals:
        ytd_actual += actual.actual_noi
        months_counted += 1

    ytd_projected = monthly_projected_cashflow * Decimal(str(months_counted))

    return {
        "ytd_actual": ytd_actual.quantize(Decimal("0.01")),
        "ytd_projected": ytd_projected.quantize(Decimal("0.01")),
        "variance": (ytd_actual - ytd_projected).quantize(Decimal("0.01")),
    }


def _get_annual_debt_service(property_obj: Property) -> Decimal:
    """Calculate annual debt service for a property."""
    from investor_app.finance.utils import calculate_monthly_mortgage, to_decimal

    loan_amount = to_decimal(property_obj.purchase_price) * (
        Decimal("1") - to_decimal(property_obj.down_payment_pct)
    )
    # convert fraction rate to percentage for calculate_monthly_mortgage
    rate_pct = to_decimal(property_obj.interest_rate) * Decimal("100")
    monthly_pmt = calculate_monthly_mortgage(
        loan_amount,
        rate_pct,
        property_obj.loan_term_years,
    )
    return monthly_pmt * MONTHS_PER_YEAR


def check_flag_for_attention(
    property_obj: Property, consecutive_months: int = 2
) -> bool:
    """Check if a property should be flagged for attention.

    Flag if actual CoC is more than 20% below underwritten CoC for consecutive months.

    Args:
        property_obj: Property instance.
        consecutive_months: Number of consecutive months to check (default 2).

    Returns:
        True if property should be flagged.
    """
    analysis = getattr(property_obj, "analysis", None)
    if not analysis:
        return False

    underwritten_coc = Decimal(str(analysis.cash_on_cash))
    if underwritten_coc == Decimal("0"):
        return False

    # Get recent actuals ordered by month descending
    recent_actuals = MonthlyActuals.objects.filter(
        prop=property_obj,
    ).order_by(
        "-month"
    )[:consecutive_months]

    if len(recent_actuals) < consecutive_months:
        return False

    total_invested = Decimal(str(property_obj.purchase_price))
    annual_debt_service = _get_annual_debt_service(property_obj)

    for actual in recent_actuals:
        variance = calculate_coc_variance(
            actual_rent=actual.actual_rent_collected,
            actual_vacancy_days=actual.actual_vacancy_days,
            actual_expenses=actual.actual_expenses,
            actual_maintenance=actual.actual_maintenance,
            underwritten_coc=underwritten_coc,
            annual_debt_service=annual_debt_service,
            total_invested=total_invested,
        )
        # If variance is less than -20% of underwritten, it's flagged
        threshold = underwritten_coc * Decimal("-0.20")
        if variance >= threshold:
            return False

    return True


def compute_portfolio_performance(user: User) -> Dict[str, object]:
    """Compute portfolio-wide performance metrics including variance analysis.

    Args:
        user: Django User instance.

    Returns:
        Dict with portfolio metrics, property details, and flagged properties.
    """
    properties = Property.objects.filter(user=user).select_related("analysis")

    property_details = []
    total_monthly_cashflow = Decimal("0")
    total_equity = Decimal("0")
    best_property = None
    worst_property = None
    flagged_properties = []

    for prop in properties:
        analysis = getattr(prop, "analysis", None)

        # Get latest actuals
        latest_actual = (
            MonthlyActuals.objects.filter(
                prop=prop,
            )
            .order_by("-month")
            .first()
        )

        # Calculate underwritten monthly values
        underwritten_monthly_noi = (
            Decimal(str(analysis.noi)) / MONTHS_PER_YEAR if analysis else Decimal("0")
        )
        annual_debt_service = _get_annual_debt_service(prop)
        underwritten_monthly_cashflow = (
            underwritten_monthly_noi - annual_debt_service / MONTHS_PER_YEAR
        )

        # Calculate variance if we have actuals
        coc_variance = Decimal("0")
        vacancy_variance = Decimal("0")
        expense_variance = Decimal("0")
        actual_monthly_noi = Decimal("0")

        if latest_actual:
            underwritten_coc = (
                Decimal(str(analysis.cash_on_cash)) if analysis else Decimal("0")
            )
            coc_variance = calculate_coc_variance(
                actual_rent=latest_actual.actual_rent_collected,
                actual_vacancy_days=latest_actual.actual_vacancy_days,
                actual_expenses=latest_actual.actual_expenses,
                actual_maintenance=latest_actual.actual_maintenance,
                underwritten_coc=underwritten_coc,
                annual_debt_service=annual_debt_service,
                total_invested=Decimal(str(prop.purchase_price)),
            )
            vacancy_variance = calculate_vacancy_variance(
                actual_vacancy_days=latest_actual.actual_vacancy_days,
                underwritten_vacancy_rate=prop.vacancy_rate,
            )
            expense_variance = calculate_expense_variance(
                actual_expenses=latest_actual.actual_expenses,
                actual_maintenance=latest_actual.actual_maintenance,
                underwritten_monthly_expenses=(
                    underwritten_monthly_noi + annual_debt_service / MONTHS_PER_YEAR
                    if analysis
                    else Decimal("0")
                ),
            )
            actual_monthly_noi = latest_actual.actual_noi

        # YTD cashflow
        ytd = calculate_ytd_cashflow(prop, date.today().year)

        total_monthly_cashflow += underwritten_monthly_cashflow
        total_equity += Decimal(str(prop.purchase_price)) * Decimal(
            "0.7"
        )  # Estimate 30% equity

        prop_detail = {
            "property": prop,
            "analysis": analysis,
            "latest_actual": latest_actual,
            "coc_variance": coc_variance,
            "vacancy_variance": vacancy_variance,
            "expense_variance": expense_variance,
            "actual_monthly_noi": actual_monthly_noi,
            "ytd": ytd,
        }
        property_details.append(prop_detail)

        # Track best/worst (by CoC variance)
        if latest_actual:
            if best_property is None or coc_variance > best_property["coc_variance"]:
                best_property = prop_detail
            if worst_property is None or coc_variance < worst_property["coc_variance"]:
                worst_property = prop_detail

        # Check for attention flag
        if check_flag_for_attention(prop):
            flagged_properties.append(prop)

    return {
        "property_details": property_details,
        "total_monthly_cashflow": total_monthly_cashflow.quantize(Decimal("0.01")),
        "total_equity": total_equity.quantize(Decimal("0.01")),
        "best_property": best_property,
        "worst_property": worst_property,
        "flagged_properties": flagged_properties,
    }
