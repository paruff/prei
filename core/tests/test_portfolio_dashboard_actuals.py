from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import MonthlyActuals, PipelineProperty, Property


@pytest.mark.django_db
def test_dashboard_shows_latest_monthly_actuals(client):
    user = get_user_model().objects.create_user("owner", password="x")  # noqa: S106
    prop = Property.objects.create(
        user=user,
        address="9 Actuals Way",
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
    PipelineProperty.objects.create(
        user=user,
        address=prop.address,
        address_hash="h",
        status=PipelineProperty.Status.ACQUIRED,
        stage="ACQUIRED",
        property_record=prop,
    )
    MonthlyActuals.objects.create(
        prop=prop, month=date(2026, 9, 1), actual_rent_collected=Decimal("1400")
    )
    MonthlyActuals.objects.create(
        prop=prop, month=date(2026, 10, 1), actual_rent_collected=Decimal("1500")
    )
    client.force_login(user)

    html = client.get(reverse("portfolio_dashboard")).content.decode()

    assert "$1,500 (Oct 2026)" in html
