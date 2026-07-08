"""Acceptance tests for ATTOM preforeclosure integration.

These tests mock the ATTOM API response at the adapter level,
verifying that the normalization and upsert logic work correctly
without a real API key or subscription.

DISC-HG-4: Confirm that the ATTOM subscription covers the
``/preforeclosure/detail`` endpoint before using in production.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterator
from unittest.mock import patch

import pytest
from django.core.management import call_command

from core.integrations.sources import attom_preforeclosure
from core.models import CountyForeclosureNotice


# ═══════════════════════════════════════════════════════════════════════
# Fixture: mocked ATTOM API response
#
# This mimics what the /preforeclosure/detail endpoint returns for a
# ZIP code with two active preforeclosure properties.
# ═══════════════════════════════════════════════════════════════════════

MOCK_ATTOM_RESPONSE: dict[str, Any] = {
    "status": {"code": 0, "msg": "Success"},
    "property": [
        {
            "address": {
                "line1": "123 Main St",
                "locality": "Dallas",
                "countrySubd": "TX",
                "postal1": "75201",
                "county": "Dallas",
                "latitude": "32.7767",
                "longitude": "-96.7970",
            },
            "preforeclosure": {
                "caseNumber": "ATTOM-NOD-2026-001",
                "stage": "Preforeclosure",
                "date": "2026-03-15",
                "auctionDate": None,
                "amount": 185000.00,
                "lenderName": "Wells Fargo Bank NA",
            },
            "avm": {"amount": {"value": 250000.00}},
            "summary": {
                "proptype": "Single Family Residence",
                "attainableparcel": "PCL-001",
            },
        },
        {
            "address": {
                "line1": "456 Oak Ave",
                "locality": "Dallas",
                "countrySubd": "TX",
                "postal1": "75202",
                "county": "Dallas",
                "latitude": "32.7845",
                "longitude": "-96.8001",
            },
            "preforeclosure": {
                "caseNumber": "ATTOM-LP-2026-002",
                "stage": "Lis Pendens",
                "date": "2026-04-01",
                "auctionDate": "2026-07-07",
                "amount": 220000.00,
                "lenderName": "JPMorgan Chase Bank NA",
            },
            "avm": {"amount": {"value": 310000.00}},
            "summary": {
                "proptype": "Single Family Residence",
                "attainableparcel": "PCL-002",
            },
        },
    ],
}


@pytest.fixture
def mock_attom_response() -> Iterator[Any]:
    """Patch the ATTOM adapter to return fixture data instead of calling the API."""
    patcher = patch.object(
        attom_preforeclosure.ATTOMAdapter,
        "fetch_foreclosure_data",
        return_value=MOCK_ATTOM_RESPONSE,
    )
    try:
        yield patcher.start()
    finally:
        patcher.stop()


@pytest.fixture
def mock_attom_empty_response() -> Iterator[Any]:
    """Patch the adapter to return an empty response."""
    patcher = patch.object(
        attom_preforeclosure.ATTOMAdapter,
        "fetch_foreclosure_data",
        return_value={"status": {"code": 0}, "property": []},
    )
    try:
        yield patcher.start()
    finally:
        patcher.stop()


# ═══════════════════════════════════════════════════════════════════════
# Tests: fetch_attom_preforeclosure()
# ═══════════════════════════════════════════════════════════════════════


class TestFetchAttomPreforeclosure:
    """Tests for the ``fetch_attom_preforeclosure`` function."""

    def test_returns_notices_list(self, mock_attom_response: Any) -> None:
        """AC-1: Returns a list (empty is valid)."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        assert isinstance(notices, list)

    def test_returns_notices_when_data_exists(self, mock_attom_response: Any) -> None:
        """Returns notices when the API returns data."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        assert len(notices) > 0

    def test_returns_empty_for_empty_response(
        self, mock_attom_empty_response: Any
    ) -> None:
        """Returns empty list when API returns no properties."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="99999")
        assert notices == []

    def test_notice_has_required_fields(self, mock_attom_response: Any) -> None:
        """Each notice has case_number, address, state, document_type."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        for n in notices:
            assert n["case_number"]
            assert n["address"]
            assert n["state"] == "TX"
            assert n["document_type"] in [
                CountyForeclosureNotice.DocumentType.NOD,
                CountyForeclosureNotice.DocumentType.LIS_PENDENS,
            ]

    def test_stage_maps_to_document_type(self, mock_attom_response: Any) -> None:
        """Preforeclosure stage maps to NOD, Lis Pendens maps to LIS_PENDENS."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        type_map = {n["case_number"]: n["document_type"] for n in notices}
        assert (
            type_map["ATTOM-NOD-2026-001"] == CountyForeclosureNotice.DocumentType.NOD
        )
        assert (
            type_map["ATTOM-LP-2026-002"]
            == CountyForeclosureNotice.DocumentType.LIS_PENDENS
        )


