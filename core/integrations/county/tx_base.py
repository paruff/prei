"""Shared base for Texas county foreclosure notice scrapers.

Each TX county publishes trustee sale / foreclosure notices on their
own website (usually the county clerk's page).  This module provides
shared helpers: Playwright page rendering, date parsing, address
parsing, and the standard scrape → upsert flow.

Usage: each county module creates a config dict and calls
``scrape_county_nts(config)`` which returns a list of notice dicts
ready for :class:`CountyForeclosureNotice`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger("prei.scraper.tx_county")

REQUEST_TIMEOUT = 30  # seconds
TEXAS_STATE = "TX"


def scrape_county_nts(county_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Scrape NTS (Notice of Trustee Sale) notices for a Texas county.

    Args:
        county_config: Dict with keys:
            - county_name (str): e.g. "Harris"
            - endpoint (str): URL of the foreclosure page
            - selectors (dict): CSS selectors for table/rows/cells

    Returns:
        List of notice dicts, or empty list on failure.
    """
    county_name = county_config["county_name"]
    endpoint = county_config["endpoint"]

    logger.info("TX %s: fetching NTS from %s", county_name, endpoint)

    html = _fetch_via_playwright(endpoint)
    if html is None:
        logger.warning("TX %s: site unreachable or login wall", county_name)
        return []

    notices = _parse_notices(html, county_config)

    logger.info("TX %s: parsed %d notice(s)", county_name, len(notices))
    return notices


def _fetch_via_playwright(url: str) -> str | None:
    """Fetch page HTML via Playwright headless Chromium."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("playwright not installed")
        return None

    try:
        with sync_playwright() as pw:
            with pw.chromium.launch(headless=True) as browser:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                )
                page = context.new_page()
                response = page.goto(
                    url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000
                )
                if response is None or not response.ok:
                    return None
                page.wait_for_timeout(3000)
                # Check for login wall
                if page.query_selector('a[href*="signin"]'):
                    logger.info("TX county: login wall detected")
                    return None
                return page.content()  # type: ignore[no-any-return]
    except Exception as exc:
        logger.debug("TX county: Playwright error: %s", exc)
        return None


def _parse_notices(html: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse NTS notices from county HTML using configured selectors."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    selectors = config.get("selectors", {})

    # Find the table using configured or fallback selectors
    table = _find_table(soup, selectors)
    if table is None:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    notices: list[dict[str, Any]] = []
    now = datetime.now()

    for row in rows[1:]:  # skip header
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        cell_texts = [c.get_text(strip=True) for c in cells]
        case_number = cell_texts[0] if cell_texts else ""
        if not case_number:
            continue

        notice = {
            "case_number": case_number,
            "document_type": "nts",
            "address": cell_texts[2] if len(cell_texts) > 2 else "",
            "city": "",
            "state": TEXAS_STATE,
            "zip_code": "",
            "county": config["county_name"],
            "trustee_name": cell_texts[3] if len(cell_texts) > 3 else "",
            "lender_name": cell_texts[4] if len(cell_texts) > 4 else "",
            "borrower_name": "",
            "sale_date": _parse_date(cell_texts[1] if len(cell_texts) > 1 else ""),
            "opening_bid": _parse_bid(cell_texts[5] if len(cell_texts) > 5 else ""),
            "unpaid_balance": None,
            "estimated_value": None,
            "parcel_number": "",
            "source_url": config.get("endpoint", ""),
            "raw_data": {"cells": cell_texts},
            "scraped_at": now,
            "last_seen_at": now,
        }

        # Parse address components
        if notice["address"]:
            parts = notice["address"].split(",")
            notice["address"] = parts[0].strip()
            if len(parts) >= 2:
                notice["city"] = parts[1].strip()
            if len(parts) >= 3:
                import re

                m = re.search(r"\b(\d{5})\b", parts[-1])
                if m:
                    notice["zip_code"] = m.group(1)

        notices.append(notice)

    return notices


def _find_table(soup: Any, selectors: dict[str, Any]) -> Any | None:
    """Locate the NTS data table using configured or fallback selectors."""
    primary = selectors.get("table", "table")
    table = soup.select_one(primary)
    if table is not None:
        return table

    for alt in selectors.get("alt_tables", []):
        table = soup.select_one(alt)
        if table is not None:
            return table

    # Last resort: keyword match
    for candidate in soup.find_all("table"):
        text = candidate.get_text().lower()
        if "trustee" in text or "foreclosure" in text or "sale" in text:
            return candidate
    return None


def _parse_date(raw: str) -> str | None:
    """Parse a date string to ISO format."""
    if not raw:
        return None
    from datetime import datetime as dt

    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return dt.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_bid(raw: str) -> Decimal | None:
    """Parse an opening bid to Decimal."""
    if not raw:
        return None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except Exception:
        return None
