from datetime import date
from decimal import Decimal
from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

from core.models import MonthlyActuals, Property

migration = import_module("core.migrations.0054_normalise_monthly_actuals_month")


@pytest.mark.django_db
def test_mid_month_rows_move_to_the_first_and_newest_wins(caplog):
    user = get_user_model().objects.create_user("m", password="x")  # noqa: S106
    prop = Property.objects.create(
        user=user,
        address="1 Main St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        purchase_price=Decimal("100000"),
        purchase_date=date(2026, 1, 1),
        bedrooms=3,
        sqft=1200,
        property_type="SFR",
        monthly_rent_gross=Decimal("1500"),
    )
    other = date(2026, 9, 1)
    MonthlyActuals.objects.create(prop=prop, month=other)
    MonthlyActuals.objects.create(prop=prop, month=date(2026, 10, 1), notes="old")
    MonthlyActuals.objects.create(prop=prop, month=date(2026, 10, 15), notes="new")
    migration.month_to_first(apps, None)
    assert "dropping" in caplog.text and "-> 2026-10-01" in caplog.text
    rows = {r.month: r.notes for r in MonthlyActuals.objects.filter(prop=prop)}
    assert rows == {other: "", date(2026, 10, 1): "new"}
