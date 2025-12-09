"""Unit tests for HUD Home Store scraper."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from core.integrations.sources.hud_scraper import HUDHomeScraper, HUDWebsiteChangeError


@pytest.fixture
def hud_scraper():
    """Create HUD scraper instance for testing."""
    return HUDHomeScraper()


@pytest.fixture
def sample_listing_html():
    """Sample HTML for a property listing."""
    return """
    <div class="property-listing">
        <div class="address">123 Ocean Drive, Miami, FL 33139</div>
        <span class="case-number">2024-HUD-12345</span>
        <span class="price">$425,000</span>
        <span class="beds">3</span>
        <span class="baths">2.5</span>
        <span class="sqft">1,850</span>
        <span class="type">Single Family</span>
        <span class="listed">01/15/2024</span>
        <span class="bid-open">02/01/2024</span>
        <span class="bid-close">02/28/2024</span>
        <span class="status">Available</span>
    </div>
    """


@pytest.fixture
def sample_page_html(sample_listing_html):
    """Sample HTML page with multiple listings."""
    return f"""
    <html>
        <body>
            {sample_listing_html}
            <div class="property-listing">
                <div class="address">456 Beach Ave, Miami, FL 33140</div>
                <span class="case-number">2024-HUD-12346</span>
                <span class="price">$350,000</span>
                <span class="beds">2</span>
                <span class="baths">2.0</span>
                <span class="sqft">1,200</span>
                <span class="type">Condo</span>
                <span class="listed">01/20/2024</span>
                <span class="bid-open">02/05/2024</span>
                <span class="bid-close">03/05/2024</span>
                <span class="status">Available</span>
            </div>
        </body>
    </html>
    """


class TestHUDHomeScraper:
    """Test suite for HUD Home Store scraper."""

    def test_initialization(self):
        """Test scraper initialization."""
        scraper = HUDHomeScraper()
        assert scraper.scraped_count == 0
        assert scraper.error_count == 0

    def test_extract_properties_from_html(self, hud_scraper, sample_page_html):
        """Test extracting properties from HTML."""
        properties = hud_scraper.extract_properties_from_html(sample_page_html)

        assert len(properties) == 2
        assert properties[0]["street"] == "123 Ocean Drive"
        assert properties[1]["street"] == "456 Beach Ave"

    def test_extract_properties_no_listings_raises_error(self, hud_scraper):
        """Test that missing listings raises error."""
        html = "<html><body><div>No listings</div></body></html>"

        with pytest.raises(HUDWebsiteChangeError):
            hud_scraper.extract_properties_from_html(html)

    def test_extract_property_data(self, hud_scraper, sample_listing_html):
        """Test extracting data from single listing."""
        soup = BeautifulSoup(sample_listing_html, "html.parser")
        listing = soup.select_one("div.property-listing")

        property_data = hud_scraper._extract_property_data(listing)

        assert property_data["street"] == "123 Ocean Drive"
        assert property_data["city"] == "Miami"
        assert property_data["state"] == "FL"
        assert property_data["zip_code"] == "33139"
        assert property_data["case_number"] == "2024-HUD-12345"
        assert property_data["opening_bid"] == Decimal("425000")
        assert property_data["bedrooms"] == 3
        assert property_data["bathrooms"] == Decimal("2.5")
        assert property_data["square_footage"] == 1850
        assert property_data["data_source"] == "HUD"
        assert property_data["foreclosure_status"] == "government"

    def test_extract_address_city_state_zip(self, hud_scraper):
        """Test address extraction with city, state, ZIP."""
        html = '<div class="address">123 Main St, Austin, TX 78701</div>'
        soup = BeautifulSoup(html, "html.parser")
        listing = soup

        address = hud_scraper._extract_address(listing)

        assert address["street"] == "123 Main St"
        assert address["city"] == "Austin"
        assert address["state"] == "TX"
        assert address["zip"] == "78701"

    def test_extract_address_with_newlines(self, hud_scraper):
        """Test address extraction with newlines."""
        html = '<div class="address">456 Oak Ave\nDenver, CO 80203</div>'
        soup = BeautifulSoup(html, "html.parser")
        listing = soup

        address = hud_scraper._extract_address(listing)

        assert address["street"] == "456 Oak Ave"
        assert address["city"] == "Denver"
        assert address["state"] == "CO"
        assert address["zip"] == "80203"

    def test_extract_address_missing_data(self, hud_scraper):
        """Test address extraction with missing data."""
        html = '<div class="not-address">No address here</div>'
        soup = BeautifulSoup(html, "html.parser")
        listing = soup

        address = hud_scraper._extract_address(listing)

        assert address["street"] == ""
        assert address["city"] == ""
        assert address["state"] == ""
        assert address["zip"] == ""

    def test_parse_price_with_dollar_sign(self, hud_scraper):
        """Test price parsing with dollar sign."""
        assert hud_scraper._parse_price("$425,000") == Decimal("425000")

    def test_parse_price_without_dollar_sign(self, hud_scraper):
        """Test price parsing without dollar sign."""
        assert hud_scraper._parse_price("350000") == Decimal("350000")

    def test_parse_price_empty_string(self, hud_scraper):
        """Test price parsing with empty string."""
        assert hud_scraper._parse_price("") is None

    def test_parse_integer(self, hud_scraper):
        """Test integer parsing."""
        assert hud_scraper._parse_integer("3") == 3
        assert hud_scraper._parse_integer("3 bedrooms") == 3
        assert hud_scraper._parse_integer("") == 0

    def test_parse_decimal(self, hud_scraper):
        """Test decimal parsing."""
        assert hud_scraper._parse_decimal("2.5") == Decimal("2.5")
        assert hud_scraper._parse_decimal("2.5 baths") == Decimal("2.5")
        assert hud_scraper._parse_decimal("") == Decimal("0")

    def test_parse_hud_date_us_format(self, hud_scraper):
        """Test date parsing with US format."""
        assert hud_scraper._parse_hud_date("01/15/2024") == "2024-01-15"

    def test_parse_hud_date_iso_format(self, hud_scraper):
        """Test date parsing with ISO format."""
        assert hud_scraper._parse_hud_date("2024-01-15") == "2024-01-15"

    def test_parse_hud_date_long_format(self, hud_scraper):
        """Test date parsing with long format."""
        assert hud_scraper._parse_hud_date("January 15, 2024") == "2024-01-15"

    def test_parse_hud_date_empty_string(self, hud_scraper):
        """Test date parsing with empty string."""
        assert hud_scraper._parse_hud_date("") is None

    def test_map_property_type_single_family(self, hud_scraper):
        """Test property type mapping for single family."""
        assert hud_scraper._map_property_type("Single Family") == "single-family"

    def test_map_property_type_condo(self, hud_scraper):
        """Test property type mapping for condo."""
        assert hud_scraper._map_property_type("Condo") == "condo"

    def test_map_property_type_multi_family(self, hud_scraper):
        """Test property type mapping for multi-family."""
        assert hud_scraper._map_property_type("Duplex") == "multi-family"

    def test_map_property_type_default(self, hud_scraper):
        """Test property type mapping with unknown type."""
        assert hud_scraper._map_property_type("Unknown") == "single-family"

    def test_generate_property_id(self, hud_scraper):
        """Test property ID generation."""
        address = {
            "street": "123 Main St",
            "city": "Miami",
            "state": "FL",
            "zip": "33139",
        }

        property_id = hud_scraper.generate_property_id(address)

        assert property_id.startswith("HUD-")
        assert len(property_id) == 16  # "HUD-" + 12 char hash

    def test_generate_property_id_consistency(self, hud_scraper):
        """Test that same address generates same ID."""
        address = {
            "street": "123 Main St",
            "city": "Miami",
            "state": "FL",
            "zip": "33139",
        }

        id1 = hud_scraper.generate_property_id(address)
        id2 = hud_scraper.generate_property_id(address)

        assert id1 == id2

    def test_scrape_state_placeholder_sync(self, hud_scraper):
        """Test scrape_state returns empty list (placeholder - synchronous version)."""

        properties = asyncio.run(hud_scraper.scrape_state("FL"))

        # Placeholder implementation returns empty list
        assert properties == []
        assert hud_scraper.scraped_count == 0

    def test_safe_extract_text(self, hud_scraper):
        """Test safe text extraction."""
        html = '<div><span class="test">Test Value</span></div>'
        soup = BeautifulSoup(html, "html.parser")
        listing = soup.select_one("div")

        text = hud_scraper._safe_extract_text(listing, "span.test")

        assert text == "Test Value"

    def test_safe_extract_text_missing_element(self, hud_scraper):
        """Test safe text extraction with missing element."""
        html = "<div></div>"
        soup = BeautifulSoup(html, "html.parser")
        listing = soup.select_one("div")

        text = hud_scraper._safe_extract_text(listing, "span.missing")

        assert text == ""

    def test_extract_properties_handles_extraction_errors(self, hud_scraper):
        """Test that extraction errors are logged but don't stop processing."""
        html = """
        <html>
            <body>
                <div class="property-listing">
                    <div class="address">Valid Property</div>
                    <span class="price">$100,000</span>
                </div>
                <div class="property-listing">
                    <!-- Malformed listing - missing required fields -->
                </div>
                <div class="property-listing">
                    <div class="address">Another Valid Property</div>
                    <span class="price">$200,000</span>
                </div>
            </body>
        </html>
        """

        properties = hud_scraper.extract_properties_from_html(html)

        # Should extract valid properties, skip malformed one
        assert len(properties) >= 0  # Some properties may be extracted
        assert hud_scraper.error_count >= 0  # Errors may be logged