# ═══════════════════════════════════════════════════════════════════════
# Tests: normalize_to_county_notice() — model validation
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestNormalizeToCountyNotice:
    """Verifies that normalized data satisfies CountyForeclosureNotice constraints."""

    def test_notice_normalizes_to_model(self, mock_attom_response: Any) -> None:
        """AC-2: Each notice dict can instantiate a valid CountyForeclosureNotice."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        for n in notices:
            obj = CountyForeclosureNotice(**n)
            obj.full_clean()  # raises ValidationError if invalid

    def test_normalized_has_decimal_fields(self, mock_attom_response: Any) -> None:
        """Unpaid balance and estimated value are Decimal or None."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        for n in notices:
            ub = n.get("unpaid_balance")
            ev = n.get("estimated_value")
            if ub is not None:
                assert isinstance(ub, Decimal)
            if ev is not None:
                assert isinstance(ev, Decimal)

    def test_filing_date_is_iso_format(self, mock_attom_response: Any) -> None:
        """Filing dates are ISO format strings (YYYY-MM-DD)."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        for n in notices:
            fd = n.get("filing_date")
            if fd:
                assert len(fd) == 10
                assert fd[4] == "-" and fd[7] == "-"

    def test_sale_date_is_none_for_nod(self, mock_attom_response: Any) -> None:
        """NOD notices may not have a sale date (pre-auction stage)."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        for n in notices:
            if n["document_type"] == CountyForeclosureNotice.DocumentType.NOD:
                assert n.get("sale_date") is None

    def test_sale_date_present_for_lis_pendens(self, mock_attom_response: Any) -> None:
        """Lis Pendens notices may have an auction/sale date."""
        notices = attom_preforeclosure.fetch_attom_preforeclosure(zip_code="75201")
        for n in notices:
            if n["document_type"] == CountyForeclosureNotice.DocumentType.LIS_PENDENS:
                assert n.get("sale_date") is not None


# ═══════════════════════════════════════════════════════════════════════
# Tests: integration with management command
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestAttomPreforeclosureCommand:
    """Tests for the ``fetch_attom_preforeclosure`` management command."""

    def test_command_creates_notices(self, mock_attom_response: Any) -> None:
        """Command upserts notices into the database."""
        call_command("fetch_attom_preforeclosure", "--zip-code=75201")
        assert CountyForeclosureNotice.objects.count() == 2

    def test_command_dry_run_no_writes(self, mock_attom_response: Any) -> None:
        """Dry run does not write to the database."""
        call_command("fetch_attom_preforeclosure", "--zip-code=75201", "--dry-run")
        assert CountyForeclosureNotice.objects.count() == 0

    def test_command_upserts_not_duplicates(self, mock_attom_response: Any) -> None:
        """Running the command twice does not create duplicates."""
        call_command("fetch_attom_preforeclosure", "--zip-code=75201")
        call_command("fetch_attom_preforeclosure", "--zip-code=75201")
        assert CountyForeclosureNotice.objects.count() == 2

    def test_command_empty_zip(self, mock_attom_empty_response: Any) -> None:
        """Command handles ZIP codes with no notices gracefully."""
        call_command("fetch_attom_preforeclosure", "--zip-code=99999")
        assert CountyForeclosureNotice.objects.count() == 0
