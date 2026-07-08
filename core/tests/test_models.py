from decimal import Decimal
from typing import NamedTuple

from django.contrib import admin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connection, models
from django.utils import timezone

from core.admin import VrmPropertyAdmin
from core.models import (
    CountyForeclosureNotice,
    HudProperty,
    UsdaProperty,
    VrmProperty,
)


class FieldExpectation(NamedTuple):
    field_type: type[models.Field]
    nullable: bool
    max_length: int | None = None


FIELD_EXPECTATIONS = {
    "vrm_property_id": FieldExpectation(models.IntegerField, False),
    "vrm_listing_url": FieldExpectation(models.URLField, False),
    "address": FieldExpectation(models.CharField, False),
    "city": FieldExpectation(models.CharField, False),
    "state": FieldExpectation(models.CharField, False, 2),
    "zip_code": FieldExpectation(models.CharField, False),
    "county": FieldExpectation(models.CharField, True),
    "list_price": FieldExpectation(models.DecimalField, True),
    "projected_monthly_rent": FieldExpectation(models.DecimalField, True),
    "estimated_rehab": FieldExpectation(models.DecimalField, True),
    "gross_annual_rent": FieldExpectation(models.DecimalField, False),
    "effective_gross_rent": FieldExpectation(models.DecimalField, False),
    "annual_expenses": FieldExpectation(models.DecimalField, False),
    "noi": FieldExpectation(models.DecimalField, False),
    "total_investment": FieldExpectation(models.DecimalField, False),
    "cap_rate": FieldExpectation(models.DecimalField, False),
    "profit_margin_pct": FieldExpectation(models.DecimalField, False),
    "meets_profit_target": FieldExpectation(models.BooleanField, False),
    "bedrooms": FieldExpectation(models.IntegerField, True),
    "bathrooms": FieldExpectation(models.DecimalField, True),
    "square_feet": FieldExpectation(models.IntegerField, True),
    "lot_size_sf": FieldExpectation(models.IntegerField, True),
    "year_built": FieldExpectation(models.IntegerField, True),
    "property_type": FieldExpectation(models.CharField, True),
    "status": FieldExpectation(models.CharField, False),
    "listing_type": FieldExpectation(models.CharField, True),
    "vendee_eligible": FieldExpectation(models.BooleanField, False),
    "occupied": FieldExpectation(models.BooleanField, True),
    "latitude": FieldExpectation(models.DecimalField, True),
    "longitude": FieldExpectation(models.DecimalField, True),
    "mls_id": FieldExpectation(models.CharField, True),
    "parcel_number": FieldExpectation(models.CharField, True),
    "days_on_site": FieldExpectation(models.IntegerField, True),
    "scraped_at": FieldExpectation(models.DateTimeField, False),
    "last_seen_at": FieldExpectation(models.DateTimeField, False),
}


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
    for field_name, expectation in FIELD_EXPECTATIONS.items():
        field = VrmProperty._meta.get_field(field_name)
        assert isinstance(field, expectation.field_type)
        assert field.null is expectation.nullable
        if expectation.max_length is not None:
            assert field.max_length == expectation.max_length

    assert VrmProperty._meta.db_table == "vrm_property"
    assert VrmProperty._meta.get_field("vrm_property_id").unique is True
    for field_name in (
        "bedrooms",
        "square_feet",
        "lot_size_sf",
        "days_on_site",
    ):
        field = VrmProperty._meta.get_field(field_name)
        assert any(
            isinstance(validator, MinValueValidator) and validator.limit_value == 0
            for validator in field.validators
        )
    assert any(
        isinstance(validator, MinValueValidator) and validator.limit_value == 1
        for validator in VrmProperty._meta.get_field("year_built").validators
    )
    assert any(
        isinstance(validator, MinValueValidator)
        and validator.limit_value == Decimal("0")
        for validator in VrmProperty._meta.get_field("bathrooms").validators
    )
    latitude_validators = VrmProperty._meta.get_field("latitude").validators
    assert any(
        isinstance(validator, MinValueValidator)
        and validator.limit_value == Decimal("-90")
        for validator in latitude_validators
    )
    assert any(
        isinstance(validator, MaxValueValidator)
        and validator.limit_value == Decimal("90")
        for validator in latitude_validators
    )
    longitude_validators = VrmProperty._meta.get_field("longitude").validators
    assert any(
        isinstance(validator, MinValueValidator)
        and validator.limit_value == Decimal("-180")
        for validator in longitude_validators
    )
    assert any(
        isinstance(validator, MaxValueValidator)
        and validator.limit_value == Decimal("180")
        for validator in longitude_validators
    )


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


