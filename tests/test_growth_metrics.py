"""Tests for TASK-B1 through TASK-B4 growth metrics adapters.

Covers:
  - Census place growth metrics (two-vintage population + income growth)
  - BLS employment growth
  - Housing demand index (Census occupancy proxy)
  - PopulateGrowthAreas management command

All HTTP calls are mocked — no real API calls in CI.
"""

from __future__ import annotations

import io
import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

import core.integrations.market.census as census_mod
from core.integrations.market.bls import fetch_employment_growth
from core.integrations.market.census import (
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
)
from core.models import GrowthArea


# ===========================================================================
#  TASK-B1 — fetch_place_growth_metrics (Census two-vintage)
# ===========================================================================


class CensusPlaceGrowthMetricsTest(TestCase):
    """Test Census two-vintage growth calculation for places (cities)."""

    def setUp(self):
        """Clear ACS vintage cache between tests to avoid stale cache in test isolation."""
        census_mod._acs_vintage_cache = None

    def _mock_census_response(
        self, population: int, income: int, housing_units: int = 100000
    ) -> MagicMock:
        """Helper to create a mock Census API response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["B01001_001E", "B19013_001E", "B25001_001E", "NAME"],
            [str(population), str(income), str(housing_units), "Place"],
        ]
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("core.integrations.market.census.requests.get")
    def test_returns_growth_rates_on_success(self, mock_get):
        """Returns growth rates from two-vintage comparison."""
        # Current vintage (2022): pop=400000, income=85000
        # Prior vintage (2017): pop=380000, income=78000
        # Pop growth: (400000-380000)/380000 = 0.0526
        # Income growth: (85000-78000)/78000 = 0.0897

        # First mock response for /data.json (auto-detect vintages)
        mock_data_json = MagicMock()
        mock_data_json.status_code = 200
        mock_data_json.json.return_value = {
            "dataset": [
                {
                    "c_vintage": 2022,
                    "title": "ACS 5-Year Detailed Tables",
                    "distribution": [
                        {"accessURL": "http://api.census.gov/data/2022/acs/acs5"}
                    ],
                },
                {
                    "c_vintage": 2017,
                    "title": "ACS 5-Year Detailed Tables",
                    "distribution": [
                        {"accessURL": "http://api.census.gov/data/2017/acs/acs5"}
                    ],
                },
            ]
        }
        mock_data_json.raise_for_status.return_value = None

        mock_get.side_effect = [
            mock_data_json,  # /data.json
            self._mock_census_response(400000, 85000),  # Current (2022)
            self._mock_census_response(380000, 78000),  # Prior (2017)
        ]

        result = fetch_place_growth_metrics(
            state_code="CA",
            place_code="67000",
            api_key="test-key",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["population_current"], 400000)
        self.assertEqual(result["population_prior"], 380000)
        self.assertAlmostEqual(float(result["population_growth_rate"]), 0.05, places=2)
        self.assertEqual(result["median_income_current"], Decimal("85000"))
        self.assertEqual(result["median_income_prior"], Decimal("78000"))
        self.assertAlmostEqual(
            float(result["median_income_growth_rate"]), 0.09, places=2
        )

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_missing_key(self, mock_get):
        """Returns None when no API key provided."""
        result = fetch_place_growth_metrics(
            state_code="CA", place_code="67000", api_key=""
        )
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_invalid_state(self, mock_get):
        """Returns None for invalid state code."""
        result = fetch_place_growth_metrics(
            state_code="ZZ", place_code="67000", api_key="test-key"
        )
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        """Returns None when Census API request fails."""
        import requests as req_lib

        mock_get.side_effect = req_lib.ConnectionError("Connection refused")

        result = fetch_place_growth_metrics(
            state_code="CA", place_code="67000", api_key="test-key"
        )
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_null_data(self, mock_get):
        """Returns None when Census returns null values."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["B01001_001E", "B19013_001E", "NAME"],
            ["-1", "null", "Place"],
        ]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = fetch_place_growth_metrics(
            state_code="CA", place_code="67000", api_key="test-key"
        )
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_negative_growth_rates(self, mock_get):
        """Returns negative growth rates when population/income decline."""
        # First mock response for /data.json (auto-detect vintages)
        mock_data_json = MagicMock()
        mock_data_json.status_code = 200
        mock_data_json.json.return_value = {
            "dataset": [
                {
                    "c_vintage": 2022,
                    "title": "ACS 5-Year Detailed Tables",
                    "distribution": [
                        {"accessURL": "http://api.census.gov/data/2022/acs/acs5"}
                    ],
                },
                {
                    "c_vintage": 2017,
                    "title": "ACS 5-Year Detailed Tables",
                    "distribution": [
                        {"accessURL": "http://api.census.gov/data/2017/acs/acs5"}
                    ],
                },
            ]
        }
        mock_data_json.raise_for_status.return_value = None

        mock_get.side_effect = [
            mock_data_json,  # /data.json
            self._mock_census_response(350000, 80000),  # Current
            self._mock_census_response(400000, 85000),  # Prior (higher)
        ]

        result = fetch_place_growth_metrics(
            state_code="CA", place_code="67000", api_key="test-key"
        )

        self.assertIsNotNone(result)
        self.assertLess(result["population_growth_rate"], 0)
        self.assertLess(result["median_income_growth_rate"], 0)


