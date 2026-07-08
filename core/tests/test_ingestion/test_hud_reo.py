"""Acceptance tests for the ``ingest_hud_reo`` management command.

Updated 2026-07-08: fixture data now mirrors the ArcGIS Hub GeoJSON
schema (confirmed DISC-HG-1).  The ArcGIS source does not include
asking_price, bedrooms, bathrooms, etc. — those fields are left as
None/defaults in HudProperty.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import HudProperty


@pytest.mark.django_db
def test_hud_ingest_creates_records(
    mock_hud_response: dict[str, Any],
) -> None:
    """Fresh ingestion from fixture creates HudProperty records."""
    call_command("ingest_hud_reo", "--dry-run")

    assert HudProperty.objects.count() == len(mock_hud_response["features"])

    first = HudProperty.objects.first()
    assert first is not None
    assert first.hud_case_number is not None
    assert first.status == HudProperty.Status.ACTIVE


@pytest.mark.django_db
def test_hud_ingest_upserts_not_duplicates(
    mock_hud_response: dict[str, Any],
) -> None:
    """Running twice does not create duplicate HudProperty records."""
    call_command("ingest_hud_reo", "--dry-run")
    call_command("ingest_hud_reo", "--dry-run")

    assert HudProperty.objects.count() == len(mock_hud_response["features"])

    # Verify each fixture case number appears exactly once
    for feature in mock_hud_response["features"]:
        case_num = feature["properties"]["CASE_NUM"]
        matches = HudProperty.objects.filter(hud_case_number=case_num)
        assert matches.count() == 1, f"Duplicate found for {case_num}"


@pytest.mark.django_db
def test_hud_ingest_marks_removed(
    mock_hud_response: dict[str, Any],
    existing_hud_record: HudProperty,
) -> None:
    """Records missing from latest fetch are marked ``removed``, not deleted."""
    call_command("ingest_hud_reo", "--dry-run")

    existing_hud_record.refresh_from_db()
    assert existing_hud_record.status == HudProperty.Status.REMOVED, (
        f"Expected removed, got {existing_hud_record.status}"
    )


@pytest.mark.django_db
def test_hud_price_not_available() -> None:
    """ArcGIS data does not include asking_price — field is None."""
    call_command("ingest_hud_reo", "--dry-run")

    prop = HudProperty.objects.first()
    assert prop is not None
    # ArcGIS source doesn't provide pricing data
    assert prop.asking_price is None


@pytest.mark.django_db
def test_hud_closed_date_becomes_sold() -> None:
    """Features with DATE_CLOSED set map to status=SOLD."""
    call_command("ingest_hud_reo", "--dry-run")

    # Third fixture feature (011-662347) has DATE_CLOSED set
    sold = HudProperty.objects.get(hud_case_number="011-662347")
    assert sold.status == HudProperty.Status.SOLD, f"Expected SOLD, got {sold.status}"


@pytest.mark.django_db
def test_hud_insured_status_choices() -> None:
    """``insured_status`` only accepts defined choices."""
    prop = HudProperty(
        hud_case_number="HUD-CHOICES-001",
        address="1 Test St",
        city="Anytown",
        state="TX",
        zip_code="78701",
        status=HudProperty.Status.ACTIVE,
        insured_status="invalid_value",
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        prop.full_clean()


@pytest.mark.django_db
def test_hud_fields_not_in_source_left_as_default() -> None:
    """Fields missing from ArcGIS source are left as None or ''."""
    call_command("ingest_hud_reo", "--dry-run")

    prop = HudProperty.objects.first()
    assert prop is not None
    assert prop.asking_price is None
    assert prop.list_price is None
    assert prop.bedrooms is None
    assert prop.bathrooms is None
    assert prop.square_feet is None
    assert prop.property_type == ""
    assert prop.insured_status == ""
    assert prop.listing_url == ""
    assert prop.image_url == ""
    assert prop.description == ""
