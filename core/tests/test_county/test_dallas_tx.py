"""Acceptance tests for Dallas County TX NTS scraper.

These tests use a mock HTML fixture that simulates the Dallas County
foreclosure notice table.  They verify that the parser correctly
extracts fields and normalizes data.

⚠️ DISC-HG-3: The fixture HTML mirrors a best-guess structure.  Once the
live page URL and format are confirmed, update the fixture and parser
selectors accordingly.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterator
from unittest.mock import patch

import pytest

from core.integrations.county import dallas_tx


# ═══════════════════════════════════════════════════════════════════════
# Fixture: mock HTML resembling a Dallas County NTS table
#
# DISC-HG-3: Replace this with actual HTML captured from the live page
# once the URL structure is confirmed.
# ═══════════════════════════════════════════════════════════════════════

MOCK_NTS_HTML = """<!DOCTYPE html>
<html>
<head><title>Dallas County Foreclosure Listings</title></head>
<body>
<h1>Notice of Trustee Sale Listings</h1>
<table class="foreclosure-table">
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
  <td>DC-2026-NTS-0001</td>
  <td>01/06/2026</td>
  <td>123 Main St, Dallas, TX 75201</td>
  <td>Shapiro Law Firm PC</td>
  <td>Wells Fargo Bank NA</td>
  <td>$250,000.00</td>
</tr>
<tr>
  <td>DC-2026-NTS-0002</td>
  <td>02/03/2026</td>
  <td>456 Oak Ave, Dallas, TX 75202</td>
  <td>Barrett Daffin Frappier Turner &amp; Engel LLP</td>
  <td>JPMorgan Chase Bank NA</td>
  <td>$185,500.00</td>
</tr>
<tr>
  <td>DC-2026-NTS-0003</td>
  <td>03/03/2026</td>
  <td>789 Elm St, Dallas, TX 75203</td>
  <td>Orlans PC</td>
  <td>Bank of America NA</td>
  <td>$310,000.00</td>
</tr>
</tbody>
</table>
</body>
</html>"""


@pytest.fixture
def mock_dallas_response() -> Iterator[Any]:
    """Patch the HTTP fetch to return fixture HTML instead of hitting the live site."""
    patcher = patch.object(dallas_tx, "_fetch_page", return_value=MOCK_NTS_HTML)
    try:
        yield patcher.start()
    finally:
        patcher.stop()


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDallasCountyScraper:
    """Acceptance tests for the Dallas County NTS scraper."""

    def test_returns_notices(self, mock_dallas_response: None) -> None:
        """AC-1: scraper returns one or more parsed notices."""
        notices = dallas_tx.scrape_dallas_county_nts()
        assert len(notices) > 0

    def test_required_fields_present(self, mock_dallas_response: None) -> None:
        """AC-2: each notice has address, notice_type == 'NTS', state == 'TX'."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            assert n["address"], f"Notice {n['case_number']} missing address"
            assert n["document_type"] == "nts", (
                f"Expected 'nts', got '{n['document_type']}'"
            )
            assert n["state"] == "TX", f"Expected 'TX', got '{n['state']}'"

    def test_notice_has_all_standard_fields(self, mock_dallas_response: None) -> None:
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

    def test_sale_date_is_first_tuesday(self, mock_dallas_response: None) -> None:
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

    def test_opening_bid_is_decimal(self, mock_dallas_response: None) -> None:
        """Opening bid values are parsed as Decimal."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            bid = n.get("opening_bid")
            if bid is not None:
                assert isinstance(bid, Decimal), (
                    f"Expected Decimal, got {type(bid).__name__}: {bid}"
                )
                assert bid > 0

    def test_county_is_dallas(self, mock_dallas_response: None) -> None:
        """County is hardcoded to 'Dallas' for this scraper."""
        notices = dallas_tx.scrape_dallas_county_nts()
        for n in notices:
            assert n["county"] == "Dallas"

    def test_returns_empty_when_site_down(self) -> None:
        """Scraper returns empty list (no crash) when the page is unreachable."""
        with patch.object(dallas_tx, "_fetch_page", return_value=None):
            notices = dallas_tx.scrape_dallas_county_nts()
            assert notices == []

    def test_returns_empty_for_empty_html(self) -> None:
        """Scraper returns empty list when HTML has no recognizable table."""
        with patch.object(dallas_tx, "_fetch_page", return_value="<html></html>"):
            notices = dallas_tx.scrape_dallas_county_nts()
            assert notices == []

    def test_all_dates_are_first_tuesday_2026(self, mock_dallas_response: None) -> None:
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
