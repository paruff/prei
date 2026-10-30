"""Fannie Mae HomePath REO listing client.

Fetches public REO property listings from Fannie Mae's HomePath website.

⚠️ Known Limitation
-------------------
homepath.com uses a strict Cloudflare WAF that blocks all programmatic
access (HTTP 403).  Even Playwright with a realistic browser profile is
blocked.  The client handles this gracefully by returning empty results
and logging a warning.  Actual property discovery requires:

1. A paid real estate data API that includes Fannie Mae REO inventory
2. A residential proxy pool (future enhancement)
3. Manual CSV/JSON import (future admin upload)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.conf import settings

logger = logging.getLogger("prei.scraper.fannie_mae")

# Number of seconds to wait between page requests
_DEFAULT_DELAY = 1.5


class FannieMaeHomePathClient:
    """Best-effort client for Fannie Mae HomePath REO listings.

    Attempts to fetch listings from homepath.com.  Returns empty results
    with a warning log when the site blocks programmatic access.
    """

    BASE_URL = "https://www.homepath.com"
    SEARCH_PATH = "/search.html"

    def __init__(self, delay_seconds: float | None = None) -> None:
        self.delay_seconds = float(
            delay_seconds
            if delay_seconds is not None
            else getattr(settings, "SCRAPER_DELAY_SECONDS", _DEFAULT_DELAY)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_by_location(self, location: str) -> list[dict[str, Any]]:
        """Search properties by city/state or ZIP code.

        Returns a list of normalized property dicts (see module docstring
        for schema).  Returns an empty list with a logged warning if the
        site blocks access.
        """
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

        logger.info("Fannie Mae: searching location=%s", location)

        with sync_playwright() as pw:
            try:
                with pw.chromium.launch(headless=True) as browser:
                    context = browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1920, "height": 1080},
                        locale="en-US",
                    )
                    page = context.new_page()

                    url = f"{self.BASE_URL}{self.SEARCH_PATH}?search={location}"
                    response = page.goto(
                        url, wait_until="domcontentloaded", timeout=30_000
                    )
                    status = response.status if response else 0

                    if status == 403 or self._detect_blocked(page):
                        logger.warning(
                            "Fannie Mae HomePath WAF blocked access "
                            "(HTTP %s). Returning empty results.",
                            status,
                        )
                        return []

                    if status != 200:
                        logger.warning(
                            "Fannie Mae HomePath returned HTTP %s for %s. "
                            "Returning empty results.",
                            status,
                            location,
                        )
                        return []

                    html = page.content()
                    return self._parse_listing_cards(html)

            except Exception as exc:
                logger.warning(
                    "Fannie Mae HomePath request failed for %s: %s. "
                    "Returning empty results.",
                    location,
                    exc,
                )
                return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_blocked(page: Any) -> bool:
        """Check if the page is a Cloudflare challenge or block page."""
        title = str(page.title()).lower()
        content = str(page.content()).lower()
        return bool(
            "cloudflare" in content
            or "checking your browser" in content
            or "the request could not be satisfied" in title
        )

    @staticmethod
    def _parse_listing_cards(html: str) -> list[dict[str, Any]]:
        """Extract property data from HomePath search results HTML.

        Returns a list of normalized dicts matching the convention defined
        in ``core/integrations/sources/__init__.py``.
        """
        # Note: this parser is a scaffold.  When HomePath becomes accessible
        # (via proxy or API), populate the selectors from the actual page
        # structure.  The docstring below documents the expected schema.
        #
        # Expected HTML structure (from homepath.com):
        #   <div class="property-card">
        #     <div class="property-address">123 Main St</div>
        #     <div class="property-city-state">Austin, TX 78701</div>
        #     <div class="property-price">$250,000</div>
        #     <div class="property-details">
        #       <span class="beds">3</span> bed
        #       <span class="baths">2</span> bath
        #       <span class="sqft">1,500</span> sqft
        #     </div>
        #     <a class="property-link" href="/listing/...">Details</a>
        #     <div class="property-status">Active</div>
        #   </div>

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".property-card")
        results: list[dict[str, Any]] = []

        for card in cards:
            try:
                # These selectors are placeholders — adjust when site is
                # accessible to verify actual DOM structure.
                address_el = card.select_one(".property-address")
                city_el = card.select_one(".property-city-state")
                price_el = card.select_one(".property-price")
                details_el = card.select_one(".property-details")
                link_el = card.select_one("a.property-link")
                status_el = card.select_one(".property-status")

                if not address_el or not city_el:
                    continue

                address = address_el.get_text(strip=True)
                city_state = city_el.get_text(strip=True)

                # Parse "Austin, TX 78701" → city, state, zip
                city = ""
                state = ""
                zip_code = ""
                if "," in city_state:
                    parts = city_state.split(",")
                    city = parts[0].strip()
                    rest = parts[1].strip().split()
                    if len(rest) >= 2:
                        state = rest[0]
                        zip_code = rest[1]
                    elif rest:
                        state = rest[0]

                price = Decimal("0")
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price_text = price_text.replace("$", "").replace(",", "")
                    try:
                        price = Decimal(price_text)
                    except Exception:
                        price = Decimal("0")

                beds = 0
                baths = Decimal("0")
                sq_ft = 0
                if details_el:
                    beds_el = details_el.select_one(".beds")
                    baths_el = details_el.select_one(".baths")
                    sqft_el = details_el.select_one(".sqft")
                    if beds_el:
                        try:
                            beds = int(beds_el.get_text(strip=True))
                        except ValueError, TypeError:
                            pass
                    if baths_el:
                        try:
                            baths = Decimal(baths_el.get_text(strip=True))
                        except ValueError, TypeError:
                            pass
                    if sqft_el:
                        sqft_text = sqft_el.get_text(strip=True).replace(",", "")
                        try:
                            sq_ft = int(sqft_text)
                        except ValueError, TypeError:
                            pass

                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    # BeautifulSoup Tag.get() returns str | AttributeValueList
                    # in its type stubs.  For href attributes, it's always a
                    # string, so narrow the type to keep mypy happy.
                    if not isinstance(href, str):
                        href = ""
                    if href and not href.startswith("http"):
                        url = f"https://www.homepath.com{href}"
                    else:
                        url = href

                status = "Active"
                if status_el:
                    status = status_el.get_text(strip=True)

                results.append(
                    {
                        "source": "fannie_mae",
                        "address": address,
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                        "price": price,
                        "beds": beds,
                        "baths": baths,
                        "sq_ft": sq_ft,
                        "property_type": "SFH",
                        "url": url,
                        "status": status,
                    }
                )
            except Exception as exc:
                logger.warning("Fannie Mae: failed to parse listing card: %s", exc)
                continue

        logger.info("Fannie Mae: parsed %d listings", len(results))
        return results
