"""Acceptance tests for the ``ingest_usda_reo`` management command."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from django.core.management import call_command

from core.management.commands.ingest_usda_reo import _parse_usda_txt
from core.models import UsdaProperty


@pytest.mark.django_db
def test_usda_ingest_creates_records(
    mock_usda_response: list[dict[str, Any]],
) -> None:
    """Fresh ingestion from fixture creates UsdaProperty records."""
    call_command("ingest_usda_reo", "--dry-run")

    assert UsdaProperty.objects.count() == len(mock_usda_response)

    first = UsdaProperty.objects.first()
    assert first is not None
    assert first.usda_case_number is not None
    assert first.status == UsdaProperty.Status.ACTIVE


@pytest.mark.django_db
def test_usda_ingest_upserts_not_duplicates(
    mock_usda_response: list[dict[str, Any]],
) -> None:
    """Running twice does not create duplicate UsdaProperty records."""
    call_command("ingest_usda_reo", "--dry-run")
    call_command("ingest_usda_reo", "--dry-run")

    assert UsdaProperty.objects.count() == len(mock_usda_response)

    for item in mock_usda_response:
        matches = UsdaProperty.objects.filter(usda_case_number=item["usda_case_number"])
        assert matches.count() == 1, f"Duplicate found for {item['usda_case_number']}"


@pytest.mark.django_db
def test_usda_ingest_marks_removed(
    mock_usda_response: list[dict[str, Any]],
    existing_usda_record: UsdaProperty,
) -> None:
    """Records missing from latest fetch are marked ``removed``, not deleted."""
    call_command("ingest_usda_reo", "--dry-run")

    existing_usda_record.refresh_from_db()
    assert existing_usda_record.status == UsdaProperty.Status.REMOVED, (
        f"Expected removed, got {existing_usda_record.status}"
    )


def test_usda_parser_extracts_fields() -> None:
    """Fixed-width TXT parser extracts correct fields from sample lines."""
    sample_txt = (
        "Opening bid $140,924.00\n"
        "N        00:00.0                    8/28/2018                  "
        "1 car at33127221       3Block   San Jose                53"
        "Ranch   501 S 1s   62682    3614   14048Direct           "
        "                            Forced A\n"
    )

    records = _parse_usda_txt(sample_txt)

    assert len(records) >= 1
    record = records[0]

    # Case number should be extracted
    assert "USDA-" in record["usda_case_number"]

    # City should be extracted
    assert record["city"] == "San Jose"

    # Should have bedrooms
    assert record["bedrooms"] == 3

    # Property type should be mapped
    assert record["property_type"] == "Ranch"

    # Opening bid should be captured from continuation line
    assert record["list_price"] == Decimal("140924.00")


@pytest.mark.django_db
def test_usda_price_is_decimal(
    mock_usda_response: list[dict[str, Any]],
) -> None:
    """``list_price`` is stored as ``Decimal``, not ``float``."""
    call_command("ingest_usda_reo", "--dry-run")

    prop = UsdaProperty.objects.first()
    assert prop is not None
    assert prop.list_price is not None
    assert isinstance(prop.list_price, Decimal)
    assert prop.list_price > Decimal("0")
