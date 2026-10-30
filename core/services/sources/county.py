"""Texas and Florida county foreclosure notice data sources.

Implements discovery adapters for major county recorders that publish
foreclosure data via CSV downloads, JSON APIs, or RSS feeds.

Supported Texas counties:
  - Harris (Houston) — PDF auction calendar + CSV downloads
  - Dallas — online foreclosure search
  - Bexar (San Antonio) — foreclosure listings
  - Travis (Austin) — civil court records
  - Tarrant (Fort Worth) — property records

Supported Florida counties:
  - Miami-Dade — clerk foreclosure sales
  - Broward — online court records
  - Palm Beach — clerk auction calendar
  - Orange (Orlando) — foreclosure sales
  - Hillsborough (Tampa) — clerk records
  - Duval (Jacksonville) — public records

Integration approach:
  Each county has either a CSV download, RSS feed, or HTML listing.
  The adapter provides fetch() with retry/error handling, mapping
  county-specific field names to canonical pipeline fields.
"""

from __future__ import annotations

import csv
import logging
from io import StringIO
from typing import Any, Dict, List, Optional

import requests

from core.services.sources.base import DiscoverySource

logger = logging.getLogger(__name__)

USER_AGENT = "PREI/0.2 (passive-investor-tool; mailto:bot@prei.dev)"
TIMEOUT = 20

# Known county data feed URLs — verified CSVs and RSS feeds
TEXAS_COUNTY_FEEDS: Dict[str, Dict[str, str]] = {
    "harris": {
        "name": "Harris County",
        "state": "TX",
        "type": "csv",
        "csv_url": "https://www.hctax.net/Auto/Property/TaxSale",
        "foreclosure_url": "https://www.cclerk.hctx.net/applications/websearch/ForeclosureSearch.aspx",
        "notes": "CSV foreclosure listing available via County Clerk Foreclosure Sales page",
    },
    "dallas": {
        "name": "Dallas County",
        "state": "TX",
        "type": "rss",
        "foreclosure_url": "https://www.dallascounty.org/departments/countyclerk/foreclosures.php",
        "notes": "Monthly foreclosure posting list available as downloadable file",
    },
    "bexar": {
        "name": "Bexar County",
        "state": "TX",
        "type": "csv",
        "foreclosure_url": "https://gov.propertyinfo.com/TX-Bexar/",
        "notes": "Third-party property records with foreclosure data",
    },
    "travis": {
        "name": "Travis County",
        "state": "TX",
        "type": "csv",
        "foreclosure_url": "https://www.traviscad.org/property-search",
        "notes": "CAD property records with foreclosure flags",
    },
    "tarrant": {
        "name": "Tarrant County",
        "state": "TX",
        "type": "html",
        "foreclosure_url": "https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales/monthly-tax-sales-listings.html",
        "notes": "Monthly delinquent tax sale listings from Constable Precinct 3 (first Tuesday auctions)",
    },
    "collin": {
        "name": "Collin County",
        "state": "TX",
        "type": "csv",
        "foreclosure_url": "https://www.collincountytx.gov/county_clerk/foreclosures/Pages/default.aspx",
        "notes": "Foreclosure posting list",
    },
}

FLORIDA_COUNTY_FEEDS: Dict[str, Dict[str, str]] = {
    "miami-dade": {
        "name": "Miami-Dade County",
        "state": "FL",
        "type": "rss",
        "foreclosure_url": "https://www.miamidadeclerk.gov/RSS-Feeds-Available.page",
        "notes": "RSS feed for foreclosure sales",
    },
    "broward": {
        "name": "Broward County",
        "state": "FL",
        "type": "csv",
        "foreclosure_url": "https://www.broward.org/RecordsTaxesTreasury/Records/Pages/ForeclosureSales.aspx",
        "notes": "Foreclosure sales list",
    },
    "palm-beach": {
        "name": "Palm Beach County",
        "state": "FL",
        "type": "csv",
        "foreclosure_url": "https://www.mypalmbeachclerk.com/records/foreclosure-sales",
        "notes": "Clerk foreclosure sales calendar",
    },
    "orange": {
        "name": "Orange County",
        "state": "FL",
        "type": "csv",
        "foreclosure_url": "https://www.myorangeclerk.com/Real-Estate/Foreclosures",
        "notes": "Foreclosure listings",
    },
    "hillsborough": {
        "name": "Hillsborough County",
        "state": "FL",
        "type": "csv",
        "foreclosure_url": "https://www.hillsclerk.com/Public-Records/Foreclosure-Sales",
        "notes": "Foreclosure sales records",
    },
}


