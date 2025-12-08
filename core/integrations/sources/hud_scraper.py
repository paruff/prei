"""HUD Home Store web scraper for government foreclosure listings."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HUDScraperError(Exception):
    """Base exception for HUD scraper errors."""

    pass


class HUDWebsiteChangeError(HUDScraperError):
    """HUD website structure has changed."""

    pass


class HUDHomeScraper:
    """
    Web scraper for HUD Home Store properties.

    Uses BeautifulSoup for HTML parsing. In production, this would use
    Playwright for JavaScript-rendered content.
    """

    BASE_URL = "https://www.hudhomestore.gov"

    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # CSS selectors - can be updated if website changes
    SELECTORS = {
        "property_listing": "div.property-listing",
        "address": "div.address",
        "case_number": "span.case-number",
        "price": "span.price",
        "beds": "span.beds",
        "baths": "span.baths",
        "sqft": "span.sqft",
        "type": "span.type",
        "listed": "span.listed",
        "bid_open": "span.bid-open",
        "bid_close": "span.bid-close",
        "status": "span.status",
        "next_page": "a.pagination-next:not(.disabled)",
    }

    # Alternative selectors if primary ones fail
    ALT_SELECTORS = {
        "property_listing": [
            "div.listing-item",
            "div.property-card",
            "article.property",
        ],
        "address": ["div.property-address", "span.address", "p.address"],
    }

    def __init__(self):
        """Initialize HUD scraper."""
        self.scraped_count = 0
        self.error_count = 0

    async def scrape_state(self, state_code: str) -> List[Dict[str, Any]]:
        """
        Scrape all HUD properties for a given state.

        Note: This is a placeholder implementation. For production use,
        see the TODO below for Playwright implementation details.

        TODO: Implement production scraper with Playwright
        Requirements for production implementation:
        1. Use Playwright to handle JavaScript-rendered content
        2. Navigate to HUD Home Store website
        3. Search for properties by state
        4. Extract property listings with pagination
        5. Handle rate limiting (2-5 seconds between requests)
        6. Implement robust error handling for website changes

        Example implementation approach:
        - Use async_playwright() context manager
        - Launch chromium browser in headless mode
        - Rotate user agents for requests
        - Implement exponential backoff on errors
        - Respect robots.txt directives

        Args:
            state_code: 2-letter state code (e.g., "FL", "CA")

        Returns:
            List of property dictionaries

        Raises:
            HUDScraperError: If scraping fails
        """
        logger.info(f"Starting HUD scrape for state: {state_code}")

        properties = []

        try:
            # Production implementation would use Playwright here
            logger.warning(
                f"HUD scraper for {state_code} is a placeholder - "
                "requires Playwright for production use"
            )

            # Simulate scraping delay
            await asyncio.sleep(random.uniform(2, 5))

            self.scraped_count = len(properties)
            logger.info(
                f"Completed HUD scrape for {state_code}: {len(properties)} properties"
            )

            return properties

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error scraping HUD for {state_code}: {str(e)}")
            raise HUDScraperError(f"Failed to scrape {state_code}: {str(e)}")

    def extract_properties_from_html(self, html: str) -> List[Dict[str, Any]]:
        """
        Extract property data from HTML page.

        Args:
            html: HTML content

        Returns:
            List of property dictionaries
        """
        soup = BeautifulSoup(html, "html.parser")
        properties = []

        # Try primary selector first
        listings = soup.select(self.SELECTORS["property_listing"])

        # If no results, try alternative selectors
        if not listings:
            for alt_selector in self.ALT_SELECTORS.get("property_listing", []):
                listings = soup.select(alt_selector)
                if listings:
                    logger.info(f"Using alternative selector: {alt_selector}")
                    break

        if not listings:
            logger.warning(
                "No property listings found - website structure may have changed"
            )
            raise HUDWebsiteChangeError("Could not find property listings in HTML")

        for listing in listings:
            try:
                property_data = self._extract_property_data(listing)
                properties.append(property_data)
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error extracting property data: {str(e)}")
                continue

        return properties

    def _extract_property_data(self, listing: Any) -> Dict[str, Any]:
        """
        Extract data from a single property listing element.

        Args:
            listing: BeautifulSoup element for property listing

        Returns:
            Property data dictionary
        """
        # Extract address
        address = self._extract_address(listing)

        # Extract other fields with safe extraction
        case_number = self._safe_extract_text(listing, self.SELECTORS["case_number"])
        price_text = self._safe_extract_text(listing, self.SELECTORS["price"])
        beds_text = self._safe_extract_text(listing, self.SELECTORS["beds"])
        baths_text = self._safe_extract_text(listing, self.SELECTORS["baths"])
        sqft_text = self._safe_extract_text(listing, self.SELECTORS["sqft"])
        prop_type = self._safe_extract_text(listing, self.SELECTORS["type"])
        listed_text = self._safe_extract_text(listing, self.SELECTORS["listed"])
        # bid_open_date not extracted - ForeclosureProperty model doesn't have this field
        # If needed in future, add bid_open_date field to model and extract here
        bid_close_text = self._safe_extract_text(listing, self.SELECTORS["bid_close"])
        status = self._safe_extract_text(listing, self.SELECTORS["status"])

        property_data = {
            "property_id": self.generate_property_id(address),
            "data_source": "HUD",
            "data_timestamp": datetime.now(),
            # Address
            "street": address.get("street", ""),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "zip_code": address.get("zip", ""),
            # HUD-specific
            "case_number": case_number,
            # Foreclosure details
            "foreclosure_status": "government",
            "opening_bid": self._parse_price(price_text),
            # Property details
            "property_type": self._map_property_type(prop_type),
            "bedrooms": self._parse_integer(beds_text),
            "bathrooms": self._parse_decimal(baths_text),
            "square_footage": self._parse_integer(sqft_text.replace(",", "")),
            # Dates
            "filing_date": self._parse_hud_date(listed_text),
            "auction_date": self._parse_hud_date(bid_close_text),
            # Status
            "foreclosure_stage": status,
        }

        return property_data

    def _extract_address(self, listing: Any) -> Dict[str, str]:
        """
        Extract and parse address components.

        Args:
            listing: BeautifulSoup element

        Returns:
            Dictionary with street, city, state, zip
        """
        address_text = self._safe_extract_text(listing, self.SELECTORS["address"])

        # If primary selector fails, try alternatives
        if not address_text:
            for alt_selector in self.ALT_SELECTORS.get("address", []):
                elem = listing.select_one(alt_selector)
                if elem:
                    address_text = elem.text.strip()
                    break

        if not address_text:
            return {"street": "", "city": "", "state": "", "zip": ""}

        # Parse address - common formats:
        # "123 Main St, Miami, FL 33139"
        # "456 Oak Ave\nAustin, TX 78701"

        address_text = address_text.replace("\n", ", ")
        parts = [p.strip() for p in address_text.split(",")]

        result = {"street": "", "city": "", "state": "", "zip": ""}

        if len(parts) >= 1:
            result["street"] = parts[0]

        if len(parts) >= 2:
            result["city"] = parts[1]

        if len(parts) >= 3:
            # Last part should be "STATE ZIP"
            state_zip = parts[2].strip()
            match = re.match(r"([A-Z]{2})\s+(\d{5})", state_zip)
            if match:
                result["state"] = match.group(1)
                result["zip"] = match.group(2)
            else:
                # Try to extract state code
                state_match = re.search(r"\b([A-Z]{2})\b", state_zip)
                if state_match:
                    result["state"] = state_match.group(1)
                # Try to extract ZIP
                zip_match = re.search(r"\b(\d{5})\b", state_zip)
                if zip_match:
                    result["zip"] = zip_match.group(1)

        return result

    def _safe_extract_text(self, listing: Any, selector: str) -> str:
        """
        Safely extract text from element.

        Args:
            listing: BeautifulSoup element
            selector: CSS selector

        Returns:
            Extracted text or empty string
        """
        try:
            elem = listing.select_one(selector)
            if elem:
                return elem.text.strip()
        except Exception as e:
            logger.debug(f"Failed to extract text with selector '{selector}': {str(e)}")

        return ""

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """
        Parse price text to Decimal.

        Args:
            price_text: Price string (e.g., "$425,000", "425000")

        Returns:
            Decimal value or None
        """
        if not price_text:
            return None

        try:
            # Remove $ and commas
            clean_price = price_text.replace("$", "").replace(",", "").strip()
            return Decimal(clean_price)
        except (ValueError, TypeError):
            return None

    def _parse_integer(self, text: str) -> int:
        """
        Parse integer from text.

        Args:
            text: Text containing integer

        Returns:
            Integer value or 0
        """
        if not text:
            return 0

        try:
            # Extract first number found
            match = re.search(r"\d+", text)
            if match:
                return int(match.group())
        except (ValueError, TypeError):
            pass

        return 0

    def _parse_decimal(self, text: str) -> Decimal:
        """
        Parse decimal from text.

        Args:
            text: Text containing decimal

        Returns:
            Decimal value or 0
        """
        if not text:
            return Decimal("0")

        try:
            # Extract decimal number
            match = re.search(r"\d+\.?\d*", text)
            if match:
                return Decimal(match.group())
        except (ValueError, TypeError):
            pass

        return Decimal("0")

    def _parse_hud_date(self, date_text: str) -> Optional[str]:
        """
        Parse HUD date format to ISO date.

        Args:
            date_text: Date string from HUD

        Returns:
            ISO formatted date string or None
        """
        if not date_text:
            return None

        try:
            from datetime import datetime as dt

            # Common HUD date formats
            formats = [
                "%m/%d/%Y",
                "%Y-%m-%d",
                "%B %d, %Y",  # "January 15, 2024"
                "%b %d, %Y",  # "Jan 15, 2024"
            ]

            for fmt in formats:
                try:
                    parsed_date = dt.strptime(date_text, fmt)
                    return parsed_date.date().isoformat()
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def _map_property_type(self, prop_type: str) -> str:
        """
        Map HUD property type to internal type.

        Args:
            prop_type: HUD property type string

        Returns:
            Internal property type
        """
        prop_type_lower = prop_type.lower()

        if "single" in prop_type_lower or "sfr" in prop_type_lower:
            return "single-family"
        elif "condo" in prop_type_lower:
            return "condo"
        elif "multi" in prop_type_lower or "duplex" in prop_type_lower:
            return "multi-family"
        elif "commercial" in prop_type_lower:
            return "commercial"

        return "single-family"

    def generate_property_id(self, address: Dict[str, str]) -> str:
        """
        Generate deterministic ID from address.

        Args:
            address: Address dictionary

        Returns:
            Unique property ID
        """
        address_str = (
            f"{address.get('street', '')}"
            f"{address.get('city', '')}"
            f"{address.get('state', '')}"
            f"{address.get('zip', '')}"
        )
        hash_value = hashlib.md5(address_str.encode()).hexdigest()[:12]
        return f"HUD-{hash_value}"


def fetch(state_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch HUD properties for a state.

    This is a synchronous wrapper for the async scraper.

    Args:
        state_code: Optional 2-letter state code

    Returns:
        List of property dictionaries
    """
    if not state_code:
        logger.warning("HUD fetch called without state code")
        return []

    scraper = HUDHomeScraper()

    # Run async scraper in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, return empty list (would need proper async handling)
            logger.warning("Event loop already running - cannot run async scraper")
            return []
        else:
            return loop.run_until_complete(scraper.scrape_state(state_code))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(scraper.scrape_state(state_code))
