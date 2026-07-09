"""Tests for census.py data pipeline functions.

Covers: discover_places_in_state, fetch_place_growth_metrics,
compute_supply_constraint_index, fetch_housing_demand_index.
All API calls are mocked — tests verify parsing, edge cases,
and error handling.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock, patch


from core.integrations.market.census import (
    compute_supply_constraint_index,
    discover_places_in_state,
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
)


# ═══════════════════════════════════════════════════════════════════════
# discover_places_in_state
# ═══════════════════════════════════════════════════════════════════════


class TestDiscoverPlacesInState:
    """Tests for discover_places_in_state()."""

    def test_returns_empty_without_api_key(self) -> None:
        """No API key → empty list."""
        result = discover_places_in_state("TX", "")
        assert result == []

    def test_returns_empty_for_bad_state(self) -> None:
        """Invalid state code → empty list."""
        result = discover_places_in_state("XX", "test-key")
        assert result == []

    @patch("core.integrations.market.census.requests.get")
    def test_parses_valid_response(self, mock_get: Mock) -> None:
        """Valid Census response → parsed place list."""
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            ["B01001_001E", "NAME", "place"],
            ["4000000", "Los Angeles, Texas", "44000"],
            ["1200000", "Dallas, Texas", "55000"],
        ]

        places = discover_places_in_state("TX", "test-key", limit=2)
        assert len(places) == 2
        assert places[0]["place_name"] == "Los Angeles"
        assert places[0]["population"] == 4000000
        assert places[1]["place_name"] == "Dallas"

    @patch("core.integrations.market.census.requests.get")
    def test_handles_api_error(self, mock_get: Mock) -> None:
        """HTTP error → empty list."""
        import requests

        mock_get.side_effect = requests.RequestException("API timeout")
        result = discover_places_in_state("TX", "test-key")
        assert result == []

    @patch("core.integrations.market.census.requests.get")
    def test_handles_invalid_json(self, mock_get: Mock) -> None:
        """Invalid JSON → empty list."""
        mock_get.return_value.ok = True
        mock_get.return_value.json.side_effect = ValueError("bad json")
        result = discover_places_in_state("TX", "test-key")
        assert result == []

    @patch("core.integrations.market.census.requests.get")
    def test_sorts_by_population_desc(self, mock_get: Mock) -> None:
        """Results are sorted by population descending."""
        mock_get.return_value.ok = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            ["B01001_001E", "NAME", "place"],
            ["500", "Small town, Texas", "001"],
            ["50000", "Medium city, Texas", "002"],
            ["500000", "Big city, Texas", "003"],
        ]

        places = discover_places_in_state("TX", "test-key", limit=3)
        assert places[0]["place_name"] == "Big city"
        assert places[1]["place_name"] == "Medium city"
        assert places[2]["population"] == 500


# ═══════════════════════════════════════════════════════════════════════
# fetch_place_growth_metrics
# ═══════════════════════════════════════════════════════════════════════


class TestFetchPlaceGrowthMetrics:
    """Tests for fetch_place_growth_metrics()."""

    def test_returns_none_without_api_key(self) -> None:
        """No API key → None."""
        result = fetch_place_growth_metrics("TX", "44000", "")
        assert result is None

    def test_returns_none_for_bad_state(self) -> None:
        """Invalid state → None."""
        result = fetch_place_growth_metrics("XX", "44000", "test-key")
        assert result is None

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_computes_growth_rates(self, mock_fetch: Mock) -> None:
        """Computes population and income growth from two vintages."""
        mock_fetch.side_effect = [
            {
                "headers": ["B01001_001E", "B19013_001E", "B25001_001E"],
                "values": ["110000", "65000", "50000"],
            },
            {
                "headers": ["B01001_001E", "B19013_001E", "B25001_001E"],
                "values": ["100000", "60000", "48000"],
            },
        ]

        result = fetch_place_growth_metrics("TX", "44000", "test-key")
        assert result is not None
        assert result["population_current"] == 110000
        assert result["population_prior"] == 100000
        # growth = (110000 - 100000) / 100000 = 0.10
        assert result["population_growth_rate"] == Decimal("0.10")
        # income growth = (65000 - 60000) / 60000 = 0.0833... → quantized to 0.08
        assert result["median_income_growth_rate"] is not None
        assert result["median_income_growth_rate"] == Decimal("0.08")
        # housing units growth = (50000 - 48000) / 48000 = 0.0417 → quantized to 0.04
        assert result["housing_units_growth_rate"] is not None
        assert result["housing_units_growth_rate"] == Decimal("0.04")

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_returns_none_if_current_missing(self, mock_fetch: Mock) -> None:
        """No current data → None."""
        mock_fetch.side_effect = [None, {"B01001_001E": "100000"}]
        result = fetch_place_growth_metrics("TX", "44000", "test-key")
        assert result is None

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_returns_none_if_prior_missing(self, mock_fetch: Mock) -> None:
        """No prior data → None."""
        mock_fetch.side_effect = [
            {"B01001_001E": "110000", "B19013_001E": "65000"},
            None,
        ]
        result = fetch_place_growth_metrics("TX", "44000", "test-key")
        assert result is None

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_handles_zero_prior_values(self, mock_fetch: Mock) -> None:
        """Zero prior values → None growth rates (not crash)."""
        mock_fetch.side_effect = [
            {
                "headers": ["B01001_001E", "B19013_001E", "B25001_001E"],
                "values": ["100", "50000", "100"],
            },
            {
                "headers": ["B01001_001E", "B19013_001E", "B25001_001E"],
                "values": ["0", "0", "0"],
            },
        ]
        result = fetch_place_growth_metrics("TX", "44000", "test-key")
        assert result is not None
        assert result["population_growth_rate"] is None
        assert result["median_income_growth_rate"] is None


# ═══════════════════════════════════════════════════════════════════════
# compute_supply_constraint_index
# ═══════════════════════════════════════════════════════════════════════


class TestComputeSupplyConstraintIndex:
    """Tests for compute_supply_constraint_index()."""

    def test_returns_none_if_no_pop_growth(self) -> None:
        """Missing pop growth → None."""
        assert compute_supply_constraint_index(None, Decimal("0.05")) is None

    def test_returns_none_if_no_units_growth(self) -> None:
        """Missing units growth → None."""
        assert compute_supply_constraint_index(Decimal("0.05"), None) is None

    def test_neutral_when_equal(self) -> None:
        """Equal growth rates → neutral 50."""
        result = compute_supply_constraint_index(Decimal("0.03"), Decimal("0.03"))
        assert result == 50

    def test_high_when_pop_outpacing_units(self) -> None:
        """Pop growth > units growth → high index."""
        result = compute_supply_constraint_index(Decimal("0.10"), Decimal("0.02"))
        # diff = 0.08, raw = 0.08 * 500 + 50 = 90
        assert result == 90

    def test_low_when_units_outpacing_pop(self) -> None:
        """Units growth > pop growth → low index."""
        result = compute_supply_constraint_index(Decimal("0.01"), Decimal("0.08"))
        # diff = -0.07, raw = -0.07 * 500 + 50 = 15
        assert result == 15

    def test_clamps_at_100(self) -> None:
        """Index clamps at 100 maximum."""
        result = compute_supply_constraint_index(Decimal("0.50"), Decimal("0.00"))
        # diff = 0.50, raw = 0.50 * 500 + 50 = 300 → clamp to 100
        assert result == 100

    def test_clamps_at_0(self) -> None:
        """Index clamps at 0 minimum."""
        result = compute_supply_constraint_index(Decimal("-0.50"), Decimal("0.00"))
        # diff = -0.50, raw = -0.50 * 500 + 50 = -200 → clamp to 0
        assert result == 0


# ═══════════════════════════════════════════════════════════════════════
# fetch_housing_demand_index
# ═══════════════════════════════════════════════════════════════════════


class TestFetchHousingDemandIndex:
    """Tests for fetch_housing_demand_index()."""

    def test_returns_none_without_api_key(self) -> None:
        """No API key → None."""
        result = fetch_housing_demand_index("TX", "44000", "")
        assert result is None

    def test_returns_none_for_bad_state(self) -> None:
        """Invalid state → None."""
        result = fetch_housing_demand_index("XX", "44000", "test-key")
        assert result is None

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_high_occupancy_low_demand(self, mock_fetch: Mock) -> None:
        """Low vacancy + low pop growth → moderate demand."""
        mock_fetch.return_value = {
            "headers": ["B25002_001E", "B25002_003E"],
            "values": ["1000", "50"],
        }
        result = fetch_housing_demand_index("TX", "44000", "test-key")
        assert result is not None
        # occupancy_score = (1 - 50/1000) * 100 = 95
        assert result == 95

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_low_occupancy_high_demand_with_growth(self, mock_fetch: Mock) -> None:
        """High vacancy + strong pop growth → occupancy score with bonus."""
        mock_fetch.return_value = {
            "headers": ["B25002_001E", "B25002_003E"],
            "values": ["1000", "400"],
        }
        result = fetch_housing_demand_index(
            "TX", "44000", "test-key", population_growth_rate=Decimal("0.08")
        )
        assert result is not None
        # occupancy_score = (1 - 400/1000) * 100 = 60
        # growth_bonus = min(8, 20) = 8
        # total = 68
        assert result == 68

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_returns_none_on_parse_error(self, mock_fetch: Mock) -> None:
        """Bad data → None."""
        mock_fetch.return_value = {
            "headers": ["B25002_001E", "B25002_003E"],
            "values": ["abc", "def"],
        }
        result = fetch_housing_demand_index("TX", "44000", "test-key")
        assert result is None

    @patch("core.integrations.market.census._fetch_acs_data")
    def test_returns_none_on_zero_units(self, mock_fetch: Mock) -> None:
        """Zero total units → None."""
        mock_fetch.return_value = {
            "headers": ["B25002_001E", "B25002_003E"],
            "values": ["0", "0"],
        }
        result = fetch_housing_demand_index("TX", "44000", "test-key")
        assert result is None
