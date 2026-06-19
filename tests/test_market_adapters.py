"""Tests for Census and BLS market data adapters.

All HTTP calls are mocked — no real API calls in CI.
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.integrations.market.census import fetch_zip_demographics
from core.integrations.market.bls import fetch_unemployment_rate


class CensusFetchZipDemographicsTest(TestCase):
    """Test Census API adapter."""

    def _mock_response(self, json_data, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("core.integrations.market.census.requests.get")
    def test_returns_correct_structure(self, mock_get):
        """fetch_zip_demographics returns dict with required keys and Decimal values."""
        census_response = [
            ["B01001_001E", "B19013_001E", "NAME"],
            ["35000", "75000", "ZCTA5 90210"],
        ]
        mock_get.return_value = self._mock_response(census_response)

        result = fetch_zip_demographics("90210", "test-key")

        self.assertIsNotNone(result)
        self.assertIn("population", result)
        self.assertIn("population_growth_pct_5yr", result)
        self.assertIn("median_household_income", result)
        self.assertEqual(result["population"], 35000)
        self.assertIsInstance(result["median_household_income"], Decimal)
        self.assertEqual(result["median_household_income"], Decimal("75000"))

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        """Gracefully returns None when HTTP request fails."""
        import requests as req_lib

        mock_get.side_effect = req_lib.ConnectionError("Connection refused")

        result = fetch_zip_demographics("90210", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_invalid_json(self, mock_get):
        """Gracefully returns None when response is not valid JSON."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_resp

        result = fetch_zip_demographics("90210", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_empty_response(self, mock_get):
        """Gracefully returns None when response structure is unexpected."""
        mock_get.return_value = self._mock_response([])

        result = fetch_zip_demographics("90210", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_null_population(self, mock_get):
        """Gracefully returns None when population is suppressed."""
        census_response = [
            ["B01001_001E", "B19013_001E"],
            ["null", "75000"],
        ]
        mock_get.return_value = self._mock_response(census_response)

        result = fetch_zip_demographics("90210", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_missing_api_key(self, mock_get):
        """Returns None immediately when API key is empty."""
        result = fetch_zip_demographics("90210", "")
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch("core.integrations.market.census.requests.get")
    def test_passes_correct_params(self, mock_get):
        """Verifies correct Census API parameters are sent."""
        census_response = [
            ["B01001_001E", "B19013_001E"],
            ["10000", "50000"],
        ]
        mock_get.return_value = self._mock_response(census_response)

        fetch_zip_demographics("23220", "my-key")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        self.assertIn("api.census.gov", call_kwargs[0][0])
        self.assertEqual(call_kwargs[1]["params"]["key"], "my-key")
        self.assertIn("23220", call_kwargs[1]["params"]["for"])


class BlsFetchUnemploymentRateTest(TestCase):
    """Test BLS API adapter."""

    def _mock_response(self, json_data, status_code=200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_decimal_fraction(self, mock_post):
        """fetch_unemployment_rate returns Decimal (not float)."""
        bls_response = {
            "Results": {
                "series": [
                    {
                        "seriesId": "LAUST510010000000003",
                        "data": [
                            {"year": "2024", "period": "M01", "value": "3.2"},
                            {"year": "2023", "period": "M12", "value": "3.1"},
                        ],
                    }
                ]
            }
        }
        mock_post.return_value = self._mock_response(bls_response)

        result = fetch_unemployment_rate("VA", "test-key")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("0.032"))

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_http_error(self, mock_post):
        """Gracefully returns None when HTTP request fails."""
        import requests as req_lib

        mock_post.side_effect = req_lib.ConnectionError("Connection refused")

        result = fetch_unemployment_rate("VA", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_invalid_json(self, mock_post):
        """Gracefully returns None when response is not valid JSON."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_resp

        result = fetch_unemployment_rate("VA", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_empty_series(self, mock_post):
        """Gracefully returns None when BLS returns no series data."""
        bls_response = {"Results": {"series": []}}
        mock_post.return_value = self._mock_response(bls_response)

        result = fetch_unemployment_rate("VA", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_null_value(self, mock_post):
        """Gracefully returns None when BLS value is suppressed."""
        bls_response = {
            "Results": {
                "series": [
                    {"seriesId": "LAUST510010000000003", "data": [{"value": "-1"}]}
                ]
            }
        }
        mock_post.return_value = self._mock_response(bls_response)

        result = fetch_unemployment_rate("VA", "test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_invalid_state(self, mock_post):
        """Returns None for invalid state code."""
        result = fetch_unemployment_rate("XX", "test-key")
        self.assertIsNone(result)
        mock_post.assert_not_called()

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_missing_api_key(self, mock_post):
        """Returns None immediately when API key is empty."""
        result = fetch_unemployment_rate("VA", "")
        self.assertIsNone(result)
        mock_post.assert_not_called()

    @patch("core.integrations.market.bls.requests.post")
    def test_handles_float_value(self, mock_post):
        """Handles BLS returning a float-style string like '4.5'."""
        bls_response = {
            "Results": {
                "series": [
                    {"seriesId": "LAUST510010000000003", "data": [{"value": "4.5"}]}
                ]
            }
        }
        mock_post.return_value = self._mock_response(bls_response)

        result = fetch_unemployment_rate("VA", "test-key")
        self.assertEqual(result, Decimal("0.045"))


class MarketSnapshotCacheTest(TestCase):
    """Test 30-day cache behavior for MarketSnapshot."""

    def test_snapshot_has_fetched_at_field(self):
        """MarketSnapshot model has fetched_at field."""
        from core.models import MarketSnapshot

        field = MarketSnapshot._meta.get_field("fetched_at")
        self.assertTrue(field.null)  # Can be null initially

    def test_snapshot_has_new_fields(self):
        """MarketSnapshot model has all new Census/BLS fields."""
        from core.models import MarketSnapshot

        for field_name in [
            "msa_name",
            "population",
            "population_growth_pct_5yr",
            "unemployment_rate",
            "median_household_income",
            "fetched_at",
        ]:
            MarketSnapshot._meta.get_field(field_name)


class RefreshMarketDataCommandTest(TestCase):
    """Test the refresh_market_data management command."""

    @patch("core.management.commands.refresh_market_data.fetch_unemployment_rate")
    @patch("core.management.commands.refresh_market_data.fetch_zip_demographics")
    def test_creates_snapshot(self, mock_census, mock_bls):
        """Command creates MarketSnapshot for given ZIP."""
        from django.core.management import call_command

        mock_census.return_value = {
            "population": 35000,
            "population_growth_pct_5yr": None,
            "median_household_income": Decimal("75000"),
        }
        mock_bls.return_value = Decimal("0.045")

        env = {
            "CENSUS_API_KEY": "test-census-key",
            "BLS_API_KEY": "test-bls-key",
        }
        with patch.dict(os.environ, env):
            call_command(
                "refresh_market_data",
                zip_codes=["90210"],
                state="VA",
            )

        from core.models import MarketSnapshot

        snapshot = MarketSnapshot.objects.get(zip_code="90210")
        self.assertEqual(snapshot.population, 35000)
        self.assertEqual(snapshot.median_household_income, Decimal("75000"))
        self.assertEqual(snapshot.unemployment_rate, Decimal("0.045"))
        self.assertIsNotNone(snapshot.fetched_at)

    @patch("core.management.commands.refresh_market_data.fetch_unemployment_rate")
    @patch("core.management.commands.refresh_market_data.fetch_zip_demographics")
    def test_skips_fresh_cache(self, mock_census, mock_bls):
        """Command skips re-fetch when cache is fresh (< 30 days)."""
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        from core.models import MarketSnapshot

        # Create fresh snapshot
        MarketSnapshot.objects.create(
            zip_code="90210",
            population=30000,
            fetched_at=timezone.now() - timedelta(days=5),
        )

        env = {
            "CENSUS_API_KEY": "test-key",
            "BLS_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env):
            call_command(
                "refresh_market_data",
                zip_codes=["90210"],
                force=False,
            )

        # Should not have called APIs (cache is fresh)
        mock_census.assert_not_called()
        mock_bls.assert_not_called()

        # Snapshot should still have old population
        snapshot = MarketSnapshot.objects.get(zip_code="90210")
        self.assertEqual(snapshot.population, 30000)

    @patch("core.management.commands.refresh_market_data.fetch_unemployment_rate")
    @patch("core.management.commands.refresh_market_data.fetch_zip_demographics")
    def test_force_refreshes_stale_cache(self, mock_census, mock_bls):
        """Command re-fetches when --force is used."""
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        from core.models import MarketSnapshot

        # Create stale snapshot
        MarketSnapshot.objects.create(
            zip_code="90210",
            population=30000,
            fetched_at=timezone.now() - timedelta(days=60),
        )

        mock_census.return_value = {
            "population": 40000,
            "population_growth_pct_5yr": None,
            "median_household_income": Decimal("80000"),
        }
        mock_bls.return_value = Decimal("0.05")

        env = {
            "CENSUS_API_KEY": "test-key",
            "BLS_API_KEY": "test-key",
        }
        with patch.dict(os.environ, env):
            call_command(
                "refresh_market_data",
                zip_codes=["90210"],
                state="VA",
                force=True,
            )

        mock_census.assert_called_once()
        snapshot = MarketSnapshot.objects.get(zip_code="90210")
        self.assertEqual(snapshot.population, 40000)