# ===========================================================================
#  TASK-B2 — fetch_employment_growth (BLS employment)
# ===========================================================================


class BlsEmploymentGrowthTest(TestCase):
    """Test BLS employment growth calculation."""

    def _mock_bls_response(self, data_entries: list[dict]) -> MagicMock:
        """Helper to create a mock BLS API response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "Results": {
                "series": [
                    {
                        "seriesId": "LAUST06001000000005",
                        "data": data_entries,
                    }
                ]
            }
        }
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_growth_on_success(self, mock_post):
        """Returns employment growth rate from earliest to latest data."""
        mock_post.return_value = self._mock_bls_response(
            [
                {"year": "2026", "period": "M01", "value": "1200000"},
                {"year": "2021", "period": "M01", "value": "1100000"},
            ]
        )
        result = fetch_employment_growth(
            state_code="CA", api_key="test-key", years_back=5
        )
        self.assertIsNotNone(result)
        # (1200000-1100000)/1100000 ≈ 0.0909
        self.assertAlmostEqual(float(result), 0.0909, places=4)

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_missing_key(self, mock_post):
        """Returns None when no API key provided."""
        result = fetch_employment_growth(state_code="CA", api_key="")
        self.assertIsNone(result)
        mock_post.assert_not_called()

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_invalid_state(self, mock_post):
        """Returns None for invalid state code."""
        result = fetch_employment_growth(state_code="ZZ", api_key="test-key")
        self.assertIsNone(result)
        mock_post.assert_not_called()

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_http_error(self, mock_post):
        """Returns None when BLS API request fails."""
        import requests as req_lib

        mock_post.side_effect = req_lib.ConnectionError("Connection refused")
        result = fetch_employment_growth(state_code="CA", api_key="test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.bls.requests.post")
    def test_returns_none_on_empty_data(self, mock_post):
        """Returns None when BLS returns no data."""
        mock_post.return_value = self._mock_bls_response([])
        result = fetch_employment_growth(state_code="CA", api_key="test-key")
        self.assertIsNone(result)

    @patch("core.integrations.market.bls.requests.post")
    def test_negative_employment_growth(self, mock_post):
        """Returns negative growth when employment declines."""
        mock_post.return_value = self._mock_bls_response(
            [
                {"year": "2026", "period": "M01", "value": "1000000"},
                {"year": "2021", "period": "M01", "value": "1200000"},
            ]
        )
        result = fetch_employment_growth(
            state_code="CA", api_key="test-key", years_back=5
        )
        self.assertIsNotNone(result)
        self.assertLess(result, 0)

    @patch("core.integrations.market.bls.requests.post")
    def test_uses_annual_average_preferentially(self, mock_post):
        """Prefers annual average (M13) over monthly data."""
        mock_post.return_value = self._mock_bls_response(
            [
                {"year": "2026", "period": "M13", "value": "1250000"},
                {"year": "2026", "period": "M01", "value": "1200000"},
                {"year": "2021", "period": "M13", "value": "1100000"},
                {"year": "2021", "period": "M01", "value": "1080000"},
            ]
        )
        result = fetch_employment_growth(
            state_code="CA", api_key="test-key", years_back=5
        )
        self.assertIsNotNone(result)
        # Uses M13: (1250000-1100000)/1100000 ≈ 0.1364
        self.assertAlmostEqual(float(result), 0.1364, places=4)


# ===========================================================================
#  TASK-B3 — fetch_housing_demand_index (Census occupancy proxy)
# ===========================================================================


class HousingDemandIndexTest(TestCase):
    """Test housing demand index calculation from ACS data."""

    def _mock_census_response(self, total_units: int, vacant_units: int) -> MagicMock:
        """Helper to create a mock Census API response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["B25002_001E", "B25002_003E", "NAME"],
            [str(total_units), str(vacant_units), "Place"],
        ]
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("core.integrations.market.census.requests.get")
    def test_returns_demand_index_on_success(self, mock_get):
        """Returns housing demand index from occupancy data."""
        # 100000 total units, 5000 vacant → 5% vacancy
        mock_get.return_value = self._mock_census_response(100000, 5000)
        result = fetch_housing_demand_index(
            state_code="CA", place_code="67000", api_key="test-key"
        )
        self.assertIsNotNone(result)
        # (1 - 0.05) * 100 = 95
        self.assertEqual(result, 95)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_missing_key(self, mock_get):
        """Returns None when no API key provided."""
        result = fetch_housing_demand_index(
            state_code="CA", place_code="67000", api_key=""
        )
        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_invalid_state(self, mock_get):
        """Returns None for invalid state code."""
        result = fetch_housing_demand_index(
            state_code="ZZ", place_code="67000", api_key="test-key"
        )
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        """Returns None when Census API request fails."""
        import requests as req_lib

        mock_get.side_effect = req_lib.ConnectionError("Connection refused")
        result = fetch_housing_demand_index(
            state_code="CA", place_code="67000", api_key="test-key"
        )
        self.assertIsNone(result)

    @patch("core.integrations.market.census.requests.get")
    def test_high_vacancy_low_demand(self, mock_get):
        """High vacancy rate results in low demand index."""
        # 100000 total, 40000 vacant → 40% vacancy → score = 60
        mock_get.return_value = self._mock_census_response(100000, 40000)
        result = fetch_housing_demand_index(
            state_code="CA", place_code="67000", api_key="test-key"
        )
        self.assertEqual(result, 60)

    @patch("core.integrations.market.census.requests.get")
    def test_population_growth_boost(self, mock_get):
        """Population growth rate boosts the demand index."""
        # 100000 total, 10000 vacant → 10% vacancy → base = 90
        # pop growth 0.05 (5%) → bonus = 5.0
        mock_get.return_value = self._mock_census_response(100000, 10000)
        result = fetch_housing_demand_index(
            state_code="CA",
            place_code="67000",
            api_key="test-key",
            population_growth_rate=Decimal("0.05"),
        )
        # 90 + 5 = 95
        self.assertEqual(result, 95)

    @patch("core.integrations.market.census.requests.get")
    def test_index_clamped_to_100(self, mock_get):
        """Demand index is clamped to maximum of 100."""
        # 100000 total, 0 vacant → 0% vacancy → base = 100
        mock_get.return_value = self._mock_census_response(100000, 0)
        result = fetch_housing_demand_index(
            state_code="CA",
            place_code="67000",
            api_key="test-key",
            population_growth_rate=Decimal("0.50"),
        )
        self.assertEqual(result, 100)

    @patch("core.integrations.market.census.requests.get")
    def test_returns_none_on_null_data(self, mock_get):
        """Returns None when Census returns null values."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["B25002_001E", "B25002_003E", "NAME"],
            ["-1", "null", "Place"],
        ]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = fetch_housing_demand_index(
            state_code="CA", place_code="67000", api_key="test-key"
        )
        self.assertIsNone(result)


# ===========================================================================
#  TASK-B4 — populate_growth_areas management command
# ===========================================================================


class PopulateGrowthAreasCommandTest(TestCase):
    """Test the populate_growth_areas management command."""

    @patch("core.management.commands.populate_growth_areas.fetch_place_growth_metrics")
    @patch("core.management.commands.populate_growth_areas.fetch_employment_growth")
    @patch("core.management.commands.populate_growth_areas.fetch_housing_demand_index")
    def test_creates_growth_area_on_success(
        self, mock_housing, mock_employment, mock_census
    ):
        """Creates a GrowthArea when all APIs return data."""
        mock_census.return_value = {
            "population_current": 400000,
            "population_prior": 380000,
            "population_growth_rate": Decimal("0.0526"),
            "median_income_current": Decimal("85000"),
            "median_income_prior": Decimal("78000"),
            "median_income_growth_rate": Decimal("0.0897"),
        }
        mock_employment.return_value = Decimal("0.0450")
        mock_housing.return_value = 90

        with patch.dict(
            os.environ,
            {
                "CENSUS_API_KEY": "test-census-key",
                "BLS_API_KEY": "test-bls-key",
            },
        ):
            out = io.StringIO()
            call_command(
                "populate_growth_areas",
                states=["CA"],
                cities=["San Francisco"],
                stdout=out,
            )

        self.assertIn("Created", out.getvalue())
        ga = GrowthArea.objects.get(state="CA", city_name="San Francisco")
        self.assertAlmostEqual(float(ga.population_growth_rate), 0.05, places=2)
        self.assertAlmostEqual(float(ga.employment_growth_rate), 0.04, places=2)
        self.assertAlmostEqual(float(ga.median_income_growth), 0.09, places=2)
        self.assertEqual(ga.housing_demand_index, 90)

    @patch("core.management.commands.populate_growth_areas.fetch_place_growth_metrics")
    @patch("core.management.commands.populate_growth_areas.fetch_employment_growth")
    @patch("core.management.commands.populate_growth_areas.fetch_housing_demand_index")
    def test_updates_existing_growth_area(
        self, mock_housing, mock_employment, mock_census
    ):
        """Updates an existing GrowthArea when run again."""
        GrowthArea.objects.create(
            state="CA",
            city_name="San Francisco",
            metro_area="San Francisco",
            population_growth_rate=Decimal("0.0100"),
            employment_growth_rate=Decimal("0.0200"),
            median_income_growth=Decimal("0.0300"),
            housing_demand_index=50,
            data_timestamp=timezone.now() - timedelta(days=60),
        )

        mock_census.return_value = {
            "population_current": 410000,
            "population_prior": 380000,
            "population_growth_rate": Decimal("0.0789"),
            "median_income_current": Decimal("90000"),
            "median_income_prior": Decimal("78000"),
            "median_income_growth_rate": Decimal("0.1538"),
        }
        mock_employment.return_value = Decimal("0.0550")
        mock_housing.return_value = 85

        with patch.dict(
            os.environ,
            {
                "CENSUS_API_KEY": "test-census-key",
                "BLS_API_KEY": "test-bls-key",
            },
        ):
            out = io.StringIO()
            call_command(
                "populate_growth_areas",
                states=["CA"],
                cities=["San Francisco"],
                stdout=out,
            )

        self.assertIn("Updated", out.getvalue())
        ga = GrowthArea.objects.get(state="CA", city_name="San Francisco")
        self.assertAlmostEqual(float(ga.population_growth_rate), 0.08, places=2)
        self.assertEqual(ga.housing_demand_index, 85)

    def test_fails_without_census_key(self):
        """Fails with CommandError when CENSUS_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError):
                call_command(
                    "populate_growth_areas",
                    states=["CA"],
                    cities=["San Francisco"],
                )

    def test_fails_without_bls_key(self):
        """Fails with CommandError when BLS_API_KEY is missing."""
        with patch.dict(
            os.environ,
            {"CENSUS_API_KEY": "test-key", "BLS_API_KEY": ""},
            clear=True,
        ):
            with self.assertRaises(CommandError):
                call_command(
                    "populate_growth_areas",
                    states=["CA"],
                    cities=["San Francisco"],
                )

    def test_fails_without_paired_args(self):
        """Fails with CommandError when only one of state/city is provided."""
        with self.assertRaises(CommandError):
            call_command("populate_growth_areas", states=["CA"])

    @patch("core.management.commands.populate_growth_areas.fetch_place_growth_metrics")
    @patch("core.management.commands.populate_growth_areas.fetch_employment_growth")
    @patch("core.management.commands.populate_growth_areas.fetch_housing_demand_index")
    def test_handles_multiple_cities(self, mock_housing, mock_employment, mock_census):
        """Creates GrowthArea records for multiple cities."""
        mock_census.return_value = {
            "population_current": 400000,
            "population_prior": 380000,
            "population_growth_rate": Decimal("0.05"),
            "median_income_current": Decimal("85000"),
            "median_income_prior": Decimal("78000"),
            "median_income_growth_rate": Decimal("0.09"),
        }
        mock_employment.return_value = Decimal("0.04")
        mock_housing.return_value = 85

        with patch.dict(
            os.environ,
            {
                "CENSUS_API_KEY": "test-census-key",
                "BLS_API_KEY": "test-bls-key",
            },
        ):
            out = io.StringIO()
            call_command(
                "populate_growth_areas",
                states=["CA", "TX"],
                cities=["San Francisco", "Austin"],
                stdout=out,
            )

        self.assertTrue(
            GrowthArea.objects.filter(state="CA", city_name="San Francisco").exists()
        )
        self.assertTrue(
            GrowthArea.objects.filter(state="TX", city_name="Austin").exists()
        )

    def test_list_cities_option(self):
        """--list-cities prints supported cities without API calls."""
        out = io.StringIO()
        call_command("populate_growth_areas", list_cities=True, stdout=out)
        self.assertIn("San Francisco", out.getvalue())
        self.assertIn("CA,", out.getvalue())

    @patch("core.management.commands.populate_growth_areas.fetch_place_growth_metrics")
    @patch("core.management.commands.populate_growth_areas.fetch_employment_growth")
    @patch("core.management.commands.populate_growth_areas.fetch_housing_demand_index")
    def test_handles_census_failure_gracefully(
        self, mock_housing, mock_employment, mock_census
    ):
        """Continues processing when Census API fails for one city."""
        mock_census.return_value = None  # Census failed

        with patch.dict(
            os.environ,
            {
                "CENSUS_API_KEY": "test-census-key",
                "BLS_API_KEY": "test-bls-key",
            },
        ):
            out = io.StringIO()
            call_command(
                "populate_growth_areas",
                states=["CA"],
                cities=["San Francisco"],
                stdout=out,
            )

        self.assertIn("Failed to fetch Census data", out.getvalue())
        self.assertFalse(
            GrowthArea.objects.filter(state="CA", city_name="San Francisco").exists()
        )
