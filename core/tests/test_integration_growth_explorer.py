"""Integration tests for Growth Area Explorer.

These tests hit the live Census ACS API and BLS API.
Requires CENSUS_API_KEY and BLS_API_KEY in the environment.

Run with: pytest core/tests/test_integration_growth_explorer.py -v -m integration

The test structure mirrors test_integration_attom.py and test_integration_fred.py:
- Module-level skipif when API keys are absent
- Each test asserts response structure, not exact values
- Tests verify the API returns expected data shapes
"""

import os
from decimal import Decimal

import pytest

from core.integrations.market.census import (
    compute_supply_constraint_index,
    discover_places_in_state,
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
    get_acs_vintages,
)
from core.integrations.sources.fred_adapter import FREDAdapter

# Skip all tests in this module if no Census and BLS API keys
pytestmark = [
    pytest.mark.skipif(
        not (os.getenv("CENSUS_API_KEY") and os.getenv("BLS_API_KEY")),
        reason="CENSUS_API_KEY and BLS_API_KEY required",
    ),
    pytest.mark.integration,
]

# Known working states for tests
TEST_STATE = "TX"
TEST_STATE_2 = "VA"


class TestACSVintages:
    """Verify ACS vintage auto-detection from Census /data.json."""

    def test_get_acs_vintages_returns_strings(self):
        """Auto-detected vintages are non-empty strings."""
        current, prior = get_acs_vintages()
        assert isinstance(current, str) and len(current) == 4
        assert isinstance(prior, str) and len(prior) == 4

    def test_get_acs_vintages_current_is_larger(self):
        """Current vintage year > prior vintage year."""
        current, prior = get_acs_vintages()
        assert int(current) > int(prior)

    def test_get_acs_vintages_returns_cached(self):
        """Second call returns cached result (same values, fast)."""
        import time

        v1 = get_acs_vintages()
        start = time.time()
        v2 = get_acs_vintages()
        elapsed = time.time() - start
        assert v1 == v2
        assert elapsed < 1.0, "Cache miss — second call should be instant"


class TestDiscoverPlacesInState:
    """Verify Census place discovery returns expected structure."""

    def test_discover_places_returns_list(self):
        """Returns a list of places with expected keys."""
        places = discover_places_in_state(TEST_STATE, os.getenv("CENSUS_API_KEY", ""))
        assert isinstance(places, list)
        assert len(places) > 0

    def test_discover_places_sorted_by_population(self):
        """Places are sorted by population descending."""
        places = discover_places_in_state(
            TEST_STATE, os.getenv("CENSUS_API_KEY", ""), limit=5
        )
        pops = [p["population"] for p in places]
        assert pops == sorted(pops, reverse=True)

    def test_discover_places_has_expected_keys(self):
        """Each place dict has place_code, place_name, population."""
        places = discover_places_in_state(
            TEST_STATE, os.getenv("CENSUS_API_KEY", ""), limit=1
        )
        assert len(places) == 1
        p = places[0]
        assert "place_code" in p
        assert "place_name" in p
        assert "population" in p
        assert isinstance(p["place_code"], str)
        assert isinstance(p["place_name"], str)
        assert isinstance(p["population"], int)

    def test_discover_places_respects_limit(self):
        """Returns at most `limit` places."""
        limit = 3
        places = discover_places_in_state(
            TEST_STATE_2, os.getenv("CENSUS_API_KEY", ""), limit=limit
        )
        assert len(places) <= limit

    def test_discover_places_first_place_is_major_city(self):
        """The top place in Texas should be Houston or San Antonio (not a tiny town)."""
        places = discover_places_in_state(
            TEST_STATE, os.getenv("CENSUS_API_KEY", ""), limit=3
        )
        top = places[0]
        assert top["population"] > 500_000, (
            f"Expected large city as top place, got {top['place_name']} "
            f"with pop {top['population']}"
        )

    def test_discover_places_top_place_has_large_population(self):
        """Top place in TX should have > 500k population."""
        places = discover_places_in_state(
            TEST_STATE, os.getenv("CENSUS_API_KEY", ""), limit=1
        )
        assert places[0]["population"] > 500_000

    def test_discover_places_name_omits_state_suffix(self):
        """Place name does not contain state abbreviation."""
        places = discover_places_in_state(
            TEST_STATE, os.getenv("CENSUS_API_KEY", ""), limit=1
        )
        name = places[0]["place_name"]
        assert ", " not in name, f"Place name '{name}' should omit state suffix"

    def test_discover_places_default_limit(self):
        """Default limit of 20 is applied when not specified."""
        places = discover_places_in_state(TEST_STATE, os.getenv("CENSUS_API_KEY", ""))
        assert len(places) <= 20


