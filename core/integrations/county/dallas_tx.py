"""Dallas County TX Notice of Trustee Sale (NTS) scraper.

Fetches public NTS foreclosure listings from Dallas County's online
foreclosure records portal and parses them into a structured dict format
suitable for upsert into CountyForeclosureNotice.

Human Gate DISC-HG-3
---------------------
Manually verify the actual URL and page structure at:
  https://www.dallascounty.org/government/county-clerk/recording/foreclosures.php

The parser below is a best-guess skeleton based on common Texas county
foreclosure page formats.  Adjust selectors and field extraction once
the actual page structure is confirmed.

Known limitation
----------------
Texas law requires NTS sales to be held on the first Tuesday of each
month.  The parser does NOT currently validate this — it returns what
the source provides.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("prei.scraper.dallas_tx")

# ═══════════════════════════════════════════════════════════════════════
# DISC-HG-3: Confirm these values before production use.
#
# The URL below is the known county clerk foreclosure page.  It may
# serve an HTML table directly, link to a PDF, or redirect to a third-
# party portal.  Adjust after manual inspection.
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_ENDPOINT = (
    "https://www.dallascounty.org/government/county-clerk/recording/foreclosures.php"
)

REQUEST_TIMEOUT = 30  # seconds
DEFAULT_DELAY = 2.0  # seconds between requests

# ── TX-specific constants ──────────────────────────────────────────
TEXAS_COUNTY = "Dallas"
TEXAS_STATE = "TX"

# ═══════════════════════════════════════════════════════════════════════
# Data schema returned by scrape_dallas_county_nts()
#
# Each notice dict contains these fields (matching CountyForeclosureNotice):
#   case_number:   str — unique case identifier
#   document_type: str — always "nts" for Notice of Trustee Sale
#   address:       str — property street address
#   city:          str — property city
#   state:         str — always "TX"
#   zip_code:      str — ZIP code (may be empty if unavailable)
#   county:        str — always "Dallas"
#   trustee_name:  str — foreclosing trustee
#   lender_name:   str — lender/beneficiary
#   sale_date:     datetime.date — scheduled auction date (may be None)
#   opening_bid:   Decimal or None — opening bid amount
#   source_url:    str — URL this record was scraped from
#   raw_data:      dict — original row data for audit
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DallasNTSRecord:
    """Structured representation of one Dallas County NTS record."""

    case_number: str
    address: str
    city: str
    trustee_name: str
    lender_name: str
    sale_date: date | None
    opening_bid: Decimal | None


# ═══════════════════════════════════════════════════════════════════════
# DISC-HG-3 HTML SELECTORS
#
# These are informed guesses based on common Texas county foreclosure
# table formats.  Replace with actual class names / IDs after manual
# inspection of the live page.
# ═══════════════════════════════════════════════════════════════════════

SELECTORS: dict[str, str] = {
    "table": "table.foreclosure-table",  # Common pattern
    "rows": "tbody tr",  # Table rows
}

# Fallback selector chain if primary table selector fails
ALT_SELECTORS: dict[str, list[str]] = {
    "table": [
        "table#foreclosures",
        "table.foreclosure-list",
        "table.table-striped",
        "div.foreclosure-list table",
    ],
    "rows": [
        "tbody tr",
        "tr.foreclosure-row",
        "div.listing",
    ],
}

# ── Column index mapping (based on common TX county NTS table layout) ──
# DISC-HG-3: Adjust these indices based on actual column order.
# Typical columns: Case No. | Sale Date | Property Address | Trustee | Lender | Bid
COLUMNS = {
    "case_number": 0,
    "sale_date": 1,
    "address": 2,
    "trustee_name": 3,
    "lender_name": 4,
    "opening_bid": 5,  # may be empty/missing
}


# ═══════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════


def scrape_dallas_county_nts() -> list[dict[str, Any]]:
    """Fetch and parse Dallas County NTS listings.

    Returns a list of notice dicts ready for upsert into
    :class:`CountyForeclosureNotice`.  Returns an empty list with a
    logged warning when the site is unreachable or the structure has
    changed.

    DISC-HG-3 note: This function is a skeleton.  The actual HTML
    parsing logic in ``_parse_html()`` must be verified against the
    live page before the results can be trusted.
    """
    logger.info("Dallas County: fetching NTS listings from %s", DEFAULT_ENDPOINT)

    html = _fetch_page()
    if html is None:
        return []

    notices = _parse_html(html)

    logger.info("Dallas County: parsed %d NTS notices", len(notices))
    return notices


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════


def _fetch_page() -> str | None:
    """HTTP GET the Dallas County foreclosure page.

    Returns the response text, or ``None`` on failure (logged).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(
            DEFAULT_ENDPOINT,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return cast(str, response.text)
    except requests.RequestException as exc:
        logger.warning(
            "Dallas County NTS page unreachable: %s",
            exc,
        )
        return None


def _parse_html(html: str) -> list[dict[str, Any]]:
    """Parse NTS listings from Dallas County HTML.

    ═══════════════════════════════════════════════════════════════════
    DISC-HG-3: This is a best-guess implementation.  The selectors,
    column order, and field extraction logic must be verified against
    the live page structure.
    ═══════════════════════════════════════════════════════════════════
    """
    soup = BeautifulSoup(html, "html.parser")
    table = _find_table(soup)

    if table is None:
        logger.warning(
            "Dallas County: could not locate NTS table — "
            "site structure may have changed (see DISC-HG-3)"
        )
        return []

    rows = _find_rows(table)
    if not rows:
        logger.info("Dallas County: NTS table found but no data rows")
        return []

    notices: list[dict[str, Any]] = []
    errors = 0

    for row in rows:
        try:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                # Not enough columns — skip header rows and sparse rows
                continue

            case_number = cells[COLUMNS["case_number"]].get_text(strip=True)
            if not case_number:
                continue  # skip rows without a case number

            notice = _row_to_notice(cells)
            if notice is not None:
                notices.append(notice)

        except Exception as exc:
            errors += 1
            logger.debug("Dallas County: failed to parse row: %s", exc)
            continue

    if errors:
        logger.warning("Dallas County: %d row(s) failed to parse", errors)

    return notices


def _find_table(soup: BeautifulSoup) -> Any | None:
    """Locate the NTS data table in the parsed HTML.

    Tries the primary selector first, then fallback selectors.
    """
    table = soup.select_one(SELECTORS["table"])
    if table is not None:
        return table

    for alt_sel in ALT_SELECTORS["table"]:
        table = soup.select_one(alt_sel)
        if table is not None:
            logger.info("Dallas County: using alternative table selector: %s", alt_sel)
            return table

    # Last resort: find any table with enough rows containing typical
    # NTS keywords
    for candidate in soup.find_all("table"):
        text = candidate.get_text().lower()
        if "trustee" in text or "foreclosure" in text or "sale" in text:
            logger.info("Dallas County: heuristic table match (keyword)")
            return candidate

    return None


def _find_rows(table: Any) -> list[Any]:
    """Extract data rows from the table."""
    for sel in [SELECTORS["rows"], *ALT_SELECTORS["rows"]]:
        rows = cast(list[Any], table.select(sel))
        if rows:
            return rows
    return []


def _row_to_notice(cells: list[Any]) -> dict[str, Any] | None:
    """Convert one table row to a notice dict.

    ═══════════════════════════════════════════════════════════════════
    DISC-HG-3: This field extraction logic is a guess.  Column count,
    ordering, and format must be confirmed against the live page.
    ═══════════════════════════════════════════════════════════════════
    """
    cell_texts = [c.get_text(strip=True) for c in cells]

    case_number = cell_texts[COLUMNS["case_number"]]
    sale_date = _parse_sale_date(cell_texts[COLUMNS["sale_date"]])
    address_raw = cell_texts[COLUMNS["address"]]
    trustee = cell_texts[COLUMNS["trustee_name"]]
    lender = cell_texts[COLUMNS["lender_name"]]
    bid_raw = (
        cell_texts[COLUMNS["opening_bid"]]
        if len(cell_texts) > COLUMNS["opening_bid"]
        else ""
    )

    # Parse address into components
    address, city, zip_code = _parse_address(address_raw)

    opening_bid = _parse_opening_bid(bid_raw)
    now = datetime.now()

    notice: dict[str, Any] = {
        "case_number": case_number,
        "document_type": "nts",
        "address": address,
        "city": city,
        "state": TEXAS_STATE,
        "zip_code": zip_code,
        "county": TEXAS_COUNTY,
        "trustee_name": trustee,
        "lender_name": lender,
        "borrower_name": "",  # Not typically available in NTS public records
        "sale_date": sale_date.isoformat() if sale_date is not None else None,
        "opening_bid": opening_bid,
        "unpaid_balance": None,
        "estimated_value": None,
        "parcel_number": "",
        "source_url": DEFAULT_ENDPOINT,
        "raw_data": {"cells": cell_texts},
        "scraped_at": now,
        "last_seen_at": now,
    }

    return notice


def _parse_sale_date(raw: str) -> date | None:
    """Parse sale date from common Texas county formats.

    Expected formats (after DISC-HG-3 confirmation):
      - "01/07/2026"
      - "2026-01-07"
      - "January 7, 2026"
      - "FIRST TUESDAY" — see special handling for TX law
    """
    if not raw:
        return None

    raw_clean = raw.strip()

    # Special case: some counties don't list individual dates but just
    # say "First Tuesday of each month" — cannot parse a specific date.
    if "first tuesday" in raw_clean.lower():
        # Cannot return a specific date; caller should handle
        return None

    from datetime import datetime as dt

    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return dt.strptime(raw_clean, fmt).date()
        except ValueError:
            continue

    return None


def _parse_opening_bid(raw: str) -> Decimal | None:
    """Parse opening bid amount from text.

    Handles formats like "$250,000.00", "250000.00", "250000".
    """
    if not raw:
        return None

    cleaned = raw.replace("$", "").replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def _parse_address(raw: str) -> tuple[str, str, str]:
    """Parse a property address into (street, city, zip).

    Handles common formats like:
      - "123 Main St, Dallas, TX 75201"
      - "123 Main St, Dallas 75201"
      - "123 Main St"
    """
    if not raw:
        return "", "", ""

    # Split on commas
    parts = [p.strip() for p in raw.split(",")]

    street = parts[0] if len(parts) >= 1 else ""
    city = ""
    zip_code = ""

    if len(parts) >= 2:
        # Second-to-last part is usually city
        city = parts[1]

    if len(parts) >= 3:
        # Last part: could be "TX 75201" or just "75201" or "TX"
        last = parts[-1]
        import re

        # Match "TX 75201" or "75201"
        m = re.search(r"\b(\d{5})\b", last)
        if m:
            zip_code = m.group(1)

    return street, city, zip_code