# ═══════════════════════════════════════════════════════════════════════
# HudProperty
# ═══════════════════════════════════════════════════════════════════════

HUD_FIELD_EXPECTATIONS: dict[str, FieldExpectation] = {
    "hud_case_number": FieldExpectation(models.CharField, False, 64),
    "address": FieldExpectation(models.CharField, False),
    "city": FieldExpectation(models.CharField, False),
    "state": FieldExpectation(models.CharField, False, 2),
    "zip_code": FieldExpectation(models.CharField, False),
    "county": FieldExpectation(models.CharField, False),
    "list_price": FieldExpectation(models.DecimalField, True),
    "bedrooms": FieldExpectation(models.IntegerField, True),
    "bathrooms": FieldExpectation(models.DecimalField, True),
    "square_feet": FieldExpectation(models.IntegerField, True),
    "property_type": FieldExpectation(models.CharField, False),
    "status": FieldExpectation(models.CharField, False),
    "listing_url": FieldExpectation(models.URLField, False),
    "image_url": FieldExpectation(models.URLField, False),
    "description": FieldExpectation(models.TextField, False),
    "scraped_at": FieldExpectation(models.DateTimeField, False),
    "last_seen_at": FieldExpectation(models.DateTimeField, False),
    "created_at": FieldExpectation(models.DateTimeField, False),
    "updated_at": FieldExpectation(models.DateTimeField, False),
}


def test_hud_property_model_fields():
    """All HudProperty fields match expectations."""
    for field_name, expectation in HUD_FIELD_EXPECTATIONS.items():
        field = HudProperty._meta.get_field(field_name)
        assert isinstance(field, expectation.field_type), (
            f"{field_name}: expected {expectation.field_type.__name__}, "
            f"got {type(field).__name__}"
        )
        assert field.null is expectation.nullable
        if expectation.max_length is not None:
            assert field.max_length == expectation.max_length, (
                f"{field_name}: expected max_length={expectation.max_length}"
            )

    assert HudProperty._meta.get_field("hud_case_number").unique is True
    for currency_field in ("list_price",):
        field = HudProperty._meta.get_field(currency_field)
        assert isinstance(field, models.DecimalField)
        assert any(
            isinstance(v, MinValueValidator) and v.limit_value == Decimal("0")
            for v in field.validators
        )
    for int_field in ("bedrooms", "square_feet"):
        field = HudProperty._meta.get_field(int_field)
        assert any(
            isinstance(v, MinValueValidator) and v.limit_value == 0
            for v in field.validators
        )


def test_hud_property_str_representation():
    """HudProperty string representation includes case number and address."""
    prop = HudProperty(
        hud_case_number="HUD-2026-001",
        address="123 Main St",
        city="Austin",
        state="TX",
        zip_code="78701",
        status=HudProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )
    assert str(prop) == "HUD HUD-2026-001 — 123 Main St, Austin"


# ═══════════════════════════════════════════════════════════════════════
# UsdaProperty
# ═══════════════════════════════════════════════════════════════════════

USDA_FIELD_EXPECTATIONS: dict[str, FieldExpectation] = {
    "usda_case_number": FieldExpectation(models.CharField, False, 64),
    "address": FieldExpectation(models.CharField, False),
    "city": FieldExpectation(models.CharField, False),
    "state": FieldExpectation(models.CharField, False, 2),
    "zip_code": FieldExpectation(models.CharField, False),
    "county": FieldExpectation(models.CharField, False),
    "list_price": FieldExpectation(models.DecimalField, True),
    "bedrooms": FieldExpectation(models.IntegerField, True),
    "bathrooms": FieldExpectation(models.DecimalField, True),
    "square_feet": FieldExpectation(models.IntegerField, True),
    "lot_size_acres": FieldExpectation(models.DecimalField, True),
    "property_type": FieldExpectation(models.CharField, False),
    "status": FieldExpectation(models.CharField, False),
    "listing_url": FieldExpectation(models.URLField, False),
    "description": FieldExpectation(models.TextField, False),
    "scraped_at": FieldExpectation(models.DateTimeField, False),
    "last_seen_at": FieldExpectation(models.DateTimeField, False),
    "created_at": FieldExpectation(models.DateTimeField, False),
    "updated_at": FieldExpectation(models.DateTimeField, False),
}


