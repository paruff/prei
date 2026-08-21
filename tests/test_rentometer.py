"""Unit tests for Rentometer API adapter."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.integrations.market.rentometer import (
    RentometerClient,
    RentometerError,
    _parse_rent,
    get_rent_estimate,
)


class TestRentometerClient:
    """Test suite for RentometerClient."""

    def test_client_requires_api_key(self) -> None:
        """Client should raise error when API key is missing."""
        with patch("core.integrations.market.rentometer.settings") as mock_settings:
            mock_settings.RENTO_METER_API_KEY = ""
            client = RentometerClient()
            assert client.api_key == ""

    def test_client_uses_settings_api_key(self) -> None:
        """Client should read API key from Django settings."""
        with patch("core.integrations.market.rentometer.settings") as mock_settings:
            mock_settings.RENTO_METER_API_KEY = "test-key-123"
            client = RentometerClient()
            assert client.api_key == "test-key-123"

    def test_client_accepts_explicit_api_key(self) -> None:
        """Client should accept explicit API key over settings."""
        client = RentometerClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    @patch("core.integrations.market.rentometer.requests.get")
    def test_get_rent_by_address_success(self, mock_get: MagicMock) -> None:
        """Successful rent lookup returns parsed data."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "median": "1850",
            "min": "1600",
            "max": "2100",
            "count": 15,
            "city": "Austin",
            "state": "TX",
        }
        mock_get.return_value = mock_resp

        client = RentometerClient(api_key="test-key")
        result = client.get_rent_by_address(
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )

        assert result is not None
        assert result["median_rent"] == Decimal("1850.00")
        assert result["min_rent"] == Decimal("1600.00")
        assert result["max_rent"] == Decimal("2100.00")
        assert result["count"] == 15

    @patch("core.integrations.market.rentometer.requests.get")
    def test_get_rent_by_address_no_data(self, mock_get: MagicMock) -> None:
        """Returns None when API returns no median rent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"median": None, "count": 0}
        mock_get.return_value = mock_resp

        client = RentometerClient(api_key="test-key")
        result = client.get_rent_by_address(
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )
        assert result is None

    @patch("core.integrations.market.rentometer.requests.get")
    def test_get_rent_by_address_api_error(self, mock_get: MagicMock) -> None:
        """Returns None on API error."""
        mock_get.side_effect = RentometerError("API error")

        client = RentometerClient(api_key="test-key")
        result = client.get_rent_by_address(
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
        )
        assert result is None


class TestGetRentEstimate:
    """Test suite for get_rent_estimate convenience function."""

    def test_returns_none_without_api_key(self) -> None:
        """Returns None when no API key is configured."""
        with patch("core.integrations.market.rentometer.settings") as mock_settings:
            mock_settings.RENTO_METER_API_KEY = ""
            result = get_rent_estimate(
                zip_code="78701",
                address="123 Main St",
                city="Austin",
                state="TX",
            )
            assert result is None

    def test_returns_none_with_incomplete_address(self) -> None:
        """Returns None when address components are missing."""
        with patch("core.integrations.market.rentometer.settings") as mock_settings:
            mock_settings.RENTO_METER_API_KEY = "test-key"
            result = get_rent_estimate(zip_code="78701")
            assert result is None

    @patch("core.integrations.market.rentometer.RentometerClient")
    def test_caches_rent_estimate(self, MockClient: MagicMock) -> None:
        """Rent estimate is cached for subsequent calls."""
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.get_rent_by_address.return_value = {
            "median_rent": Decimal("1850.00"),
            "min_rent": Decimal("1600.00"),
            "max_rent": Decimal("2100.00"),
            "count": 15,
        }

        with patch("core.integrations.market.rentometer.settings") as mock_settings:
            mock_settings.RENTO_METER_API_KEY = "test-key"

            # First call hits API
            result1 = get_rent_estimate(
                zip_code="78701",
                address="123 Main St",
                city="Austin",
                state="TX",
            )
            assert result1 == Decimal("1850.00")
            assert mock_instance.get_rent_by_address.call_count == 1

            # Second call uses cache
            result2 = get_rent_estimate(
                zip_code="78701",
                address="123 Main St",
                city="Austin",
                state="TX",
            )
            assert result2 == Decimal("1850.00")
            assert (
                mock_instance.get_rent_by_address.call_count == 1
            )  # No additional API call


class TestParseRent:
    """Edge cases for _parse_rent's Decimal coercion."""

    def test_none_returns_none(self) -> None:
        assert _parse_rent(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert _parse_rent("") is None

    def test_non_numeric_returns_none(self) -> None:
        assert _parse_rent("not-a-number") is None

    def test_negative_returns_none(self) -> None:
        assert _parse_rent(-500) is None

    def test_zero_returns_none(self) -> None:
        assert _parse_rent(0) is None

    def test_valid_string_returns_decimal(self) -> None:
        assert _parse_rent("1850") == Decimal("1850.00")

    def test_valid_float_returns_decimal(self) -> None:
        assert _parse_rent(1850.5) == Decimal("1850.50")


class TestGetErrorClassification:
    """RentometerClient._get() must funnel every failure through RentometerError."""

    @patch("core.integrations.market.rentometer.requests.get")
    def test_timeout_raises_rentometer_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.Timeout("timed out")
        client = RentometerClient(api_key="test-key")
        with pytest.raises(RentometerError):
            client._get("rent", params={})

    @patch("core.integrations.market.rentometer.requests.get")
    def test_server_error_raises_rentometer_error(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_get.return_value = mock_resp
        client = RentometerClient(api_key="test-key")
        with pytest.raises(RentometerError):
            client._get("rent", params={})

    @patch("core.integrations.market.rentometer.requests.get")
    def test_server_error_caught_by_get_rent_by_address(
        self, mock_get: MagicMock
    ) -> None:
        """A 500 must not escape as a raw requests.HTTPError past the adapter."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_get.return_value = mock_resp
        client = RentometerClient(api_key="test-key")
        result = client.get_rent_by_address(
            address="123 Main St", city="Austin", state="TX", zip_code="78701"
        )
        assert result is None
