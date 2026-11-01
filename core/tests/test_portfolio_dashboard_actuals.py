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


def _owner_with_property(client):
    user = get_user_model().objects.create_user("poster", password="x")  # noqa: S106
    prop = Property.objects.create(
        user=user,
        address="1 Post St",
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
    client.force_login(user)
    return prop


def _post(client, prop, **extra):
    data = {
        "property_id": prop.pk,
        "month": "2026-10-15",
        "actual_rent_collected": "1500.00",
        "actual_vacancy_days": "0",
        "actual_expenses": "300.00",
        "actual_maintenance": "50.00",
        **extra,
    }
    return client.post(reverse("portfolio_actuals_add"), data, follow=True)


@pytest.mark.django_db
def test_mid_month_post_updates_existing_row(client):
    prop = _owner_with_property(client)
    MonthlyActuals.objects.create(prop=prop, month=date(2026, 10, 1))
    _post(client, prop)
    rows = MonthlyActuals.objects.filter(prop=prop)
    assert rows.count() == 1
    assert rows.get().actual_rent_collected == Decimal("1500.00")


@pytest.mark.django_db
def test_resubmitting_month_keeps_notes(client):
    prop = _owner_with_property(client)
    MonthlyActuals.objects.create(prop=prop, month=date(2026, 10, 1), notes="roof leak")
    _post(client, prop)
    assert MonthlyActuals.objects.get(prop=prop).notes == "roof leak"


@pytest.mark.django_db
def test_explicit_notes_replace_and_empty_notes_clear(client):
    prop = _owner_with_property(client)
    MonthlyActuals.objects.create(prop=prop, month=date(2026, 10, 1), notes="roof leak")
    _post(client, prop, notes="new tenant")
    assert MonthlyActuals.objects.get(prop=prop).notes == "new tenant"
    _post(client, prop, notes="")
    assert MonthlyActuals.objects.get(prop=prop).notes == ""


@pytest.mark.django_db
def test_error_flash_names_the_field(client):
    prop = _owner_with_property(client)
    response = _post(client, prop, actual_rent_collected="")
    flashes = [str(m) for m in response.context["messages"]]
    assert any("Actual rent collected: This field is required." in m for m in flashes)
