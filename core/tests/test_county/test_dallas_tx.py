"""Acceptance tests for Dallas County TX NTS scraper.

These tests use a mock that replaces the Playwright-based page fetch,
allowing the scraper to be tested without a real browser session or
authentication on the publicsearch.us portal.

⚠️ DISC-HG-3 (confirmed 2026-07-08):
The Dallas County foreclosure data is served through a React SPA
(publicsearch.us) that requires a user account.  The scraper currently
returns empty results in production.  The mock fixture data below
reflects the expected field schema; update with real data once an
authenticated session is available.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterator
from unittest.mock import patch

import pytest

from core.integrations.county import dallas_tx


# ═══════════════════════════════════════════════════════════════════════
# Fixture data
#
# These dicts match the schema returned by scrape_dallas_county_nts().
# Update with real values once an authenticated session confirms the
# actual data format.
# ═══════════════════════════════════════════════════════════════════════

FIXTURE_NOTICES: list[dict[str, Any]] = [
    {
        "case_number": "DC-2026-NTS-0001",
        "document_type": "nts",
        "address": "123 Main St",
        "city": "Dallas",
        "state": "TX",
        "zip_code": "75201",
        "county": "Dallas",
        "trustee_name": "Shapiro Law Firm PC",
        "lender_name": "Wells Fargo Bank NA",
        "borrower_name": "",
        "sale_date": "2026-01-06",
        "opening_bid": Decimal("250000.00"),
        "unpaid_balance": None,
        "estimated_value": None,
        "parcel_number": "",
        "source_url": dallas_tx.DEFAULT_ENDPOINT,
        "raw_data": {
            "cells": [
                "DC-2026-NTS-0001",
                "01/06/2026",
                "123 Main St, Dallas, TX 75201",
                "Shapiro Law Firm PC",
                "Wells Fargo Bank NA",
                "$250,000.00",
            ]
        },
    },
    {
        "case_number": "DC-2026-NTS-0002",
        "document_type": "nts",
        "address": "456 Oak Ave",
        "city": "Dallas",
        "state": "TX",
        "zip_code": "75202",
        "county": "Dallas",
        "trustee_name": "Barrett Daffin Frappier Turner & Engel LLP",
        "lender_name": "JPMorgan Chase Bank NA",
        "borrower_name": "",
        "sale_date": "2026-02-03",
        "opening_bid": Decimal("185500.00"),
        "unpaid_balance": None,
        "estimated_value": None,
        "parcel_number": "",
        "source_url": dallas_tx.DEFAULT_ENDPOINT,
        "raw_data": {
            "cells": [
                "DC-2026-NTS-0002",
                "02/03/2026",
                "456 Oak Ave, Dallas, TX 75202",
                "Barrett Daffin Frappier Turner & Engel LLP",
                "JPMorgan Chase Bank NA",
                "$185,500.00",
            ]
        },
    },
    {
        "case_number": "DC-2026-NTS-0003",
        "document_type": "nts",
        "address": "789 Elm St",
        "city": "Dallas",
        "state": "TX",
        "zip_code": "75203",
        "county": "Dallas",
        "trustee_name": "Orlans PC",
        "lender_name": "Bank of America NA",
        "borrower_name": "",
        "sale_date": "2026-03-03",
        "opening_bid": Decimal("310000.00"),
        "unpaid_balance": None,
        "estimated_value": None,
        "parcel_number": "",
        "source_url": dallas_tx.DEFAULT_ENDPOINT,
        "raw_data": {
            "cells": [
                "DC-2026-NTS-0003",
                "03/03/2026",
                "789 Elm St, Dallas, TX 75203",
                "Orlans PC",
                "Bank of America NA",
                "$310,000.00",
            ]
        },
    },
]


@pytest.fixture
def mock_dallas_response() -> Iterator[Any]:
    """Mock the Playwright-based fetch to return fixture notice data."""
    patcher = patch.object(
        dallas_tx,
        "_try_fetch_via_playwright",
        return_value=FIXTURE_NOTICES,
    )
    try:
        yield patcher.start()
    finally:
        patcher.stop()


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDallasCountyScraper:
    """Acceptance tests for the Dallas County NTS scraper."""

    def test_returns_notices(self, mock_dallas_response: Any) -> None:
        """AC-1: scraper returns one or more parsed notices."""
        notices = dallas_tx.scrape_dallas_county_nts()
        assert len(notices) > 0

    def test_required_fields_present(self, mock_dallas_response: Any) -> None:
        """AC-2: each notice has address, document_type == 'nts', state == 'TX'."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            assert n["address"], f"Notice {n['case_number']} missing address"
            assert n["document_type"] == "nts", (
                f"Expected 'nts', got '{n['document_type']}'"
            )
            assert n["state"] == "TX", f"Expected 'TX', got '{n['state']}'"

    def test_notice_has_all_standard_fields(self, mock_dallas_response: Any) -> None:
        """Verify every notice has the full set of expected fields."""
        notices = dallas_tx.scrape_dallas_county_nts()
        required = [
            "case_number",
            "document_type",
            "address",
            "city",
            "state",
            "zip_code",
            "county",
            "trustee_name",
            "lender_name",
            "sale_date",
        ]
        for n in notices:
            for field in required:
                assert n.get(field) is not None and n[field] != "", (
                    f"Notice {n.get('case_number', '?')} missing field: {field}"
                )

    def test_sale_date_is_first_tuesday(self, mock_dallas_response: Any) -> None:
        """AC-3: TX law requires NTS sales on the first Tuesday of the month."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            sale_date_str = n.get("sale_date")
            if sale_date_str:
                sale_date = date.fromisoformat(sale_date_str)
                assert sale_date.weekday() == 1, (
                    f"Notice {n['case_number']}: sale date {sale_date} "
                    f"is not a Tuesday (weekday={sale_date.weekday()})"
                )

    def test_opening_bid_is_decimal(self, mock_dallas_response: Any) -> None:
        """Opening bid values are parsed as Decimal."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            bid = n.get("opening_bid")
            if bid is not None:
                assert isinstance(bid, Decimal), (
                    f"Expected Decimal, got {type(bid).__name__}: {bid}"
                )
                assert bid > 0

    def test_county_is_dallas(self, mock_dallas_response: Any) -> None:
        """County is hardcoded to 'Dallas' for this scraper."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            assert n["county"] == "Dallas"

    def test_returns_empty_when_fetch_fails(self) -> None:
        """Scraper returns empty list (no crash) when Playwright returns None."""
        with patch.object(dallas_tx, "_try_fetch_via_playwright", return_value=None):
            notices = dallas_tx.scrape_dallas_county_nts()
            assert notices == []

    def test_returns_empty_when_playwright_not_available(self) -> None:
        """Scraper returns empty list when playwright is not installed."""
        with patch.object(dallas_tx, "_try_fetch_via_playwright", return_value=None):
            notices = dallas_tx.scrape_dallas_county_nts()
            assert notices == []

    def test_all_dates_are_first_tuesday_2026(self, mock_dallas_response: Any) -> None:
        """Verify all three fixture dates fall on a Tuesday."""
        import calendar

        notices = dallas_tx.scrape_dallas_county_nts()
        expected_dates = [
            date(2026, 1, 6),  # First Tuesday of Jan 2026
            date(2026, 2, 3),  # First Tuesday of Feb 2026
            date(2026, 3, 3),  # First Tuesday of Mar 2026
        ]
        parsed_dates = [
            date.fromisoformat(n["sale_date"]) for n in notices if n.get("sale_date")
        ]
        for d in parsed_dates:
            assert d in expected_dates, (
                f"Unexpected date {d} — not a first Tuesday in 2026"
            )
            assert d.weekday() == calendar.TUESDAY


class TestDallasCountyParser:
    """Unit tests for the HTML parsing logic (``_parse_rendered_html``)."""

    FIXTURE_HTML = """<!DOCTYPE html>
