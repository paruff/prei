"""Tests for Fannie Mae HomePath scraper client."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse


from core.integrations.sources.fannie_mae import FannieMaeHomePathClient

# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

_SAMPLE_LISTING_HTML = """
<div class="property-card">
    <div class="property-address">123 Main St</div>
    <div class="property-city-state">Austin, TX 78701</div>
    <div class="property-price">$250,000</div>
    <div class="property-details">
        <span class="beds">3</span> bed
        <span class="baths">2</span> bath
        <span class="sqft">1,500</span> sqft
    </div>
    <a class="property-link" href="/listing/abc123">Details</a>
    <div class="property-status">Active</div>
</div>
<div class="property-card">
    <div class="property-address">456 Oak Ave</div>
    <div class="property-city-state">Austin, TX 78702</div>
    <div class="property-price">$185,000</div>
    <div class="property-details">
        <span class="beds">2</span> bed
        <span class="baths">1</span> bath
        <span class="sqft">950</span> sqft
    </div>
    <a class="property-link" href="/listing/def456">Details</a>
    <div class="property-status">Active</div>
</div>
"""

_EMPTY_HTML = "<html><head></head><body></body></html>"

_CLOUDFLARE_BLOCK_HTML = """
<html><head><title>ERROR: The request could not be satisfied</title></head>
<body><p>Cloudflare WAF blocked this request.</p></body></html>
"""


# ---------------------------------------------------------------------------
# _parse_listing_cards
# ---------------------------------------------------------------------------


class TestParseListingCards:
    """Direct parsing tests (no network)."""

    def test_parses_valid_listings(self) -> None:
        """Happy path: extract fields from well-formed HTML."""
        results = FannieMaeHomePathClient._parse_listing_cards(_SAMPLE_LISTING_HTML)
        assert len(results) == 2

        first = results[0]
        assert first["source"] == "fannie_mae"
        assert first["address"] == "123 Main St"
        assert first["city"] == "Austin"
        assert first["state"] == "TX"
        assert first["zip_code"] == "78701"
        assert first["price"] == Decimal("250000")
        assert first["beds"] == 3
        assert first["baths"] == Decimal("2")
        assert first["sq_ft"] == 1500
        assert first["status"] == "Active"
        parsed_url = urlparse(first["url"])
        assert parsed_url.netloc == "www.homepath.com"

        second = results[1]
        assert second["address"] == "456 Oak Ave"
        assert second["price"] == Decimal("185000")
        assert second["beds"] == 2

    def test_returns_empty_list_for_empty_html(self) -> None:
        """Empty HTML produces empty results."""
        results = FannieMaeHomePathClient._parse_listing_cards(_EMPTY_HTML)
        assert results == []

    def test_skips_malformed_cards(self) -> None:
        """Cards missing address are skipped without crashing."""
        html = """
        <div class="property-card">
            <div class="property-price">$100</div>
        </div>
        <div class="property-card">
            <div class="property-address">789 Pine St</div>
            <div class="property-city-state">Dallas, TX 75201</div>
        </div>
        """
        results = FannieMaeHomePathClient._parse_listing_cards(html)
        assert len(results) == 1
        assert results[0]["address"] == "789 Pine St"

    def test_handles_missing_price(self) -> None:
        """Card without a price defaults to Decimal('0')."""
        html = """
        <div class="property-card">
            <div class="property-address">101 Main</div>
            <div class="property-city-state">Dallas, TX 75201</div>
        </div>
        """
        results = FannieMaeHomePathClient._parse_listing_cards(html)
        assert len(results) == 1
        assert results[0]["price"] == Decimal("0")

    def test_handles_missing_details(self) -> None:
        """Card without details section defaults beds/baths/sqft to 0."""
        html = """
        <div class="property-card">
            <div class="property-address">101 Main</div>
            <div class="property-city-state">Dallas, TX 75201</div>
            <div class="property-price">$200,000</div>
        </div>
        """
        results = FannieMaeHomePathClient._parse_listing_cards(html)
        assert len(results) == 1
        assert results[0]["beds"] == 0
        assert results[0]["baths"] == Decimal("0")
        assert results[0]["sq_ft"] == 0


# ---------------------------------------------------------------------------
# _detect_blocked
# ---------------------------------------------------------------------------


class TestDetectBlocked:
    """Cloudflare WAF block detection."""

    def test_detects_cloudflare_block(self) -> None:
        """Page with Cloudflare error is detected as blocked."""
        mock_page = MagicMock()
        mock_page.title.return_value = "ERROR: The request could not be satisfied"
        mock_page.content.return_value = _CLOUDFLARE_BLOCK_HTML

        assert FannieMaeHomePathClient._detect_blocked(mock_page) is True

    def test_passes_normal_page(self) -> None:
        """Normal page is not detected as blocked."""
        mock_page = MagicMock()
        mock_page.title.return_value = "Fannie Mae HomePath - Properties"
        mock_page.content.return_value = _SAMPLE_LISTING_HTML

        assert FannieMaeHomePathClient._detect_blocked(mock_page) is False

    def test_detects_short_content(self) -> None:
        """Very short page without block indicators is NOT treated as blocked."""
        mock_page = MagicMock()
        mock_page.title.return_value = "Fannie Mae HomePath"
        mock_page.content.return_value = "<html><body>short</body></html>"

        assert FannieMaeHomePathClient._detect_blocked(mock_page) is False


# ---------------------------------------------------------------------------
# search_by_location (mocked Playwright)
# ---------------------------------------------------------------------------


class TestSearchByLocation:
    """Integration via mocked Playwright."""

    def test_returns_listings_on_success(self) -> None:
        """Happy path: Playwright fetches page and returns parsed listings."""
        mock_page = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
        mock_page.title.return_value = "Fannie Mae HomePath - Search Results"
        mock_page.content.return_value = _SAMPLE_LISTING_HTML

        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser  # context manager
        mock_browser.__enter__.return_value = mock_browser  # context manager support
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_playwright = MagicMock()
        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser
        mock_playwright.chromium = mock_chromium

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.__enter__.return_value = mock_playwright

            client = FannieMaeHomePathClient(delay_seconds=0)
            results = client.search_by_location("Austin, TX")

        assert len(results) == 2
        assert results[0]["city"] == "Austin"

    def test_returns_empty_on_403(self) -> None:
        """Playwright receives HTTP 403 from Cloudflare → empty results."""
        mock_page = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 403
        mock_page.goto.return_value = mock_response
        mock_page.title.return_value = "ERROR: The request could not be satisfied"
        mock_page.content.return_value = _CLOUDFLARE_BLOCK_HTML

        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser  # context manager
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_playwright = MagicMock()
        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser
        mock_playwright.chromium = mock_chromium

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.__enter__.return_value = mock_playwright

            client = FannieMaeHomePathClient(delay_seconds=0)
            results = client.search_by_location("Austin, TX")

        assert results == []

    def test_returns_empty_on_exception(self) -> None:
        """Playwright raises an exception → empty results, no crash."""
        mock_playwright = MagicMock()
        mock_chromium = MagicMock()
        mock_chromium.launch.side_effect = Exception("Connection refused")
        mock_playwright.chromium = mock_chromium

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.__enter__.return_value = mock_playwright

            client = FannieMaeHomePathClient(delay_seconds=0)
            results = client.search_by_location("Austin, TX")

        assert results == []

    def test_returns_empty_on_blocked_page(self) -> None:
        """Non-403 but detected as blocked → empty results."""
        mock_page = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200  # but page content is blocked
        mock_page.goto.return_value = mock_response
        mock_page.title.return_value = "ERROR: The request could not be satisfied"
        mock_page.content.return_value = _CLOUDFLARE_BLOCK_HTML

        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser  # context manager
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_playwright = MagicMock()
        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser
        mock_playwright.chromium = mock_chromium

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.__enter__.return_value = mock_playwright

            client = FannieMaeHomePathClient(delay_seconds=0)
            results = client.search_by_location("Austin, TX")

        assert results == []