def test_usda_property_model_fields():
    """All UsdaProperty fields match expectations."""
    for field_name, expectation in USDA_FIELD_EXPECTATIONS.items():
        field = UsdaProperty._meta.get_field(field_name)
        assert isinstance(field, expectation.field_type), (
            f"{field_name}: expected {expectation.field_type.__name__}, "
            f"got {type(field).__name__}"
        )
        assert field.null is expectation.nullable
        if expectation.max_length is not None:
            assert field.max_length == expectation.max_length

    assert UsdaProperty._meta.get_field("usda_case_number").unique is True
    for currency_field in ("list_price", "lot_size_acres"):
        field = UsdaProperty._meta.get_field(currency_field)
        assert isinstance(field, models.DecimalField)
        assert any(
            isinstance(v, MinValueValidator) and v.limit_value == Decimal("0")
            for v in field.validators
        )
    for int_field in ("bedrooms", "square_feet"):
        field = UsdaProperty._meta.get_field(int_field)
        assert any(
            isinstance(v, MinValueValidator) and v.limit_value == 0
            for v in field.validators
        )


def test_usda_property_str_representation():
    """UsdaProperty string representation includes case number and address."""
    prop = UsdaProperty(
        usda_case_number="USDA-2026-001",
        address="456 Oak Ave",
        city="Austin",
        state="TX",
        zip_code="78702",
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )
    assert str(prop) == "USDA USDA-2026-001 — 456 Oak Ave, Austin"


# ═══════════════════════════════════════════════════════════════════════
# CountyForeclosureNotice
# ═══════════════════════════════════════════════════════════════════════

COUNTY_FIELD_EXPECTATIONS: dict[str, FieldExpectation] = {
    "case_number": FieldExpectation(models.CharField, False, 128),
    "document_type": FieldExpectation(models.CharField, False),
    "borrower_name": FieldExpectation(models.CharField, False),
    "lender_name": FieldExpectation(models.CharField, False),
    "trustee_name": FieldExpectation(models.CharField, False),
    "address": FieldExpectation(models.CharField, False),
    "city": FieldExpectation(models.CharField, False),
    "state": FieldExpectation(models.CharField, False, 2),
    "zip_code": FieldExpectation(models.CharField, False),
    "county": FieldExpectation(models.CharField, False),
    "filing_date": FieldExpectation(models.DateField, True),
    "sale_date": FieldExpectation(models.DateField, True),
    "auction_time": FieldExpectation(models.CharField, False),
    "auction_location": FieldExpectation(models.TextField, False),
    "opening_bid": FieldExpectation(models.DecimalField, True),
    "unpaid_balance": FieldExpectation(models.DecimalField, True),
    "estimated_value": FieldExpectation(models.DecimalField, True),
    "parcel_number": FieldExpectation(models.CharField, False),
    "source_url": FieldExpectation(models.URLField, False),
    "raw_data": FieldExpectation(models.JSONField, False),
    "scraped_at": FieldExpectation(models.DateTimeField, False),
    "last_seen_at": FieldExpectation(models.DateTimeField, False),
    "created_at": FieldExpectation(models.DateTimeField, False),
    "updated_at": FieldExpectation(models.DateTimeField, False),
}


def test_county_foreclosure_notice_model_fields():
    """All CountyForeclosureNotice fields match expectations."""
    for field_name, expectation in COUNTY_FIELD_EXPECTATIONS.items():
        field = CountyForeclosureNotice._meta.get_field(field_name)
        assert isinstance(field, expectation.field_type), (
            f"{field_name}: expected {expectation.field_type.__name__}, "
            f"got {type(field).__name__}"
        )
        assert field.null is expectation.nullable
        if expectation.max_length is not None:
            assert field.max_length == expectation.max_length

    assert CountyForeclosureNotice._meta.get_field("case_number").unique is True
    for currency_field in ("opening_bid", "unpaid_balance", "estimated_value"):
        field = CountyForeclosureNotice._meta.get_field(currency_field)
        assert isinstance(field, models.DecimalField)
        assert any(
            isinstance(v, MinValueValidator) and v.limit_value == Decimal("0")
            for v in field.validators
        )


def test_county_foreclosure_notice_str_representation():
    """CountyForeclosureNotice string includes document type, case, and location."""
    notice = CountyForeclosureNotice(
        case_number="NOD-2026-001",
        document_type=CountyForeclosureNotice.DocumentType.NOD,
        address="789 Pine St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        county="Dallas",
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )
    assert "Notice of Default" in str(notice)
    assert "NOD-2026-001" in str(notice)
    assert "Dallas" in str(notice)