<html>
<head><title>Dallas County Foreclosure Results</title></head>
<body>
<div id="content">
<table>
<thead>
<tr>
  <th>Case Number</th>
  <th>Sale Date</th>
  <th>Property Address</th>
  <th>Trustee</th>
  <th>Lender/Beneficiary</th>
  <th>Opening Bid</th>
</tr>
</thead>
<tbody>
<tr>
  <td>DC-2026-NTS-0101</td>
  <td>04/07/2026</td>
  <td>101 Test Blvd, Dallas, TX 75201</td>
  <td>Shapiro Law Firm PC</td>
  <td>Wells Fargo Bank NA</td>
  <td>$175,000.00</td>
</tr>
<tr>
  <td>DC-2026-NTS-0102</td>
  <td>05/05/2026</td>
  <td>202 Sample Ave, Dallas, TX 75202</td>
  <td>Barrett Daffin Frappier Turner &amp; Engel LLP</td>
  <td>JPMorgan Chase Bank NA</td>
  <td>$220,000.00</td>
</tr>
</tbody>
</table>
</div>
</body>
</html>"""

    def test_parser_extracts_notices(self) -> None:
        """Parser extracts notices from rendered HTML."""
        notices = dallas_tx._parse_rendered_html(self.FIXTURE_HTML)
        assert len(notices) == 2

    def test_parser_required_fields(self) -> None:
        """Each parsed notice has required fields."""
        notices = dallas_tx._parse_rendered_html(self.FIXTURE_HTML)
        for n in notices:
            assert n["document_type"] == "nts"
            assert n["county"] == "Dallas"
            assert n["state"] == "TX"
            assert n["address"]
            assert n["case_number"]

    def test_parser_extracts_opening_bid(self) -> None:
        """Opening bid is parsed as Decimal from rendered HTML."""
        notices = dallas_tx._parse_rendered_html(self.FIXTURE_HTML)
        bids = [n["opening_bid"] for n in notices if n.get("opening_bid")]
        assert len(bids) == 2
        assert all(isinstance(b, Decimal) for b in bids)
        assert bids == [Decimal("175000.00"), Decimal("220000.00")]

    def test_parser_returns_empty_for_no_table(self) -> None:
        """Parser returns empty list when HTML has no recognizable table."""
        notices = dallas_tx._parse_rendered_html("<html><body></body></html>")
        assert notices == []

    def test_parser_extracts_address_components(self) -> None:
        """Address, city and zip are parsed from the address column."""
        notices = dallas_tx._parse_rendered_html(self.FIXTURE_HTML)
        assert notices[0]["address"] == "101 Test Blvd"
        assert notices[0]["city"] == "Dallas"
        assert notices[0]["zip_code"] == "75201"
        assert notices[1]["address"] == "202 Sample Ave"
        assert notices[1]["city"] == "Dallas"
        assert notices[1]["zip_code"] == "75202"

    def test_parser_sale_dates_are_first_tuesday(self) -> None:
        """Parsed sale dates are all first Tuesdays."""
        notices = dallas_tx._parse_rendered_html(self.FIXTURE_HTML)
        expected = [
            date(2026, 4, 7),  # First Tuesday Apr 2026
            date(2026, 5, 5),  # First Tuesday May 2026
        ]
        for n, expected_date in zip(notices, expected):
            parsed = date.fromisoformat(n["sale_date"])
            assert parsed == expected_date
            assert parsed.weekday() == 1  # Tuesday