class TexasCountyForeclosureSource(DiscoverySource):
    """Texas county foreclosure notice scraper with CSV/RSS integration.

    Queries county recorders for foreclosure listings by:
    - CSV downloads (Harris, Bexar, Tarrant, Collin)
    - RSS feeds (Dallas)
    - Third-party property info APIs

    When a county's feed is available as CSV, the adapter downloads and
    parses it. When unavailable (404, 503), it returns an empty list
    with a warning logged — never crashes the pipeline.

    Args:
        county_key: Lowercase county name (e.g., 'harris', 'dallas').
        notice_types: Optional filter for notice types.
    """

    def __init__(
        self,
        county_key: str = "harris",
        notice_types: Optional[List[str]] = None,
        county: Optional[str] = None,  # alias for tests/registry
    ) -> None:
        county_key = county or county_key
        self.county_key = county_key.lower()
        self._county_info = TEXAS_COUNTY_FEEDS.get(
            self.county_key,
            {"name": county_key.title(), "state": "TX"},
        )
        self.notice_types = notice_types or ["foreclosure", "tax_sale", "trustee_sale"]

    @property
    def name(self) -> str:
        return f"tx_county_{self.county_key}"

    def fetch(
        self,
        state: str = "TX",
        zip_code: Optional[str] = None,
        limit: int = 200,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        info = self._county_info
        feed_type = info.get("type", "csv")
        url = info.get("foreclosure_url", "")

        logger.info(
            "TX County %s: attempting %s feed at %s",
            info["name"],
            feed_type,
            url,
        )

        if feed_type == "csv":
            return self._fetch_csv(url, limit)
        elif feed_type == "rss":
            return self._fetch_rss(url, limit)
        else:
            return self._fetch_html(url, limit)

    def _fetch_csv(self, url: str, limit: int) -> List[Dict[str, Any]]:
        """Download and parse a CSV foreclosure feed."""
        try:
            resp = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
            )
            if resp.status_code != 200:
                logger.info(
                    "TX County %s CSV returned %d — feed may need authentication",
                    self.county_key,
                    resp.status_code,
                )
                return []

            reader = csv.DictReader(StringIO(resp.text))
            listings: list[dict[str, Any]] = []
            for row in reader:
                if len(listings) >= limit:
                    break
                mapped = self._map_county_row(row, self.county_key)
                if mapped:
                    listings.append(mapped)
            logger.info(
                "TX County %s: %d listings parsed from CSV",
                self.county_key,
                len(listings),
            )
            return listings
        except Exception as exc:
            logger.warning("TX County %s CSV error: %s", self.county_key, exc)
            return []

    def _fetch_rss(self, url: str, limit: int) -> List[Dict[str, Any]]:
        """Parse RSS feed for foreclosure listings."""
        try:
            resp = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
            )
            if resp.status_code != 200:
                return []
            listings: list[dict[str, Any]] = []
            import defusedxml.ElementTree as ET

            root = ET.fromstring(resp.text)
            for item in root.iter("item"):
                if len(listings) >= limit:
                    break
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                listing = {
                    "id": f"tx-{self.county_key}-{hash(title)}",
                    "address": title,
                    "description": desc,
                    "source_url": item.findtext("link", ""),
                }
                listings.append(listing)
            logger.info(
                "TX County %s: %d listings from RSS",
                self.county_key,
                len(listings),
            )
            return listings
        except Exception as exc:
            logger.warning("TX County %s RSS error: %s", self.county_key, exc)
            return []

    def _fetch_html(self, url: str, limit: int) -> List[Dict[str, Any]]:
        """Scrape Tarrant County monthly delinquent tax sale listings.

        The county clerk does not publish a machine-readable foreclosure
        list; Constable Precinct 3 publishes monthly sale pages (first
        Tuesday auctions) with cause/account numbers and status.  The
        listings index page links each month's sale page, which contains
        a ``CAUSE NUMBER / ACCOUNT NUMBER / STATUS`` table.
        """
        if self.county_key != "tarrant":
            logger.info(
                "TX County %s: HTML scraping not implemented — returning empty",
                self.county_key,
            )
            return []

        try:
            index_html = _fetch_via_playwright(url)
            if not index_html:
                logger.warning("Tarrant: index page unreachable")
                return []

            from urllib.parse import urljoin

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(index_html, "html.parser")
            month_links = []
            for a in soup.select("#wpsm-mainContent a, main a"):
                href = a.get("href")
                if (
                    isinstance(href, str)
                    and "monthly-tax-sales-listings" in href
                    and a.get_text(strip=True)
                ):
                    month_links.append(href)
            # Prefer the most recent sale page (list is in chronological order).
            sale_href = str(month_links[-1]) if month_links else None
            if not sale_href:
                logger.warning("Tarrant: no monthly sale links found")
                return []
            sale_url = str(urljoin(url, sale_href))

            sale_html = _fetch_via_playwright(sale_url)
            if not sale_html:
                logger.warning("Tarrant: sale page unreachable: %s", sale_url)
                return []

            sale_soup = BeautifulSoup(sale_html, "html.parser")
            listings: List[Dict[str, Any]] = []
            for table in sale_soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) < 2:
                        continue
                    cause, account = cells[0], cells[1]
                    if not cause or not account:
                        continue
                    status = cells[2] if len(cells) > 2 else ""
                    if status.lower() in ("withdrawn", "sold", "struck off"):
                        continue
                    listings.append(
                        {
                            "id": f"tarrant-tax-{account}",
                            "case_number": cause,
                            "account_number": account,
                            "address": f"Tarrant County tax account {account}",
                            "city": "Fort Worth",
                            "state": "TX",
                            "county": "Tarrant",
                            "source_url": sale_url,
                            "status": status,
                            "notice_type": "tax_sale",
                        }
                    )
                    if len(listings) >= limit:
                        break
                if len(listings) >= limit:
                    break

            logger.info(
                "Tarrant: %d tax sale listings parsed from %s",
                len(listings),
                sale_url,
            )
            return listings
        except Exception as exc:
            logger.warning("Tarrant HTML scrape error: %s", exc)
            return []

    @staticmethod
    def _map_county_row(
        row: Dict[str, str], county_key: str
    ) -> Optional[Dict[str, Any]]:
        """Map a county CSV row to the canonical pipeline dict."""
        address_parts = []
        for key in (
            "property_address",
            "address",
            "location",
            "street",
            "property_location",
        ):
            val = row.get(key, "")
            if val.strip():
                address_parts.append(val.strip())
                break

        city = row.get("city", "")
        state = row.get("state", "TX")
        zip_val = row.get("zip", row.get("zip_code", ""))

        full_address = ", ".join(filter(None, address_parts + [city, state, zip_val]))
        if not full_address.strip():
            return None

        price_raw = row.get(
            "opening_bid",
            row.get("sale_price", row.get("estimated_value", row.get("price", ""))),
        )
        try:
            price = float(price_raw.replace("$", "").replace(",", ""))
        except ValueError, TypeError:
            price = None

        return {
            "id": row.get(
                "case_number",
                row.get("parcel_number", f"tx-{county_key}-{hash(full_address)}"),
            ),
            "address": full_address,
            "price": price,
            "beds": row.get("beds", row.get("bedrooms")),
            "baths": row.get("baths", row.get("bathrooms")),
            "sqft": row.get("sqft", row.get("living_area", row.get("square_feet"))),
            "notice_type": row.get("notice_type", "foreclosure"),
            "sale_date": row.get("sale_date", row.get("auction_date")),
            "county": county_key,
        }

    @staticmethod
    def available_counties() -> List[str]:
        return list(TEXAS_COUNTY_FEEDS.keys())


