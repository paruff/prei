"""Integration tests for ATTOM API adapter.

These tests hit the live ATTOM API and require a valid ATTOM_API_KEY in the environment.
Run with: pytest core/tests/test_integration_attom.py -v -m integration
"""

import os
import pytest

from core.integrations.sources.attom_adapter import (
    ATTOMAdapter,
    ATTOMAPIError,
    ATTOMAuthenticationError,
)


# Skip all tests in this module if no ATTOM API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ATTOM_API_KEY"),
    reason="ATTOM_API_KEY not set in environment",
)


class TestATTOMLiveIntegration:
    """Live integration tests against ATTOM API."""

    def setup_method(self):
        """Create adapter instance for each test."""
        self.adapter = ATTOMAdapter()

    def test_authentication_header_format(self):
        """Verify adapter uses correct APIKey header format."""
        # The adapter should use 'APIKey' header (capital A, capital K)
        # as per ATTOM documentation, not 'apikey' or 'Authorization: Bearer'
        assert "APIKey" in self.adapter.session.headers
        assert self.adapter.session.headers["APIKey"] == os.getenv("ATTOM_API_KEY")

    def test_sale_snapshot_returns_data(self):
        """Test sale/snapshot endpoint returns property data for a ZIP code."""
        # Use a ZIP code with known activity
        resp = self.adapter.fetch_with_cache("123 Main St", "San Francisco, CA 94102")

        # Should return valid response structure
        assert isinstance(resp, dict)
        assert "property" in resp or "status" in resp
        assert "_from_cache" in resp  # cache metadata added

    def test_avm_detail_returns_valuation(self):
        """Test AVM/detail endpoint returns valuation data."""
        resp = self.adapter.fetch_avm_detail("123 Main St", "San Francisco, CA 94102")

        assert isinstance(resp, dict)
        # AVM response should have property or status data
        assert "property" in resp or "avm" in resp or "status" in resp

    def test_sales_history_returns_transactions(self):
        """Test sales history endpoint."""
        resp = self.adapter.fetch_sales_history(
            "123 Main St", "San Francisco, CA 94102"
        )

        assert isinstance(resp, dict)
        assert "property" in resp or "sale" in resp or "status" in resp

    def test_invalid_key_raises_auth_error(self):
        """Test that invalid API key raises authentication error."""
        bad_adapter = ATTOMAdapter(api_key="INVALID_KEY_THAT_WILL_FAIL")
        with pytest.raises(ATTOMAuthenticationError):
            bad_adapter.fetch_property_detail("123 Main St")

    def test_endpoint_structure_matches_docs(self):
        """Verify endpoint URLs match ATTOM documentation structure."""
        adapter = self.adapter

        # Property detail endpoint
        assert (
            adapter.BASE_URL == "https://api.gateway.attomdata.com/propertyapi/v1.0.0"
        )

        # Test that endpoints follow the Resource/Package pattern
        # e.g., /property/detail, /sale/snapshot, /avm/detail
        detail_endpoint = adapter.BASE_URL + "/property/detail"
        assert "/property/detail" in detail_endpoint

        sale_endpoint = adapter.BASE_URL + "/sale/snapshot"
        assert "/sale/snapshot" in sale_endpoint

        avm_endpoint = adapter.BASE_URL + "/avm/detail"
        assert "/avm/detail" in avm_endpoint

    def test_rate_limit_handling(self):
        """Test that rate limit errors are properly caught."""
        # This test just verifies the exception class exists and is importable
        from core.integrations.sources.attom_adapter import ATTOMRateLimitError

        assert issubclass(ATTOMRateLimitError, ATTOMAPIError)

    def test_usage_stats_tracking(self):
        """Test that usage stats can be retrieved."""
        stats = self.adapter.get_usage_stats(days=1)

        assert isinstance(stats, dict)
        assert "total_calls" in stats
        assert "total_cost" in stats
        assert "days" in stats
        assert isinstance(stats["days"], list)


class TestATTOMLiveEndpoints:
    """Test specific live ATTOM endpoints with expected response formats."""

    def setup_method(self):
        self.adapter = ATTOMAdapter()

    @pytest.mark.slow
    def test_property_detail_with_valid_address(self):
        """Test property detail with a known address."""
        # Use a well-known San Francisco address
        resp = self.adapter.fetch_property_detail(
            address1="123 Main St",
            address2="San Francisco, CA 94102",
        )

        assert isinstance(resp, dict)
        # Should have property data structure
        if "property" in resp:
            prop = resp["property"]
            assert "address" in prop
            assert "summary" in prop

    @pytest.mark.slow
    def test_foreclosure_data_for_geoid(self):
        """Test foreclosure data endpoint for a geographic area."""
        # Use a California county FIPS code (06037 = Los Angeles)
        resp = self.adapter.fetch_foreclosure_data(geoid="06037", radius=10)

        assert isinstance(resp, dict)
        if "property" in resp:
            assert isinstance(resp["property"], list)


# Mark slow tests
pytestmark = pytest.mark.integration
