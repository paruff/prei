from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import ForeclosureProperty


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return APIClient()


@pytest.fixture
def sample_foreclosure_properties(db):
    """Create sample foreclosure properties for testing."""
    now = timezone.now()

    properties = []

    # Miami, FL - Auction scheduled
    properties.append(
        ForeclosureProperty.objects.create(
            property_id="FH-FL-2024-12345",
            data_source="ATTOM",
            data_timestamp=now,
            street="123 Ocean Drive",
            city="Miami",
            county="Miami-Dade County",
            state="FL",
            zip_code="33139",
            latitude=Decimal("25.7617"),
            longitude=Decimal("-80.1918"),
            foreclosure_status="auction",
            foreclosure_stage="Notice of Trustee Sale",
            filing_date=now.date(),
            auction_date=(now + timezone.timedelta(days=12)).date(),
            auction_time="10:00 AM EST",
            auction_location="Miami-Dade County Courthouse, 73 W Flagler St",
            opening_bid=Decimal("425000"),
            unpaid_balance=Decimal("480000"),
            lender_name="Wells Fargo Bank",
            case_number="2024-FC-12345",
            trustee_name="ABC Foreclosure Services",
            trustee_phone="305-555-0100",
            property_type="single-family",
            bedrooms=3,
            bathrooms=Decimal("2.5"),
            square_footage=1850,
            lot_size=5400,
            year_built=2005,
            stories=2,
            garage="2-car attached",
            pool=False,
            condition="Fair",
            estimated_value=Decimal("550000"),
            last_sale_price=Decimal("380000"),
            last_sale_date=now.date(),
            tax_assessed_value=Decimal("520000"),
            annual_taxes=Decimal("7800"),
            images=["https://example.com/img1.jpg"],
            property_detail_url="https://example.com/property/12345",
        )
    )

    # Miami, FL - Pre-foreclosure
    properties.append(
        ForeclosureProperty.objects.create(
            property_id="FH-FL-2024-12346",
            data_source="ATTOM",
            data_timestamp=now,
            street="456 Beach Ave",
            city="Miami",
            county="Miami-Dade County",
            state="FL",
            zip_code="33140",
            latitude=Decimal("25.8000"),
            longitude=Decimal("-80.2000"),
            foreclosure_status="preforeclosure",
            foreclosure_stage="Notice of Default",
            filing_date=now.date(),
            auction_date=None,
            property_type="condo",
            bedrooms=2,
            bathrooms=Decimal("2.0"),
            square_footage=1200,
            lot_size=0,
            year_built=2010,
            estimated_value=Decimal("350000"),
        )
    )

    # Austin, TX - REO
    properties.append(
        ForeclosureProperty.objects.create(
            property_id="FH-TX-2024-98765",
            data_source="ATTOM",
            data_timestamp=now,
            street="789 Main St",
            city="Austin",
            county="Travis County",
            state="TX",
            zip_code="78701",
            foreclosure_status="reo",
            foreclosure_stage="Bank Owned",
            opening_bid=Decimal("600000"),
            property_type="single-family",
            bedrooms=4,
            bathrooms=Decimal("3.0"),
            square_footage=2500,
            year_built=2015,
        )
    )

    return properties


@pytest.mark.django_db
class TestForeclosuresAPI:
    """Integration tests for the foreclosures API."""

    def test_successful_retrieval_for_city_state(
        self, api_client, sample_foreclosure_properties
    ):
        """Test successful retrieval of foreclosures for city, state format."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "Miami, FL"})

        assert response.status_code == 200
        data = response.json()

        assert data["location"] == "Miami, FL"
        assert data["resultsCount"] == 2
        assert "dataTimestamp" in data
        assert "ATTOM" in data["dataSources"]
        assert len(data["properties"]) == 2

        # Check first property structure
        first_prop = data["properties"][0]
        assert "propertyId" in first_prop
        assert "address" in first_prop
        assert "foreclosureDetails" in first_prop
        assert "propertyDetails" in first_prop
        assert "valuationData" in first_prop
        assert "images" in first_prop
        assert "links" in first_prop

    def test_successful_retrieval_for_zip_code(
        self, api_client, sample_foreclosure_properties
    ):
        """Test successful retrieval of foreclosures by ZIP code."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "33139"})

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 1
        assert len(data["properties"]) == 1
        assert data["properties"][0]["propertyId"] == "FH-FL-2024-12345"

    def test_successful_retrieval_for_state_code(
        self, api_client, sample_foreclosure_properties
    ):
        """Test successful retrieval of foreclosures by state code."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "FL"})

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 2
        assert len(data["properties"]) == 2

    def test_filter_by_foreclosure_stage(
        self, api_client, sample_foreclosure_properties
    ):
        """Test filtering by foreclosure stage."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "FL", "stage": "auction"})

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 1
        assert data["properties"][0]["foreclosureDetails"]["status"] == "auction"

    def test_filter_by_multiple_stages(self, api_client, sample_foreclosure_properties):
        """Test filtering by multiple foreclosure stages."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(
            url, {"location": "FL", "stage": "auction,preforeclosure"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 2

    def test_filter_by_property_type(self, api_client, sample_foreclosure_properties):
        """Test filtering by property type."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(
            url, {"location": "FL", "propertyType": "single-family"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 1
        assert (
            data["properties"][0]["propertyDetails"]["propertyType"] == "single-family"
        )

    def test_filter_by_price_range(self, api_client, sample_foreclosure_properties):
        """Test filtering by price range."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(
            url, {"location": "FL", "minPrice": "400000", "maxPrice": "500000"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 1

    def test_filter_by_bedrooms(self, api_client, sample_foreclosure_properties):
        """Test filtering by bedroom count."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "FL", "minBeds": "3"})

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 1
        assert data["properties"][0]["propertyDetails"]["bedrooms"] == 3

    def test_filter_by_square_footage(self, api_client, sample_foreclosure_properties):
        """Test filtering by square footage."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(
            url, {"location": "FL", "minSqft": "1500", "maxSqft": "2000"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 1

    def test_sort_by_auction_date_ascending(
        self, api_client, sample_foreclosure_properties
    ):
        """Test sorting by auction date in ascending order."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(
            url, {"location": "FL", "sortBy": "auctionDate", "order": "asc"}
        )

        assert response.status_code == 200
        data = response.json()

        # Pre-foreclosure has no auction date, so should be last
        assert len(data["properties"]) == 2

    def test_pagination(self, api_client, sample_foreclosure_properties):
        """Test pagination functionality."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "FL", "page": "1", "limit": "1"})

        assert response.status_code == 200
        data = response.json()

        assert len(data["properties"]) == 1
        assert data["pagination"]["currentPage"] == 1
        assert data["pagination"]["totalPages"] == 2
        assert data["pagination"]["totalResults"] == 2
        assert data["pagination"]["resultsPerPage"] == 1

    def test_returns_400_for_missing_location(self, api_client):
        """Test that missing location parameter returns 400 error."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url)

        assert response.status_code == 400
        data = response.json()

        assert "error" in data
        assert data["code"] == "INVALID_LOCATION"
        assert "validFormats" in data

    def test_returns_400_for_invalid_foreclosure_stage(
        self, api_client, sample_foreclosure_properties
    ):
        """Test that invalid foreclosure stage returns 400 error."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "FL", "stage": "invalid_stage"})

        assert response.status_code == 400
        data = response.json()

        assert data["code"] == "INVALID_PARAMETER"

    def test_returns_400_for_invalid_property_type(
        self, api_client, sample_foreclosure_properties
    ):
        """Test that invalid property type returns 400 error."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(
            url, {"location": "FL", "propertyType": "invalid_type"}
        )

        assert response.status_code == 400
        data = response.json()

        assert data["code"] == "INVALID_PARAMETER"

    def test_returns_empty_list_for_area_with_no_foreclosures(self, api_client, db):
        """Test that areas with no foreclosures return empty list with message."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "WY"})

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 0
        assert len(data["properties"]) == 0
        assert "message" in data
        assert "No foreclosure properties found" in data["message"]

    def test_response_includes_data_sources(
        self, api_client, sample_foreclosure_properties
    ):
        """Test that response includes data sources."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "FL"})

        assert response.status_code == 200
        data = response.json()

        assert "dataSources" in data
        assert "ATTOM" in data["dataSources"]

    def test_location_parsing_county(self, api_client, sample_foreclosure_properties):
        """Test location parsing for county name."""
        url = reverse("api:foreclosures-list")
        response = api_client.get(url, {"location": "Miami-Dade County"})

        assert response.status_code == 200
        data = response.json()

        assert data["resultsCount"] == 2