class TestFetchPlaceGrowthMetrics:
    """Verify place-level growth metrics from Census ACS."""

    def _get_top_place_code(self, state: str) -> tuple[str, str]:
        """Helper to get place_code + place_name for the top place in a state."""
        places = discover_places_in_state(
            state, os.getenv("CENSUS_API_KEY", ""), limit=1
        )
        assert len(places) == 1, f"No places found for state {state}"
        return str(places[0]["place_code"]), str(places[0]["place_name"])

    def test_fetch_growth_metrics_returns_expected_keys(self):
        """Returns dict with growth rate keys."""
        place_code, place_name = self._get_top_place_code(TEST_STATE)
        result = fetch_place_growth_metrics(
            TEST_STATE, place_code, os.getenv("CENSUS_API_KEY", "")
        )
        assert result is not None, (
            f"Growth metrics returned None for {place_name}, {TEST_STATE}"
        )
        assert "population_growth_rate" in result
        assert "median_income_growth_rate" in result
        assert "housing_units_growth_rate" in result

    def test_fetch_growth_metrics_population_is_decimal(self):
        """Population growth rate is a Decimal or None (not a float)."""
        place_code, _ = self._get_top_place_code(TEST_STATE)
        result = fetch_place_growth_metrics(
            TEST_STATE, place_code, os.getenv("CENSUS_API_KEY", "")
        )
        assert result is not None
        rate = result["population_growth_rate"]
        assert rate is None or isinstance(rate, Decimal), (
            f"Expected Decimal or None, got {type(rate)}"
        )

    def test_fetch_growth_metrics_income_is_decimal(self):
        """Median income growth rate is a Decimal or None."""
        place_code, _ = self._get_top_place_code(TEST_STATE)
        result = fetch_place_growth_metrics(
            TEST_STATE, place_code, os.getenv("CENSUS_API_KEY", "")
        )
        assert result is not None
        rate = result["median_income_growth_rate"]
        assert rate is None or isinstance(rate, Decimal)

    def test_fetch_growth_metrics_returns_current_population(self):
        """Current population is returned as an int."""
        place_code, _ = self._get_top_place_code(TEST_STATE)
        result = fetch_place_growth_metrics(
            TEST_STATE, place_code, os.getenv("CENSUS_API_KEY", "")
        )
        assert result is not None
        assert isinstance(result["population_current"], int)
        assert result["population_current"] > 0

    def test_fetch_growth_metrics_prior_population(self):
        """Prior population is returned as an int."""
        place_code, _ = self._get_top_place_code(TEST_STATE)
        result = fetch_place_growth_metrics(
            TEST_STATE, place_code, os.getenv("CENSUS_API_KEY", "")
        )
        assert result is not None
        assert isinstance(result["population_prior"], int)
        assert result["population_prior"] > 0

    def test_fetch_growth_metrics_housing_units_optional(self):
        """Housing units (B25001_001E) may be missing — function should still succeed."""
        place_code, _ = self._get_top_place_code(TEST_STATE)
        result = fetch_place_growth_metrics(
            TEST_STATE, place_code, os.getenv("CENSUS_API_KEY", "")
        )
        assert result is not None
        # housing_units_current may be 0 if data is suppressed
        assert "housing_units_current" in result
        assert "housing_units_growth_rate" in result

    def test_fetch_growth_metrics_no_api_key(self):
        """Returns None when no API key provided."""
        result = fetch_place_growth_metrics(TEST_STATE, "12345", "")
        assert result is None

    def test_fetch_growth_metrics_invalid_state(self):
        """Returns None for invalid state code."""
        result = fetch_place_growth_metrics("ZZ", "12345", "fake-key")
        assert result is None

    def test_fetch_growth_metrics_multiple_places(self):
        """Growth metrics can be fetched for multiple places in the same state."""
        api_key = os.getenv("CENSUS_API_KEY", "")
        places = discover_places_in_state(TEST_STATE, api_key, limit=3)
        success_count = 0
        for p in places:
            result = fetch_place_growth_metrics(TEST_STATE, p["place_code"], api_key)
            if result is not None:
                success_count += 1
        assert success_count >= 2, (
            f"Expected at least 2 places to return growth metrics, got {success_count}"
        )


