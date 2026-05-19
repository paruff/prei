from decimal import Decimal

from django.contrib import admin
from django.db import connection
from django.db import models
from django.utils import timezone

from core.admin import VrmPropertyAdmin
from core.models import VrmProperty


def test_rental_income_fixture_effective_gross_income(rental_income_sfr):
    assert rental_income_sfr.effective_gross_income() == Decimal("2280.000000")


def test_operating_expense_fixtures_monthly_amounts(
    expense_property_tax_annual,
    expense_maintenance_monthly,
):
    assert expense_property_tax_annual.monthly_amount() == Decimal("325.00")
    assert expense_maintenance_monthly.monthly_amount() == Decimal("200.00")


def test_analysis_with_financing_fixture_has_stress_metrics(analysis_with_financing):
    assert analysis_with_financing.cash_on_cash < Decimal("0")
    assert analysis_with_financing.dscr < Decimal("1.0000")


def test_full_sfr_composite_fixture(full_sfr):
    assert set(full_sfr.keys()) == {"property", "rental_income", "expenses", "analysis"}
    assert len(full_sfr["expenses"]) == 5
    assert full_sfr["analysis"].property == full_sfr["property"]


def test_portfolio_fixture_bundles_expected_properties(portfolio):
    assert len(portfolio["primary_user_properties"]) == 3
    assert portfolio["other_user_property"] not in portfolio["primary_user_properties"]


def test_vrm_property_model_fields_and_constraints(db):
    field_expectations = {
        "vrm_property_id": (models.IntegerField, False, None),
        "vrm_listing_url": (models.URLField, False, None),
        "address": (models.CharField, False, None),
        "city": (models.CharField, False, None),
        "state": (models.CharField, False, 2),
        "zip_code": (models.CharField, False, None),
        "county": (models.CharField, True, None),
        "list_price": (models.DecimalField, True, None),
        "bedrooms": (models.IntegerField, True, None),
        "bathrooms": (models.DecimalField, True, None),
        "square_feet": (models.IntegerField, True, None),
        "lot_size_sf": (models.IntegerField, True, None),
        "year_built": (models.IntegerField, True, None),
        "property_type": (models.CharField, True, None),
        "status": (models.CharField, False, None),
        "listing_type": (models.CharField, True, None),
        "vendee_eligible": (models.BooleanField, False, None),
        "occupied": (models.BooleanField, True, None),
        "latitude": (models.DecimalField, True, None),
        "longitude": (models.DecimalField, True, None),
        "mls_id": (models.CharField, True, None),
        "parcel_number": (models.CharField, True, None),
        "days_on_site": (models.IntegerField, True, None),
        "scraped_at": (models.DateTimeField, False, None),
        "last_seen_at": (models.DateTimeField, False, None),
    }

    for field_name, (field_type, nullable, max_length) in field_expectations.items():
        field = VrmProperty._meta.get_field(field_name)
        assert isinstance(field, field_type)
        assert field.null is nullable
        if max_length is not None:
            assert field.max_length == max_length

    assert VrmProperty._meta.db_table == "vrm_property"
    assert VrmProperty._meta.get_field("vrm_property_id").unique is True


def test_vrm_property_model_schema_and_admin_registration(db):
    table_names = set(connection.introspection.table_names())
    assert "vrm_property" in table_names

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "vrm_property")
    assert any(
        details["unique"] and details["columns"] == ["vrm_property_id"]
        for details in constraints.values()
    )

    registered_admin = admin.site._registry[VrmProperty]
    assert isinstance(registered_admin, VrmPropertyAdmin)
    assert registered_admin.list_filter == ("state", "status", "vendee_eligible")


def test_vrm_property_str_representation(db):
    vrm_property = VrmProperty.objects.create(
        vrm_property_id=101,
        vrm_listing_url="https://www.vrmproperties.com/properties/101",
        address="369 Charles St",
        city="Winchester",
        state="VA",
        zip_code="22601",
        status=VrmProperty.Status.FOR_SALE,
        vendee_eligible=True,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
        list_price=Decimal("250000.00"),
    )

    assert str(vrm_property) == "369 Charles St, Winchester, VA"
