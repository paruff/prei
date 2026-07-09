"""Tests for BLS QCEW county employment adapter."""

from core.integrations.market.bls_qcew import fetch_county_employment_growth


class TestBLSQCEW:
    """Tests for BLS QCEW county employment."""

    def test_returns_none_without_api_key(self) -> None:
        """Without BLS_API_KEY, returns None gracefully."""
        result = fetch_county_employment_growth("TX", "113", api_key="")
        assert result is None

    def test_returns_none_for_bad_state(self) -> None:
        """Invalid state code returns None."""
        result = fetch_county_employment_growth("XX", "113", api_key="test")
        assert result is None
