"""Acceptance tests for the ``ingest_hud_reo`` management command."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import HudProperty


@pytest.mark.django_db
def test_hud_ingest_creates_records(
    mock_hud_response: dict[str, list[dict[str, Any]]],
) -> None:
    """Fresh ingestion from fixture creates HudProperty records."""
    call_command("ingest_hud_reo", "--dry-run")

    assert HudProperty.objects.count() == len(mock_hud_response["results"])

    first = HudProperty.objects.first()
    assert first is not None
    assert first.hud_case_number is not None
    assert first.status == HudProperty.Status.ACTIVE


@pytest.mark.django_db
def test_hud_ingest_upserts_not_duplicates(
    mock_hud_response: dict[str, list[dict[str, Any]]],
) -> None:
    """Running twice does not create duplicate HudProperty records."""
    call_command("ingest_hud_reo", "--dry-run")
    call_command("ingest_hud_reo", "--dry-run")

    assert HudProperty.objects.count() == len(mock_hud_response["results"])

    # Verify each fixture case number appears exactly once
    for item in mock_hud_response["results"]:
        matches = HudProperty.objects.filter(hud_case_number=item["case_number"])
        assert matches.count() == 1, f"Duplicate found for {item['case_number']}"


@pytest.mark.django_db
def test_hud_ingest_marks_removed(
    mock_hud_response: dict[str, list[dict[str, Any]]],
    existing_hud_record: HudProperty,
) -> None:
    """Records missing from latest fetch are marked ``removed``, not deleted."""
    call_command("ingest_hud_reo", "--dry-run")

    existing_hud_record.refresh_from_db()
    assert existing_hud_record.status == HudProperty.Status.REMOVED, (
        f"Expected removed, got {existing_hud_record.status}"
    )


@pytest.mark.django_db
def test_hud_price_is_decimal(
    mock_hud_response: dict[str, list[dict[str, Any]]],
) -> None:
    """``asking_price`` is stored as ``Decimal``, not ``float``."""
    call_command("ingest_hud_reo", "--dry-run")

    prop = HudProperty.objects.first()
    assert prop is not None
    assert prop.asking_price is not None
    assert isinstance(prop.asking_price, Decimal)
    assert prop.asking_price > Decimal("0")


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