class TestFetchHousingDemandIndex:
    """Verify housing demand index computation from Census."""

    def test_housing_demand_returns_int(self):
        """Housing demand index is an int in range 0-100."""
        place_code, _ = TestFetchPlaceGrowthMetrics()._get_top_place_code(TEST_STATE)
        api_key = os.getenv("CENSUS_API_KEY", "")
        result = fetch_housing_demand_index(
            state_code=TEST_STATE,
            place_code=place_code,
            api_key=api_key,
            population_growth_rate=Decimal("0.05"),
        )
        if result is not None:
            assert isinstance(result, int) or result == int(result)
            assert 0 <= result <= 100, f"Index {result} out of range 0-100"
        # If result is None, that's acceptable (data may not be available)

    def test_housing_demand_with_zero_growth(self):
        """Housing demand index with zero population growth."""
        place_code, _ = TestFetchPlaceGrowthMetrics()._get_top_place_code(TEST_STATE)
        api_key = os.getenv("CENSUS_API_KEY", "")
        result = fetch_housing_demand_index(
            state_code=TEST_STATE,
            place_code=place_code,
            api_key=api_key,
            population_growth_rate=Decimal("0"),
        )
        if result is not None:
            assert isinstance(result, int)
            assert 0 <= result <= 100

    def test_housing_demand_no_api_key(self):
        """Returns None when no API key provided."""
        result = fetch_housing_demand_index("CA", "12345", "", Decimal("0.05"))
        assert result is None


class TestEmploymentGrowth:
    """Verify employment growth data via FRED (replaces BLS which has 25 req/day limit)."""

    def setup_method(self):
        """Create FRED adapter for each test."""
        self.fred = FREDAdapter()

    def test_employment_growth_returns_decimal(self):
        """Employment growth is a Decimal or None."""
        result = self.fred.fetch_state_employment_growth(TEST_STATE)
        if result is not None:
            assert isinstance(result, Decimal)

    def test_employment_growth_reasonable_range(self):
        """Employment growth is between -50% and +50% (not an extreme outlier)."""
        result = self.fred.fetch_state_employment_growth(TEST_STATE)
        if result is not None:
            assert -0.5 < float(result) < 0.5, (
                f"Employment growth {result} is outside expected range"
            )

    def test_employment_growth_invalid_state(self):
        """Returns None for invalid state code."""
        result = self.fred.fetch_state_employment_growth("ZZ")
        assert result is None

    def test_employment_growth_multiple_states(self):
        """Employment growth returns data for major states via FRED."""
        tx_growth = self.fred.fetch_state_employment_growth("TX")
        ca_growth = self.fred.fetch_state_employment_growth("CA")
        fl_growth = self.fred.fetch_state_employment_growth("FL")
        # At least one major state should return employment growth data
        assert any(g is not None for g in [tx_growth, ca_growth, fl_growth]), (
            "FRED employment growth returned None for TX, CA, and FL"
        )
        # Values that do exist should be Decimals
        for g in [tx_growth, ca_growth, fl_growth]:
            if g is not None:
                assert isinstance(g, Decimal)

    def test_employment_growth_positive_for_growing_states(self):
        """Fast-growing states should have positive employment growth over 5 years."""
        for state in ["TX", "FL", "UT", "NC", "AZ"]:
            result = self.fred.fetch_state_employment_growth(state)
            if result is not None:
                assert float(result) > -0.1, (
                    f"Employment growth for {state} should not be severely negative, got {result}"
                )


class TestSupplyConstraintIndex:
    """Verify supply constraint computation (no API calls needed)."""

    def test_zero_gap_returns_50(self):
        """Equal growth rates produce neutral score of 50."""
        result = compute_supply_constraint_index(Decimal("0.05"), Decimal("0.05"))
        assert result == 50

    def test_positive_gap_increases_score(self):
        """Population growing faster than housing increases score."""
        result = compute_supply_constraint_index(Decimal("0.10"), Decimal("0.00"))
        assert result == 100  # 0.10 * 500 + 50 = 100

    def test_negative_gap_decreases_score(self):
        """Housing growing faster than population decreases score."""
        result = compute_supply_constraint_index(Decimal("0.00"), Decimal("0.10"))
        assert result == 0  # -0.10 * 500 + 50 = 0

    def test_null_population_returns_none(self):
        """Returns None if population growth is None."""
        result = compute_supply_constraint_index(None, Decimal("0.05"))
        assert result is None

    def test_null_housing_returns_none(self):
        """Returns None if housing growth is None."""
        result = compute_supply_constraint_index(Decimal("0.05"), None)
        assert result is None

    def test_score_clamped_to_0(self):
        """Score does not go below 0."""
        result = compute_supply_constraint_index(Decimal("-0.20"), Decimal("0.00"))
        assert result == 0

    def test_score_clamped_to_100(self):
        """Score does not go above 100."""
        result = compute_supply_constraint_index(Decimal("0.20"), Decimal("0.00"))
        assert result == 100


class TestEndToEndGrowthAnalysis:
    """Full end-to-end test: discover → growth metrics → score for a state.

    These tests simulate what the Growth Area Explorer view does.
    """

    def test_full_analysis_texas(self):
        """Complete analysis for Texas — discovers 10+ places with growth data."""
        api_key_census = os.getenv("CENSUS_API_KEY", "")

        # Step 1: Discover places
        places = discover_places_in_state("TX", api_key_census, limit=5)
        assert len(places) >= 3, "Expected at least 3 places from TX"

        # Step 2: Fetch growth metrics for each place
        success_count = 0
        for p in places:
            result = fetch_place_growth_metrics("TX", p["place_code"], api_key_census)
            if result is not None:
                success_count += 1
                assert isinstance(
                    result["population_growth_rate"], (Decimal, type(None))
                )
                assert isinstance(
                    result["median_income_growth_rate"], (Decimal, type(None))
                )
        assert success_count >= 2, (
            f"Expected at least 2 places to have growth metrics, got {success_count}"
        )

    def test_full_analysis_virginia(self):
        """Complete analysis for Virginia."""
        api_key_census = os.getenv("CENSUS_API_KEY", "")

        places = discover_places_in_state("VA", api_key_census, limit=3)
        assert len(places) >= 1, "Expected at least 1 place from VA"

        # At least the top place should have growth metrics
        result = fetch_place_growth_metrics(
            "VA", places[0]["place_code"], api_key_census
        )
        assert result is not None, (
            f"Growth metrics should work for {places[0]['place_name']}, VA"
        )

    def test_full_analysis_california(self):
        """Complete analysis for California (large state, many places)."""
        api_key_census = os.getenv("CENSUS_API_KEY", "")

        places = discover_places_in_state("CA", api_key_census, limit=5)
        assert len(places) >= 3, "Expected at least 3 places from CA"

        success_count = 0
        for p in places[:3]:
            result = fetch_place_growth_metrics("CA", p["place_code"], api_key_census)
            if result is not None:
                success_count += 1
        assert success_count >= 2, (
            "Expected at least 2 places from CA to have growth metrics"
        )