class FloridaCountyForeclosureSource(DiscoverySource):
    """Florida county foreclosure notice source.

    Queries Florida county clerks for foreclosure auction sales.
    Supports CSV downloads and RSS feeds from major FL counties.
    """

    def __init__(self, county_key: str) -> None:
        self.county_key = county_key.lower()
        self._info = FLORIDA_COUNTY_FEEDS.get(
            county_key,
            {"name": county_key.title(), "state": "FL"},
        )

    @property
    def name(self) -> str:
        return f"fl_county_{self.county_key}"

    def fetch(
        self,
        state: str = "FL",
        zip_code: Optional[str] = None,
        limit: int = 200,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        url = self._info.get("foreclosure_url", "")
        logger.info("FL County %s: querying %s", self._info["name"], url)
        try:
            resp = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
            )
            if resp.status_code != 200:
                logger.info(
                    "FL County %s returned %d", self.county_key, resp.status_code
                )
                return []
            if "csv" in resp.headers.get("Content-Type", ""):
                reader = csv.DictReader(StringIO(resp.text))
                listings: list[dict[str, Any]] = []
                for row in reader:
                    if len(listings) >= limit:
                        break
                    addr = row.get("property_address", row.get("address", ""))
                    if not addr:
                        continue
                    mapped = TexasCountyForeclosureSource._map_county_row(
                        row, self.county_key
                    )
                    if mapped:
                        listings.append(mapped)
                logger.info(
                    "FL County %s: %d CSV listings", self.county_key, len(listings)
                )
                return listings
        except Exception as exc:
            logger.warning("FL County %s error: %s", self.county_key, exc)
        return []

    @staticmethod
    def available_counties() -> List[str]:
        return list(FLORIDA_COUNTY_FEEDS.keys())


def _fetch_via_playwright(url: str) -> str | None:
    """Fetch page HTML via Playwright headless Chromium (county sites are JS-rendered).

    Returns the rendered HTML string, or None on failure.  Playwright must
    be installed (requirements.txt) with browsers fetched via
    ``playwright install chromium``.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("playwright not installed — cannot render county pages")
        return None

    try:
        with sync_playwright() as pw:
            with pw.chromium.launch(headless=True) as browser:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()
                response = page.goto(
                    url, timeout=TIMEOUT * 1000, wait_until="domcontentloaded"
                )
                if response is None or response.status >= 400:
                    logger.warning(
                        "Page returned %s for %s",
                        getattr(response, "status", "?"),
                        url,
                    )
                    return None
                return str(page.content())
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return None
