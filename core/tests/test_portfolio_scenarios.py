"""Tests for monthly_income_series and portfolio_trend_summary (Phase 2.5)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from core.models import OperatingExpense, Property, RentalIncome
from core.services.portfolio import monthly_income_series, portfolio_trend_summary

User = get_user_model()


def _make_property(user, purchase_price: str = "120000") -> Property:
    return Property.objects.create(
        user=user,
        address="1 Test St",
        city="Testville",
        state="TX",
        zip_code="00000",
        purchase_price=Decimal(purchase_price),
    )


def _first_of_month(offset: int = 0) -> date:
    """Return the first day of the month ``offset`` months before today."""
    today = date.today()
    total = today.year * 12 + today.month - 1 - offset
    y, m = divmod(total, 12)
    return date(y, m + 1, 1)


@pytest.mark.django_db
def test_monthly_series_correct_labels_and_totals(user):
    """12 months of rental income → correct YYYY-MM labels and summed income."""
    prop = _make_property(user)

    # Create one RentalIncome record per month for the past 12 months.
    for offset in range(12):
        effective = _first_of_month(offset)
        RentalIncome.objects.create(
            property=prop,
            monthly_rent=Decimal("1000"),
            effective_date=effective,
            vacancy_rate=Decimal("0.00"),
        )

    series = monthly_income_series(user, months=12)

    assert len(series) == 12
    # All months should be present and have the expected income.
    for row in series:
        assert "month" in row
        # Each month should have exactly one RI record contributing $1 000.
        assert row["gross_income"] == Decimal("1000")
        assert row["noi"] == Decimal("1000")

    # Labels should be in ascending order and formatted as YYYY-MM.
    labels = [row["month"] for row in series]
    assert labels == sorted(labels)
    for label in labels:
        year_part, month_part = label.split("-")
        assert len(year_part) == 4
        assert 1 <= int(month_part) <= 12


@pytest.mark.django_db
def test_monthly_series_no_properties_returns_empty(user):
    """User with no properties should return an empty list without error."""
    result = monthly_income_series(user)
    assert result == []


@pytest.mark.django_db
def test_trend_summary_single_month_returns_zero(user):
    """portfolio_trend_summary with a single data point must not divide by zero."""
    prop = _make_property(user)
    RentalIncome.objects.create(
        property=prop,
        monthly_rent=Decimal("2000"),
        effective_date=_first_of_month(0),
        vacancy_rate=Decimal("0.00"),
    )

    # With months=1 the series has exactly one entry; trend must be zero.
    series = monthly_income_series(user, months=1)
    assert len(series) == 1

    result = portfolio_trend_summary(user)
    # Whether the series has 1 non-zero entry or all others are zero, the
    # oldest month's value is zero (months 2-12 are zero), so no division
    # by zero and trend equals Decimal("0").
    assert isinstance(result["trend_noi"], Decimal)
    assert isinstance(result["trend_cap_rate"], Decimal)
    # oldest noi == 0 → guard returns zero
    assert result["trend_noi"] == Decimal("0")
    assert result["trend_cap_rate"] == Decimal("0")


@pytest.mark.django_db
def test_annual_expense_prorated_monthly(user):
    """OperatingExpense with frequency='annual' is divided by 12 in each month."""
    prop = _make_property(user)
    effective = _first_of_month(0)

    RentalIncome.objects.create(
        property=prop,
        monthly_rent=Decimal("2400"),
        effective_date=effective,
        vacancy_rate=Decimal("0.00"),
    )
    # Annual expense of $1200 should contribute $100/month.
    OperatingExpense.objects.create(
        property=prop,
        category="Insurance",
        amount=Decimal("1200"),
        frequency=OperatingExpense.Frequency.ANNUAL,
        effective_date=effective,
    )

    series = monthly_income_series(user, months=1)
    assert len(series) == 1
    row = series[0]

    assert row["gross_income"] == Decimal("2400")
    assert row["expenses"] == Decimal("100")  # 1200 / 12
    assert row["noi"] == Decimal("2300")
