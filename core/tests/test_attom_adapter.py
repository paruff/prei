"""Unit tests for ATTOM API adapter."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from core.integrations.sources.attom_adapter import (
    ATTOMAdapter,
    ATTOMAPIError,
    ATTOMAuthenticationError,
    ATTOMRateLimitError,
)


@pytest.fixture
def attom_adapter():
    """Create ATTOM adapter instance for testing."""
    return ATTOMAdapter(api_key="test_api_key")


@pytest.fixture
def sample_attom_response():
    """Sample ATTOM API response."""
    return {
        "property": {
            "address": {
                "line1": "123 Ocean Drive",
                "locality": "Miami",
                "countrySubd": "FL",
                "postal1": "33139",
                "county": "Miami-Dade",
                "latitude": "25.7617",
                "longitude": "-80.1918",
            },
            "building": {
                "rooms": {"beds": 3, "bathstotal": 2.5},
                "size": {"universalsize": 1850},
            },
            "summary": {"proptype": "Single Family Residential", "yearbuilt": 2005},
        },
        "preforeclosure": {
            "stage": "Notice of Trustee Sale",
            "date": "2024-01-15",
            "auctionDate": "2024-02-28",
            "amount": 480000,
            "lenderName": "Wells Fargo Bank",
            "caseNumber": "2024-FC-12345",
        },
    }


class TestATTOMAdapter:
    """Test suite for ATTOM API adapter."""

    def test_initialization_with_api_key(self):
        """Test adapter initialization with API key."""
        adapter = ATTOMAdapter(api_key="test_key")
        assert adapter.api_key == "test_key"
        assert adapter.session.headers["apikey"] == "test_key"

    def test_initialization_without_api_key(self):
        """Test adapter initialization without API key."""
        with patch.dict("os.environ", {"ATTOM_API_KEY": "env_key"}):
            adapter = ATTOMAdapter()
            assert adapter.api_key == "env_key"

    @patch("core.integrations.sources.attom_adapter.requests.Session.get")
    def test_fetch_property_detail_success(
        self, mock_get, attom_adapter, sample_attom_response
    ):
        """Test successful property detail fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_attom_response
        mock_response.headers = {}
        mock_get.return_value = mock_response

        result = attom_adapter.fetch_property_detail(
            "123 Ocean Drive", "Miami, FL 33139"
        )

        assert result == sample_attom_response
        mock_get.assert_called_once()

    @patch("core.integrations.sources.attom_adapter.requests.Session.get")
    def test_fetch_property_detail_authentication_failure(self, mock_get, attom_adapter):
        """Test authentication failure handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(ATTOMAuthenticationError) as exc_info:
            attom_adapter.fetch_property_detail("123 Main St")

        assert "Invalid or expired" in str(exc_info.value)

    @patch("core.integrations.sources.attom_adapter.requests.Session.get")
    def test_fetch_property_detail_rate_limit(self, mock_get, attom_adapter):
        """Test rate limit handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"X-RateLimit-Reset": "2024-12-08T12:00:00Z"}
        mock_get.return_value = mock_response

        with pytest.raises(ATTOMRateLimitError) as exc_info:
            attom_adapter.fetch_property_detail("123 Main St")

        assert "Rate limit exceeded" in str(exc_info.value)

    @patch("core.integrations.sources.attom_adapter.requests.Session.get")
    def test_fetch_property_detail_timeout(self, mock_get, attom_adapter):
        """Test timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(ATTOMAPIError) as exc_info:
            attom_adapter.fetch_property_detail("123 Main St")

        assert "timeout" in str(exc_info.value).lower()

    @patch("core.integrations.sources.attom_adapter.cache")
    @patch("core.integrations.sources.attom_adapter.requests.Session.get")
    def test_fetch_with_cache_returns_cached_data(
        self, mock_get, mock_cache, attom_adapter, sample_attom_response
    ):
        """Test that cached data is returned when available."""
        mock_cache.get.return_value = sample_attom_response

        result = attom_adapter.fetch_with_cache("123 Main St", "Miami, FL")

        assert result["_from_cache"] is True
        mock_get.assert_not_called()

    @patch("core.integrations.sources.attom_adapter.cache")
    @patch("core.integrations.sources.attom_adapter.requests.Session.get")
    def test_fetch_with_cache_makes_api_call_when_no_cache(
        self, mock_get, mock_cache, attom_adapter, sample_attom_response
    ):
        """Test that API call is made when cache is empty."""
        mock_cache.get.return_value = None

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_attom_response
        mock_response.headers = {}
        mock_get.return_value = mock_response

        result = attom_adapter.fetch_with_cache("123 Main St", "Miami, FL")

        assert result["_from_cache"] is False
        mock_get.assert_called_once()
        mock_cache.set.assert_called_once()

    def test_normalize_property(self, attom_adapter, sample_attom_response):
        """Test property data normalization."""
        normalized = attom_adapter.normalize_property(sample_attom_response)

        assert normalized["data_source"] == "ATTOM"
        assert normalized["street"] == "123 Ocean Drive"
        assert normalized["city"] == "Miami"
        assert normalized["state"] == "FL"
        assert normalized["zip_code"] == "33139"
        assert normalized["bedrooms"] == 3
        assert normalized["bathrooms"] == Decimal("2.5")
        assert normalized["square_footage"] == 1850
        assert normalized["year_built"] == 2005
        assert normalized["lender_name"] == "Wells Fargo Bank"
        assert normalized["foreclosure_status"] == "auction"

    def test_map_foreclosure_stage_preforeclosure(self, attom_adapter):
        """Test foreclosure stage mapping for pre-foreclosure."""
        data = {"stage": "Notice of Default"}
        assert attom_adapter._map_foreclosure_stage(data) == "preforeclosure"

    def test_map_foreclosure_stage_auction(self, attom_adapter):
        """Test foreclosure stage mapping for auction."""
        data = {"stage": "Notice of Trustee Sale"}
        assert attom_adapter._map_foreclosure_stage(data) == "auction"

    def test_map_foreclosure_stage_reo(self, attom_adapter):
        """Test foreclosure stage mapping for REO."""
        data = {"stage": "Bank Owned REO"}
        assert attom_adapter._map_foreclosure_stage(data) == "reo"

    def test_map_property_type_single_family(self, attom_adapter):
        """Test property type mapping for single family."""
        assert attom_adapter._map_property_type("Single Family Residential") == "single-family"

    def test_map_property_type_condo(self, attom_adapter):
        """Test property type mapping for condo."""
        assert attom_adapter._map_property_type("Condominium") == "condo"

    def test_map_property_type_multi_family(self, attom_adapter):
        """Test property type mapping for multi-family."""
        assert attom_adapter._map_property_type("Multi Family Dwelling") == "multi-family"

    def test_generate_property_id(self, attom_adapter, sample_attom_response):
        """Test property ID generation."""
        property_id = attom_adapter._generate_property_id(sample_attom_response)

        assert property_id.startswith("ATTOM-")
        assert len(property_id) == 18  # "ATTOM-" + 12 char hash

    @patch("core.integrations.sources.attom_adapter.cache")
    def test_track_api_call(self, mock_cache, attom_adapter):
        """Test API call tracking."""
        mock_cache.get.return_value = 0

        attom_adapter._track_api_call("/test/endpoint", 200)

        # Should update both call count and cost
        assert mock_cache.set.call_count == 2

    @patch("core.integrations.sources.attom_adapter.cache")
    def test_get_usage_stats(self, mock_cache, attom_adapter):
        """Test usage statistics retrieval."""
        mock_cache.get.side_effect = [5, Decimal("0.05")]  # calls, cost for today

        stats = attom_adapter.get_usage_stats(days=1)

        assert stats["total_calls"] == 5
        assert stats["total_cost"] == 0.05
        assert len(stats["days"]) == 1

    def test_safe_decimal_with_valid_number(self, attom_adapter):
        """Test safe decimal conversion with valid number."""
        assert attom_adapter._safe_decimal("123.45") == Decimal("123.45")
        assert attom_adapter._safe_decimal(123.45) == Decimal("123.45")

    def test_safe_decimal_with_none(self, attom_adapter):
        """Test safe decimal conversion with None."""
        assert attom_adapter._safe_decimal(None) is None

    def test_safe_decimal_with_empty_string(self, attom_adapter):
        """Test safe decimal conversion with empty string."""
        assert attom_adapter._safe_decimal("") is None

    def test_parse_date_with_iso_format(self, attom_adapter):
        """Test date parsing with ISO format."""
        assert attom_adapter._parse_date("2024-01-15") == "2024-01-15"

    def test_parse_date_with_us_format(self, attom_adapter):
        """Test date parsing with US format."""
        assert attom_adapter._parse_date("01/15/2024") == "2024-01-15"

    def test_parse_date_with_none(self, attom_adapter):
        """Test date parsing with None."""
        assert attom_adapter._parse_date(None) is None

    def test_normalize_property_with_partial_data(self, attom_adapter):
        """Test normalization with missing fields."""
        partial_data = {
            "property": {
                "address": {
                    "line1": "123 Main St",
                    "locality": "Miami",
                    "countrySubd": "FL",
                },
                "building": {"rooms": {}, "size": {}},
                "summary": {},
            },
            "preforeclosure": {},
        }

        normalized = attom_adapter.normalize_property(partial_data)

        assert normalized["street"] == "123 Main St"
        assert normalized["bedrooms"] == 0
        assert normalized["bathrooms"] == Decimal("0")
        assert normalized["square_footage"] == 0
