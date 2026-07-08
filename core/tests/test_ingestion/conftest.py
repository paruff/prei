"""Test fixtures for USDA REO ingestion tests."""

from __future__ import annotations

from typing import Any

import pytest
from django.utils import timezone

from core.management.commands.ingest_usda_reo import USDA_FIXTURE_DATA
from core.models import UsdaProperty


@pytest.fixture
def mock_usda_response() -> list[dict[str, Any]]:
    """Return the embedded USDA fixture data for assertion matching.

    The ``ingest_usda_reo --dry-run`` command uses the same embedded
    fixture data, so tests can assert record counts against this fixture.
    """
    return USDA_FIXTURE_DATA


@pytest.fixture
def existing_usda_record() -> UsdaProperty:
    """Create a UsdaProperty record *not* present in the fixture data.

    After a full ingestion run this record should be marked as ``removed``
    because its ``usda_case_number`` does not appear in the latest fetch.
    """
    return UsdaProperty.objects.create(
        usda_case_number="USDA-LEGACY-999",
        address="100 Legacy Ln",
        city="Austin",
        state="TX",
        zip_code="78701",
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )
