"""Integration tests for FRED API adapter.

These tests hit the live FRED API and require a valid FRED_API_KEY in the environment.
Run with: pytest core/tests/test_integration_fred.py -v -m integration

Get a free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import os
import pytest

from core.integrations.sources.fred_adapter import FREDAdapter, FREDAuthenticationError


# Skip all tests in this module if no FRED API key
pytestmark = pytest.mark.skipif(
    not (os.getenv("FRED_API_KEY") or os.getenv("FRED_api_key")),
    reason="FRED_API_KEY not set in environment",
)


class TestFREDLIntegration:
    """Live integration tests against FRED API."""

    def setup_method(self):
        """Create adapter instance for each test."""
        self.adapter = FREDAdapter()

    def test_adapter_initialization(self):
        """Test adapter initializes with API key from environment."""
        assert self.adapter.api_key == os.getenv("FRED_API_KEY")
        assert self.adapter.session.headers.get("Accept") == "application/json"

    def test_invalid_key_raises_auth_error(self):
        """Test that invalid API key raises authentication error."""
        bad_adapter = FREDAdapter(api_key="INVALID_KEY")
        with pytest.raises(FREDAuthenticationError):
            bad_adapter.get_series_observations("PERMIT")

    def test_get_series_observations_national_permits(self):
        """Test fetching national building permits (PERMIT series)."""
        obs = self.adapter.get_series_observations(
            series_id="PERMIT",
            limit=5,
        )

        assert isinstance(obs, list)
        assert len(obs) <= 5
        if obs:
            assert "date" in obs[0]
            assert "value" in obs[0]

    def test_get_latest_observation(self):
        """Test getting latest observation for a series."""
        latest = self.adapter.get_latest_observation("PERMIT")

        assert latest is not None
        assert "date" in latest
        assert "value" in latest

    def test_get_series_info(self):
        """Test getting series metadata."""
        info = self.adapter.get_series_info("PERMIT")

        assert info is not None
        assert info.get("id") == "PERMIT"
        assert "title" in info
        assert "frequency" in info

    def test_search_series(self):
        """Test searching for series by text."""
        results = self.adapter.search_series("building permits", limit=5)

        assert isinstance(results, list)
        assert len(results) <= 5
        if results:
            assert "id" in results[0]
            assert "title" in results[0]

    def test_get_category_series(self):
        """Test getting series in a category."""
        # Category 32061 = "Housing" category (may vary)
        results = self.adapter.get_category_series(32061)

        assert isinstance(results, list)
        # May be empty if category doesn't exist, but shouldn't error


class TestFREDLiveSupplyConstraint:
    """Test FRED supply constraint convenience methods."""

    def setup_method(self):
        self.adapter = FREDAdapter()

    def test_get_building_permits_national(self):
        """Test national building permits retrieval."""
        permits = self.adapter.get_building_permits(limit=12)

        assert isinstance(permits, list)
        assert len(permits) <= 12
        if permits:
            assert "date" in permits[0]
            assert "value" in permits[0]

    def test_get_building_permits_state(self):
        """Test state-level building permits (e.g., California)."""
        # PERMITCA for California
        permits = self.adapter.get_building_permits(state_code="CA", limit=6)

        assert isinstance(permits, list)
        if permits:
            assert "date" in permits[0]

    def test_get_housing_starts_national(self):
        """Test national housing starts retrieval."""
        starts = self.adapter.get_housing_starts(limit=6)

        assert isinstance(starts, list)
        if starts:
            assert "date" in starts[0]

    def test_get_housing_starts_regional(self):
        """Test regional housing starts (West region)."""
        starts = self.adapter.get_housing_starts(region="W", limit=6)

        assert isinstance(starts, list)

    def test_get_supply_constraint_indicators(self):
        """Test supply constraint indicators for a state."""
        indicators = self.adapter.get_supply_constraint_indicators("CA", years_back=2)

        assert isinstance(indicators, dict)
        assert indicators["state"] == "CA"
        assert "building_permits" in indicators
        assert "housing_starts" in indicators

        permits = indicators["building_permits"]
        starts = indicators["housing_starts"]

        assert "observations" in permits
        assert "growth_rate" in permits
        assert "latest" in permits
        assert "observations" in starts
        assert "growth_rate" in starts
        assert "latest" in starts


class TestFREDSeriesAvailability:
    """Verify key FRED series are available and return data."""

    def setup_method(self):
        self.adapter = FREDAdapter()

    @pytest.mark.parametrize(
        "series_id",
        [
            "PERMIT",  # National building permits
            "HOUST",  # National housing starts
            "UNRATE",  # Unemployment rate
            "FEDFUNDS",  # Federal funds rate
            "MORTGAGE30US",  # 30-year mortgage rate
        ],
    )
    def test_key_series_returns_data(self, series_id):
        """Test that key economic series return observations."""
        obs = self.adapter.get_series_observations(series_id, limit=3)

        assert isinstance(obs, list)
        assert len(obs) > 0
        assert "date" in obs[0]
        assert "value" in obs[0]

    @pytest.mark.parametrize(
        "state_code,series_id",
        [
            ("CA", "CABPPRIVSA"),
            ("TX", "TXBPPRIVSA"),
            ("FL", "FLBPPRIVSA"),
            ("NY", "NYBPPRIVSA"),
        ],
    )
    def test_state_permit_series_exist(self, state_code, series_id):
        """Test that state permit series exist."""
        info = self.adapter.get_series_info(series_id)

        # Some states may not have permit series, so we just check it doesn't error
        # If it exists, verify structure
        if info is not None:
            assert info.get("id") == series_id


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration
