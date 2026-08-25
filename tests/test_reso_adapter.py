"""Tests for RESO Web API adapter."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from core.integrations.sources.reso_adapter import (
    RESOAdapter,
    normalize_property_type,
    normalize_property_data,
)


class TestPropertyTypeNormalization:
    """Tests for property type normalization."""

    def test_normalize_sfr(self) -> None:
        """Test single family residence normalization."""
        assert normalize_property_type("Single Family") == "SFR"
        assert normalize_property_type("Single Family Residence") == "SFR"
        assert normalize_property_type("SINGLE FAMILY") == "SFR"
        assert normalize_property_type("Single Family Detached") == "SFR"

    def test_normalize_condo(self) -> None:
        """Test condo normalization."""
        assert normalize_property_type("Condo") == "CONDO"
        assert normalize_property_type("Condominium") == "CONDO"

    def test_normalize_townhouse(self) -> None:
        """Test townhouse normalization."""
        assert normalize_property_type("Townhouse") == "TOWNHOUSE"
        assert normalize_property_type("Town House") == "TOWNHOUSE"

    def test_normalize_multi(self) -> None:
        """Test multi-family normalization."""
        assert normalize_property_type("Duplex") == "DUPLEX"
        assert normalize_property_type("Triplex") == "TRIPLEX"
        assert normalize_property_type("Fourplex") == "FOURPLEX"
        assert normalize_property_type("Multifamily") == "MULTIFAMILY"

    def test_normalize_unknown(self) -> None:
        """Test unknown type returns uppercase version."""
        assert normalize_property_type("Weird Type") == "WEIRD TYPE"
        assert normalize_property_type(None) is None
        assert normalize_property_type("") is None


class TestPropertyDataNormalization:
    """Tests for property data normalization."""

    @pytest.mark.django_db
    def test_normalize_complete_property(self) -> None:
        """Test normalizing complete property data."""

        raw = {
            "ListingId": "12345",
            "ListingKey": "LIST-123",
            "UnparsedAddress": "123 Main St",
            "StreetNumber": "123",
            "StreetName": "Main St",
            "City": "Austin",
            "StateOrProvince": "TX",
            "PostalCode": "78701",
            "ListPrice": "450000",
            "BedroomsTotal": "3",
            "BathroomsTotalInteger": "2",
            "LivingArea": "2000",
            "LotSizeSquareFeet": "7500",
            "PropertyType": "Single Family",
            "PropertySubType": "Detached",
            "YearBuilt": "2010",
            "LotSizeAcres": "0.25",
            "DaysOnMarket": "15",
            "StandardStatus": "Active",
            "ListingContractDate": "2024-01-15",
            "ExpirationDate": "2024-07-15",
            "MlsNumber": "1234567",
            "MlsId": "TX-123",
            "Latitude": "30.2672",
            "Longitude": "-97.7431",
            "Media": [
                {
                    "MediaURL": "https://example.com/photo1.jpg",
                    "MediaType": "Photo",
                    "Description": "Front view",
                    "Order": 1,
                },
                {
                    "MediaURL": "https://example.com/photo2.jpg",
                    "MediaType": "Photo",
                    "Order": 2,
                },
            ],
            "VirtualTourURL": "https://tour.example.com/123",
            "PublicRemarks": "Beautiful home in Austin",
            "PrivateRemarks": "Agent only remarks",
            "ListAgentKey": "AGENT123",
            "ListOfficeKey": "OFFICE456",
        }

        result = normalize_property_data(raw)

        assert result["source"] == "reso"
        assert result["listing_id"] == "12345"
        assert result["address"] == "123 Main St"
        assert result["city"] == "Austin"
        assert result["state"] == "TX"
        assert result["zip_code"] == "78701"
        assert result["price"] == 450000
        assert result["beds"] == 3
        assert result["baths"] == Decimal("2")
        assert result["sq_ft"] == 2000
        assert result["property_type"] == "SFR"
        assert result["property_sub_type"] == "Detached"
        assert result["year_built"] == 2010
        assert result["lot_size_acres"] == Decimal("0.25")
        assert result["days_on_market"] == 15
        assert result["listing_status"] == "Active"
        assert len(result["photos"]) == 2
        assert result["photos"][0]["url"] == "https://example.com/photo1.jpg"
        assert result["photos"][0]["order"] == 1
        assert result["virtual_tour_url"] == "https://tour.example.com/123"
        assert result["remarks"] == "Beautiful home in Austin"
        assert result["agent_id"] == "AGENT123"
        assert result["office_id"] == "OFFICE456"

    def test_normalize_minimal_property(self) -> None:
        """Test normalizing minimal property data."""

        raw = {
            "ListingId": "MIN-001",
            "UnparsedAddress": "456 Oak Ave",
            "City": "Dallas",
            "StateOrProvince": "TX",
            "PostalCode": "75201",
            "ListPrice": "300000",
        }

        result = normalize_property_data(raw)

        assert result["listing_id"] == "MIN-001"
        assert result["address"] == "456 Oak Ave"
        assert result["city"] == "Dallas"
        assert result["state"] == "TX"
        assert result["zip_code"] == "75201"
        assert result["price"] == 300000
        assert result["property_type"] is None  # Not provided
        assert result["photos"] == []


class TestRESOAdapter:
    """Tests for RESOAdapter class."""

    @pytest.fixture
    def adapter(self) -> RESOAdapter:
        """Create a test adapter instance."""
        return RESOAdapter(
            base_url="https://api.test.mls.com/odata",
            username="test_user",
            password="test_pass",
        )

    def test_adapter_creation(self, adapter: RESOAdapter) -> None:
        """Test adapter initialization."""
        assert adapter.base_url == "https://api.test.mls.com/odata"
        assert adapter.username == "test_user"
        assert adapter.password == "test_pass"  # noqa: S105 - test fixture credential

    def test_build_filter_simple(self) -> None:
        """Test simple filter building."""
        adapter = RESOAdapter(base_url="https://api.test.com/odata")

        filter_expr = adapter.build_filter(
            [
                {"field": "City", "operator": "eq", "value": "Austin"},
                {"field": "ListPrice", "operator": "ge", "value": 300000},
            ]
        )

        # The exact format may vary, but should contain both conditions
        assert "City eq 'Austin'" in filter_expr
        assert "ListPrice ge 300000" in filter_expr

    def test_build_filter_operators(self) -> None:
        """Test various filter operators."""
        adapter = RESOAdapter(base_url="https://api.test.com/odata")

        # Test gt
        assert "gt 100" in adapter.build_filter(
            [{"field": "Price", "operator": "gt", "value": 100}]
        )

        # Test lt
        assert "lt 100" in adapter.build_filter(
            [{"field": "Price", "operator": "lt", "value": 100}]
        )

        # Test contains
        assert "contains" in adapter.build_filter(
            [{"field": "City", "operator": "contains", "value": "Austin"}]
        )

    @patch("core.integrations.sources.reso_adapter.requests.Session.request")
    def test_fetch_property_success(self, mock_request, adapter: RESOAdapter) -> None:
        """Test successful property fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ListingId": "12345",
            "ListingKey": "LIST-123",
            "ListPrice": 450000,
            "City": "Austin",
        }
        mock_response.raise_for_status = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = adapter.fetch_property("LIST-123")

        assert result["ListingId"] == "12345"
        assert result["ListingKey"] == "LIST-123"
        assert result["ListPrice"] == 450000

    @patch("core.integrations.sources.reso_adapter.requests.Session.request")
    def test_fetch_property_404(self, mock_request, adapter: RESOAdapter) -> None:
        """Test 404 handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.text = "Not Found"
        mock_response.raise_for_status = Mock(side_effect=Exception("404 Not Found"))
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            adapter.fetch_property("NONEXISTENT")
        assert (
            "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()
        )

    @patch("core.integrations.sources.reso_adapter.requests.Session.request")
    def test_query_properties(self, mock_request, adapter: RESOAdapter) -> None:
        """Test property query with filters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"ListingId": "1", "ListPrice": 300000},
                {"ListingId": "2", "ListPrice": 400000},
            ],
            "@odata.count": 2,
        }
        mock_response.raise_for_status = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = adapter.query_properties(
            filter_expr="City eq 'Austin'",
            top=2,
        )

        assert len(result["value"]) == 2
        assert result["@odata.count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
