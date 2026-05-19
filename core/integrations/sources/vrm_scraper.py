"""VRM Properties scraper for VA REO listing collection by state."""

from __future__ import annotations

import logging
import re
import time
from decimal import Decimal
from math import ceil
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from core.models import VrmProperty

logger = logging.getLogger("prei.scraper.vrm")


class VrmScraper:
    """Scrape VRM Properties listing pages and parse property cards."""

    BASE_URL = "https://vrmproperties.com"
    LISTINGS_PATH = "/Properties-For-Sale"
    RESULTS_PER_PAGE = 16

    def __init__(self, delay_seconds: Optional[float] = None) -> None:
        default_delay = getattr(settings, "SCRAPER_DELAY_SECONDS", 1.5)
        self.delay_seconds = float(
            default_delay if delay_seconds is None else delay_seconds
        )

    def collect_state_listings(self, state_code: str) -> list[dict[str, Any]]:
        """Collect all listing pages for a single state."""
        state = state_code.strip().upper()
        page = 1
        all_properties: list[dict[str, Any]] = []

        first_page_html = self._fetch_listing_page(state, page)
        first_page_properties = self.extract_properties_from_html(first_page_html)
        if not first_page_properties:
            return []

        total_pages = self.extract_total_pages(first_page_html)
        all_properties.extend(first_page_properties)

        for page in range(2, total_pages + 1):
            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds)
            html = self._fetch_listing_page(state, page)
            all_properties.extend(self.extract_properties_from_html(html))

        return all_properties

    def _fetch_listing_page(self, state_code: str, page: int) -> str:
        """Fetch one VRM listings page."""
        response = requests.get(
            f"{self.BASE_URL}{self.LISTINGS_PATH}",
            params={
                "state": state_code,
                "currentPage": page,
                "orderBy": "days desc",
            },
            timeout=30,
        )
        response.raise_for_status()
        return str(response.text)

    def extract_total_pages(self, html: str) -> int:
        """Extract total pagination page count from result count text."""
        soup = BeautifulSoup(html, "html.parser")
        count_selectors = [
            ".search-results-count",
            ".results-count",
            "[data-testid='results-count']",
        ]

        count_text = ""
        for selector in count_selectors:
            element = soup.select_one(selector)
            if element:
                count_text = element.get_text(" ", strip=True)
                break

        if not count_text:
            count_text = soup.get_text(" ", strip=True)

        matches = [
            re.search(r"of\s+(\d+)", count_text, flags=re.IGNORECASE),
            re.search(r"(\d+)\s+results", count_text, flags=re.IGNORECASE),
        ]
        for match in matches:
            if match:
                total_results = int(match.group(1))
                return max(1, ceil(total_results / self.RESULTS_PER_PAGE))

        return 1

    def extract_properties_from_html(self, html: str) -> list[dict[str, Any]]:
        """Extract VRM property cards from listing HTML."""
        soup = BeautifulSoup(html, "html.parser")
        properties: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        for card_link in soup.select("a[href*='/Property-For-Sale/']"):
            property_data = self._extract_property_data(card_link)
            if not property_data:
                continue

            property_id = int(property_data["vrm_property_id"])
            if property_id in seen_ids:
                continue

            seen_ids.add(property_id)
            properties.append(property_data)

        return properties

    def _extract_property_data(self, card_link: Any) -> Optional[Dict[str, Any]]:
        """Extract a normalized property dictionary from one card link element."""
        href = card_link.get("href")
        if not isinstance(href, str):
            return None

        match = re.search(r"/Property-For-Sale/(\d+)/", href)
        if not match:
            return None

        vrm_property_id = int(match.group(1))
        full_url = urljoin(f"{self.BASE_URL}/", href.lstrip("/"))

        address_text = self._extract_text(card_link, [".property-address", ".address"])
        address = self._parse_address(address_text)

        status_text = self._extract_text(
            card_link,
            [".status-badge", "[class*='status']", "[class*='badge']"],
        )
        listing_type_text = self._extract_text(
            card_link,
            [".auction-badge", "[class*='auction']"],
        )

        return {
            "vrm_property_id": vrm_property_id,
            "vrm_listing_url": full_url,
            "address": address["address"],
            "city": address["city"],
            "state": address["state"],
            "zip_code": address["zip_code"],
            "list_price": self._parse_decimal(
                self._extract_text(card_link, [".property-price", "[class*='price']"])
            ),
            "bedrooms": self._parse_int(
                self._extract_text(card_link, [".beds", "[class*='bed']"])
            ),
            "bathrooms": self._parse_decimal(
                self._extract_text(card_link, [".baths", "[class*='bath']"])
            ),
            "square_feet": self._parse_int(
                self._extract_text(card_link, [".sqft", "[class*='sqft']"])
            ),
            "status": self._normalize_status(status_text),
            "vendee_eligible": self._has_vendee_badge(card_link),
            "listing_type": self._normalize_listing_type(listing_type_text),
        }

    def _extract_text(self, node: Any, selectors: list[str]) -> str:
        """Extract text using the first matching selector."""
        for selector in selectors:
            element = node.select_one(selector)
            if element:
                return str(element.get_text(" ", strip=True))
        return ""

    def _parse_address(self, address_text: str) -> dict[str, str]:
        """Parse `street, city, ST ZIP` style addresses."""
        if not address_text:
            return {"address": "", "city": "", "state": "", "zip_code": ""}

        match = re.match(
            r"^\s*(.*?)\s*,\s*(.*?)\s*,\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\s*$",
            address_text,
        )
        if match:
            return {
                "address": match.group(1).strip(),
                "city": match.group(2).strip(),
                "state": match.group(3).strip(),
                "zip_code": match.group(4).strip(),
            }

        parts = [part.strip() for part in address_text.split(",") if part.strip()]
        if len(parts) >= 3:
            state_zip = parts[-1].split()
            state = state_zip[0].upper() if state_zip else ""
            zip_code = state_zip[1] if len(state_zip) > 1 else ""
            return {
                "address": parts[0],
                "city": parts[1],
                "state": state,
                "zip_code": zip_code,
            }

        return {
            "address": address_text.strip(),
            "city": "",
            "state": "",
            "zip_code": "",
        }

    def _parse_decimal(self, value: str) -> Optional[Decimal]:
        """Parse decimal numbers from mixed display text."""
        if not value:
            return None
        match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", value)
        if not match:
            return None
        return Decimal(match.group(0).replace(",", ""))

    def _parse_int(self, value: str) -> Optional[int]:
        """Parse an integer from mixed display text."""
        if not value:
            return None
        match = re.search(r"\d+(?:,\d{3})*", value)
        if not match:
            return None
        return int(match.group(0).replace(",", ""))

    def _normalize_status(self, status_text: str) -> str:
        """Map display status text to VrmProperty status choices."""
        normalized = status_text.strip().lower()
        if "coming" in normalized:
            return VrmProperty.Status.COMING_SOON
        if "pending" in normalized or "under contract" in normalized:
            return VrmProperty.Status.PENDING
        if "sold" in normalized:
            return VrmProperty.Status.SOLD
        return VrmProperty.Status.FOR_SALE

    def _normalize_listing_type(self, listing_type_text: str) -> Optional[str]:
        """Map listing type badges to model choices."""
        normalized = listing_type_text.strip().lower()
        if not normalized:
            return VrmProperty.ListingType.TRADITIONAL
        if "online" in normalized and "auction" in normalized:
            return VrmProperty.ListingType.ONLINE_AUCTION
        if "in-person" in normalized and "auction" in normalized:
            return VrmProperty.ListingType.IN_PERSON_AUCTION
        if "auction" in normalized:
            return VrmProperty.ListingType.ONLINE_AUCTION
        return VrmProperty.ListingType.TRADITIONAL

    def _has_vendee_badge(self, card_link: Any) -> bool:
        """Detect Vendee-eligible marker in the listing card."""
        return bool(
            card_link.select_one(
                "img[alt*='vendee' i], img[src*='vendee' i], [class*='vendee' i]"
            )
        )
