"""VRM Properties scraper for VA REO listing collection by state."""

from __future__ import annotations

import json
import logging
import re
import time
from decimal import Decimal
from typing import Any, cast

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

    def __init__(self, delay_seconds: float | None = None) -> None:
        default_delay = getattr(settings, "SCRAPER_DELAY_SECONDS", 1.5)
        self.delay_seconds = float(
            default_delay if delay_seconds is None else delay_seconds
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        params: dict[str, str | int] = {
            "state": state_code,
            "currentPage": page,
            "orderBy": "days desc",
        }
        response = requests.get(
            f"{self.BASE_URL}{self.LISTINGS_PATH}",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return str(response.text)

    def fetch_property_detail(self, listing_url: str) -> str:
        """Fetch a single VRM detail page."""
        response = requests.get(listing_url, timeout=30)
        response.raise_for_status()
        return str(response.text)

    def extract_property_details_from_html(self, html: str) -> dict[str, Any]:
        """Extract enrichment fields from a VRM property detail page."""
        soup = BeautifulSoup(html, "html.parser")
        details: dict[str, Any] = {
            "latitude": None,
            "longitude": None,
            "year_built": None,
            "lot_size_sf": None,
            "parcel_number": None,
            "mls_id": None,
            "property_type": None,
            "occupied": None,
            "county": None,
            "vendee_eligible": self._has_vendee_badge(soup),
        }

        details.update(self._extract_geo_position(soup))
        details.update(self._extract_house_facts(soup))
        details["county"] = self._extract_county_from_breadcrumb(soup)
        return details

    # ------------------------------------------------------------------
    # Listing-page parsing (JSON-model based)
    # ------------------------------------------------------------------

    def extract_total_pages(self, html: str) -> int:
        """Extract total pagination page count from the embedded JSON model."""
        soup = BeautifulSoup(html, "html.parser")
        model = self._extract_json_model(soup)
        if model is not None:
            total_pages = model.get("totalPages")
            if isinstance(total_pages, int) and total_pages >= 1:
                return total_pages

        # Fallback: try text-based extraction
        count_text = soup.get_text(" ", strip=True)
        for p in (r"of\s+(\d+)", r"(\d+)\s+results"):
            match = re.search(p, count_text, flags=re.IGNORECASE)
            if match:
                total_results = int(match.group(1))
                return max(1, -(-total_results // self.RESULTS_PER_PAGE))  # ceil

        return 1

    def extract_properties_from_html(self, html: str) -> list[dict[str, Any]]:
        """Extract VRM property cards from the embedded JSON model.

        The VRM site now renders property data via a ``<script>`` tag
        containing ``propertySearchResultsModelJson`` — a JSON object
        with a ``properties`` array.  We parse that instead of scraping
        CSS classes from the DOM.
        """
        soup = BeautifulSoup(html, "html.parser")
        model = self._extract_json_model(soup)
        if model is None:
            logger.warning("No propertySearchResultsModelJson found in page HTML")
            return []

        raw_properties: list[dict[str, Any]] = model.get("properties") or []
        seen_ids: set[int] = set()
        result: list[dict[str, Any]] = []

        for raw in raw_properties:
            prop = self._json_to_property(raw)
            if prop is None:
                continue

            pid = prop["vrm_property_id"]
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            result.append(prop)

        return result

    # ------------------------------------------------------------------
    # JSON-model helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_model(soup: BeautifulSoup) -> dict[str, Any] | None:
        """Find and parse ``propertySearchResultsModelJson`` from a ``<script>`` tag."""
        pattern = re.compile(
            r"var\s+propertySearchResultsModelJson\s*=\s*(\{.*?\});",
            re.DOTALL,
        )
        for script in soup.find_all("script"):
            text = script.string
            if not text:
                continue
            match = pattern.search(text)
            if match:
                try:
                    return cast("dict[str, Any]", json.loads(match.group(1)))
                except json.JSONDecodeError as exc:
                    logger.warning("Failed to parse property JSON model: %s", exc)
                    return None
        return None

    def _json_to_property(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        """Convert a single JSON property object into our normalized schema.

        Returns ``None`` when the record has no usable identifier or
        address — those listings are incomplete placeholders.
        """
        raw_id = raw.get("assetId")
        if not isinstance(raw_id, int) or raw_id <= 0:
            return None

        # --- map known fields ---
        prop: dict[str, Any] = {
            "vrm_property_id": raw_id,
            "vendee_eligible": bool(raw.get("isVendeeFinancing", False)),
        }

        # address: combine line1 + line2
        addr = (raw.get("addressLine1") or "").strip()
        addr2 = (raw.get("addressLine2") or "").strip()
        if addr2:
            addr = f"{addr} {addr2}"
        prop["address"] = addr

        prop["city"] = (raw.get("city") or "").strip().title()
        prop["state"] = (raw.get("state") or "").strip().upper()
        prop["zip_code"] = str(raw.get("zip") or "").strip()

        # price: treat 0 / None as "not listed"
        price_raw = raw.get("listPrice")
        if isinstance(price_raw, (int, float)) and price_raw > 0:
            prop["list_price"] = Decimal(str(price_raw))
        else:
            prop["list_price"] = None

        # numeric fields
        prop["bedrooms"] = self._json_int(raw.get("bedrooms"))
        prop["bathrooms"] = self._json_decimal(raw.get("bathrooms"))
        prop["square_feet"] = self._json_int(raw.get("squareFootage"))

        # status
        status_str = (raw.get("assetListingStatus") or "").strip()
        prop["status"] = self._normalize_json_status(status_str)

        # listing type
        prop["listing_type"] = self._json_listing_type(raw)

        # listing URL
        prop["vrm_listing_url"] = self._build_listing_url(prop)

        return prop

    @staticmethod
    def _json_int(value: Any) -> int | None:
        """Safely cast a JSON number to ``int``."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _json_decimal(value: Any) -> Decimal | None:
        """Safely cast a JSON number to ``Decimal``."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_json_status(status_str: str) -> str:
        """Map VRM's ``assetListingStatus`` to our ``VrmProperty.Status`` choices."""
        if not status_str:
            return VrmProperty.Status.FOR_SALE
        normalized = status_str.lower().strip()
        if "coming" in normalized:
            return VrmProperty.Status.COMING_SOON
        if "pending" in normalized or "under contract" in normalized:
            return VrmProperty.Status.PENDING
        if "sold" in normalized:
            return VrmProperty.Status.SOLD
        return VrmProperty.Status.FOR_SALE

    @staticmethod
    def _json_listing_type(raw: dict[str, Any]) -> str:
        """Determine listing type from JSON auction flags."""
        if raw.get("isOnlineAuction"):
            return VrmProperty.ListingType.ONLINE_AUCTION
        if raw.get("isAuction"):
            return VrmProperty.ListingType.IN_PERSON_AUCTION
        return VrmProperty.ListingType.TRADITIONAL

    @staticmethod
    def _build_listing_url(prop: dict[str, Any]) -> str:
        """Construct the VRM listing detail URL from property components."""
        pid = prop["vrm_property_id"]
        # Build slug: "123 Main St, City, ST 12345" -> "123-main-st-city-st-12345"
        parts = [
            prop.get("address", ""),
            prop.get("city", ""),
            prop.get("state", ""),
            prop.get("zip_code", ""),
        ]
        slug = "-".join(p for p in parts if p)
        slug = slug.lower().replace(" ", "-")
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        return f"{VrmScraper.BASE_URL}/Property-For-Sale/{pid}/{slug}"

    def _extract_geo_position(self, soup: BeautifulSoup) -> dict[str, Decimal | None]:
        """Parse latitude/longitude from the geo.position meta tag."""
        geo_meta = soup.find("meta", attrs={"name": "geo.position"})
        content = geo_meta.get("content") if geo_meta else None
        if not isinstance(content, str) or ";" not in content:
            return {"latitude": None, "longitude": None}

        latitude_text, longitude_text = content.split(";", 1)
        try:
            return {
                "latitude": Decimal(latitude_text.strip()),
                "longitude": Decimal(longitude_text.strip()),
            }
        except Exception:
            return {"latitude": None, "longitude": None}

    def _extract_house_facts(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse common fields from detail-page house-facts table rows."""
        facts: dict[str, Any] = {
            "year_built": None,
            "lot_size_sf": None,
            "parcel_number": None,
            "mls_id": None,
            "property_type": None,
            "occupied": None,
        }
        key_map: dict[str, str] = {
            "year built": "year_built",
            "lot": "lot_size_sf",
            "parcel number": "parcel_number",
            "mls id": "mls_id",
            "property type": "property_type",
            "occupied": "occupied",
        }

        for row in soup.select("table tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            raw_key = (
                str(cells[0].get_text(" ", strip=True)).strip().lower().rstrip(":")
            )
            raw_value = str(cells[1].get_text(" ", strip=True)).strip()
            if not raw_key or not raw_value:
                continue
            field_name = key_map.get(raw_key)
            if field_name is None:
                continue
            if field_name == "year_built":
                facts[field_name] = self._parse_int(raw_value)
            elif field_name == "lot_size_sf":
                facts[field_name] = self._parse_lot_size_sf(raw_value)
            elif field_name == "occupied":
                facts[field_name] = self._parse_occupied(raw_value)
            else:
                facts[field_name] = raw_value

        return facts

    def _parse_lot_size_sf(self, raw_value: str) -> int | None:
        """Parse lot size into square feet from mixed lot-size strings."""
        value = raw_value.lower()
        if "acre" in value:
            acre_match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", value)
            if not acre_match:
                return None
            acres = Decimal(acre_match.group(0).replace(",", ""))
            return int(acres * Decimal("43560"))

        return self._parse_int(raw_value)

    def _parse_occupied(self, raw_value: str) -> bool | None:
        """Parse occupied values into booleans when possible."""
        normalized = raw_value.strip().lower()
        if normalized in {"yes", "y", "true", "occupied"}:
            return True
        if normalized in {"no", "n", "false", "vacant", "not occupied"}:
            return False
        return None

    def _extract_county_from_breadcrumb(self, soup: BeautifulSoup) -> str | None:
        """Extract county from breadcrumb level 2 link text when present."""
        breadcrumb_links = soup.select(
            "nav[aria-label*='breadcrumb' i] a, .breadcrumb a, ol.breadcrumb a"
        )
        breadcrumb_texts = [
            str(link.get_text(" ", strip=True)).strip()
            for link in breadcrumb_links
            if str(link.get_text(" ", strip=True)).strip()
        ]
        if len(breadcrumb_texts) >= 2:
            return breadcrumb_texts[1]
        return None

    def _has_vendee_badge(self, card_link: Any) -> bool:
        """Detect Vendee-eligible marker in the listing card."""
        return bool(
            card_link.select_one(
                "img[alt*='vendee' i], img[src*='vendee' i], [class*='vendee' i]"
            )
        )

    # ------------------------------------------------------------------
    # Detail-page helpers (kept for enrich_vrm_details command)
    # ------------------------------------------------------------------

    def _parse_int(self, value: str) -> int | None:
        """Parse an integer from mixed display text."""
        numeric_token = self._extract_numeric_token(value, allow_decimal=False)
        if numeric_token is None:
            return None
        return int(numeric_token)

    @staticmethod
    def _extract_numeric_token(value: str, allow_decimal: bool) -> str | None:
        """Extract a sanitized numeric token, optionally allowing decimal places."""
        if not value:
            return None
        pattern = r"\d+(?:,\d{3})*(?:\.\d+)?" if allow_decimal else r"\d+(?:,\d{3})*"
        match = re.search(pattern, value)
        if not match:
            return None
        return match.group(0).replace(",", "")
