"""Tests for VRM listing scraper and collect_vrm_data command."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from core.integrations.sources.vrm_scraper import VrmScraper
from core.models import VrmProperty


class TestVrmScraper:
    """Test suite for VRM listing scraper."""

    @staticmethod
    def _mock_response(html: str) -> Mock:
        response = Mock()
        response.text = html
        response.raise_for_status.return_value = None
        return response

    def test_collect_state_listings_fetches_all_pages(self) -> None:
        """Scraper should detect total pages and fetch all pages for a state."""
        page_1_html = """
        <html><body>
            <div class="search-results-count">17 Results</div>
            <a class="property-card-link" href="/Property-For-Sale/18581/one">
                <div class="property-address">369 Charles St, Winchester, VA 22601</div>
                <div class="property-price">$175,000</div>
                <span class="beds">3 Beds</span>
                <span class="baths">2 Baths</span>
                <span class="sqft">1,504 Sq Ft</span>
                <span class="status-badge">For Sale</span>
            </a>
        </body></html>
        """
        page_2_html = """
        <html><body>
            <a class="property-card-link" href="/Property-For-Sale/18582/two">
                <div class="property-address">1 Main St, Richmond, VA 23220</div>
                <div class="property-price">$200,000</div>
                <span class="beds">4 Beds</span>
                <span class="baths">2.5 Baths</span>
                <span class="sqft">2,000 Sq Ft</span>
                <span class="status-badge">Pending</span>
            </a>
        </body></html>
        """

        scraper = VrmScraper(delay_seconds=0)

        with patch("core.integrations.sources.vrm_scraper.requests.get") as get_mock:
            get_mock.side_effect = [
                self._mock_response(page_1_html),
                self._mock_response(page_2_html),
            ]

            listings = scraper.collect_state_listings("VA")

        assert len(listings) == 2
        assert get_mock.call_count == 2

    def test_extract_properties_from_html_extracts_required_fields(self) -> None:
        """Parser should extract required fields from listing cards."""
        html = """
        <html><body>
            <a class="property-card-link" href="/Property-For-Sale/18581/369-charles-st">
                <div class="property-address">369 Charles St, Winchester, VA 22601</div>
                <div class="property-price">$175,000</div>
                <span class="beds">3 Beds</span>
                <span class="baths">2 Baths</span>
                <span class="sqft">1,504 Sq Ft</span>
                <span class="status-badge">For Sale</span>
                <img alt="Vendee" src="/images/vendee.png" />
                <span class="auction-badge">Online Auction</span>
            </a>
        </body></html>
        """

        scraper = VrmScraper(delay_seconds=0)
        properties = scraper.extract_properties_from_html(html)

        assert len(properties) == 1
        property_data = properties[0]
        assert property_data["vrm_property_id"] == 18581
        assert property_data["address"] == "369 Charles St"
        assert property_data["city"] == "Winchester"
        assert property_data["state"] == "VA"
        assert property_data["zip_code"] == "22601"
        assert property_data["list_price"] == Decimal("175000")
        assert property_data["bedrooms"] == 3
        assert property_data["bathrooms"] == Decimal("2")
        assert property_data["square_feet"] == 1504
        assert property_data["status"] == VrmProperty.Status.FOR_SALE
        assert property_data["vendee_eligible"] is True
        assert property_data["listing_type"] == VrmProperty.ListingType.ONLINE_AUCTION
        assert (
            property_data["vrm_listing_url"]
            == "https://vrmproperties.com/Property-For-Sale/18581/369-charles-st"
        )


@pytest.mark.django_db
class TestCollectVrmDataCommand:
    """Tests for collect_vrm_data management command."""

    def test_command_upserts_without_overwriting_scraped_at(self) -> None:
        """Re-runs should update existing records and preserve original scraped_at."""
        original_scraped_at = timezone.now() - timedelta(days=5)
        original_last_seen = timezone.now() - timedelta(days=2)
        existing = VrmProperty.objects.create(
            vrm_property_id=18581,
            vrm_listing_url="https://vrmproperties.com/Property-For-Sale/18581/old",
            address="Old Address",
            city="Winchester",
            state="VA",
            zip_code="22601",
            list_price=Decimal("100000"),
            bedrooms=2,
            bathrooms=Decimal("1.0"),
            square_feet=1200,
            status=VrmProperty.Status.FOR_SALE,
            listing_type=VrmProperty.ListingType.TRADITIONAL,
            vendee_eligible=False,
            scraped_at=original_scraped_at,
            last_seen_at=original_last_seen,
        )

        records = [
            {
                "vrm_property_id": 18581,
                "vrm_listing_url": "https://vrmproperties.com/Property-For-Sale/18581/new",
                "address": "369 Charles St",
                "city": "Winchester",
                "state": "VA",
                "zip_code": "22601",
                "list_price": Decimal("175000"),
                "bedrooms": 3,
                "bathrooms": Decimal("2.0"),
                "square_feet": 1504,
                "status": VrmProperty.Status.PENDING,
                "listing_type": VrmProperty.ListingType.ONLINE_AUCTION,
                "vendee_eligible": True,
            }
        ]

        with patch(
            "core.management.commands.collect_vrm_data.VrmScraper.collect_state_listings",
            return_value=records,
        ):
            call_command("collect_vrm_data", "--state", "VA")

        existing.refresh_from_db()
        assert VrmProperty.objects.count() == 1
        assert existing.address == "369 Charles St"
        assert existing.list_price == Decimal("175000")
        assert existing.status == VrmProperty.Status.PENDING
        assert existing.scraped_at == original_scraped_at
        assert existing.last_seen_at > original_last_seen

    def test_command_logs_no_properties_for_empty_state(self, caplog) -> None:
        """Empty scrape should log no properties and exit successfully."""
        caplog.set_level("INFO", logger="prei.scraper.vrm")

        with patch(
            "core.management.commands.collect_vrm_data.VrmScraper.collect_state_listings",
            return_value=[],
        ):
            call_command("collect_vrm_data", "--state", "ZZ")

        assert VrmProperty.objects.count() == 0
        assert "No properties found for state ZZ" in caplog.text

    def test_command_rejects_invalid_state_format(self) -> None:
        """Command should validate uppercase 2-letter state code."""
        with pytest.raises(
            CommandError, match="state must be a 2-letter uppercase code"
        ):
            call_command("collect_vrm_data", "--state", "va")

    def test_command_prints_collection_summary(self, capsys) -> None:
        """Command should print summary after a successful run."""
        records = [
            {
                "vrm_property_id": 99999,
                "vrm_listing_url": "https://vrmproperties.com/Property-For-Sale/99999/sample",
                "address": "10 Elm St",
                "city": "Richmond",
                "state": "VA",
                "zip_code": "23220",
                "list_price": Decimal("250000"),
                "bedrooms": 4,
                "bathrooms": Decimal("2.0"),
                "square_feet": 1800,
                "status": VrmProperty.Status.FOR_SALE,
                "listing_type": VrmProperty.ListingType.TRADITIONAL,
                "vendee_eligible": False,
            }
        ]

        with patch(
            "core.management.commands.collect_vrm_data.VrmScraper.collect_state_listings",
            return_value=records,
        ):
            call_command("collect_vrm_data", "--state", "VA")

        out = capsys.readouterr().out
        assert "Collected 1 properties for state VA" in out
