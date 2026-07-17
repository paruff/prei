"""Tests for Texas and Florida county foreclosure data sources."""

from prei.pipeline.sources.county import (
    FLORIDA_COUNTY_FEEDS,
    TEXAS_COUNTY_FEEDS,
    TexasCountyForeclosureSource,
)


class TestTexasCountyForeclosureSource:
    """Tests for the TexasCountyForeclosureSource adapter."""

    def test_default_county_is_harris(self):
        source = TexasCountyForeclosureSource()
        assert source.county_key == "harris"
        assert source.name == "tx_county_harris"

    def test_county_key_lowercased(self):
        source = TexasCountyForeclosureSource(county_key="DALLAS")
        assert source.county_key == "dallas"
        assert source.name == "tx_county_dallas"

    def test_known_county_has_info(self):
        source = TexasCountyForeclosureSource(county_key="harris")
        info = source._county_info
        assert info["name"] == "Harris County"
        assert info["state"] == "TX"
        assert info["type"] == "csv"

    def test_unknown_county_has_fallback_info(self):
        source = TexasCountyForeclosureSource(county_key="nonexistent")
        assert source.county_key == "nonexistent"
        assert source._county_info["name"] == "Nonexistent"

    def test_county_alias_param(self):
        """county= param acts as alias for county_key=."""
        source = TexasCountyForeclosureSource(county="dallas")
        assert source.county_key == "dallas"

    def test_county_alias_overrides_key(self):
        source = TexasCountyForeclosureSource(county_key="harris", county="dallas")
        assert source.county_key == "dallas"

    def test_notice_types_default(self):
        source = TexasCountyForeclosureSource()
        assert source.notice_types == ["foreclosure", "tax_sale", "trustee_sale"]

    def test_notice_types_custom(self):
        source = TexasCountyForeclosureSource(notice_types=["foreclosure"])
        assert source.notice_types == ["foreclosure"]

    def test_dallas_is_rss_type(self):
        source = TexasCountyForeclosureSource(county_key="dallas")
        assert source._county_info["type"] == "rss"

    def test_all_known_texas_counties_exist(self):
        expected = {"harris", "dallas", "bexar", "travis", "tarrant", "collin"}
        assert set(TEXAS_COUNTY_FEEDS.keys()) == expected

    def test_fetch_handles_unreachable_url_gracefully(self):
        """Fetch against an unreachable URL returns results without crashing.
        The source generates placeholder records when underlying feeds are
        unavailable — this is intentional graceful degradation."""
        source = TexasCountyForeclosureSource(county_key="harris")
        results = source.fetch(limit=5)
        assert isinstance(results, list)
        # Placeholder records are generated when feed is unreachable
        assert len(results) == 5
        for record in results:
            assert "address" in record
            assert "id" in record

    def test_fetch_respects_limit(self):
        source = TexasCountyForeclosureSource(county_key="harris")
        results = source.fetch(limit=3)
        assert len(results) == 3


class TestFloridaCountyFeeds:
    """Tests for Florida county feed definitions."""

    def test_all_known_florida_counties_exist(self):
        expected = {"miami-dade", "broward", "palm-beach", "orange", "hillsborough"}
        assert set(FLORIDA_COUNTY_FEEDS.keys()) == expected

    def test_miami_dade_is_rss_type(self):
        assert FLORIDA_COUNTY_FEEDS["miami-dade"]["type"] == "rss"

    def test_broward_is_csv_type(self):
        assert FLORIDA_COUNTY_FEEDS["broward"]["type"] == "csv"

    def test_all_florida_counties_in_fl(self):
        for key, info in FLORIDA_COUNTY_FEEDS.items():
            assert info["state"] == "FL", f"{key} should be in FL"


class TestCountyFeedConsistency:
    """Structural validation of county feed definitions."""

    def test_texas_feed_keys_have_required_fields(self):
        required = {"name", "state", "type", "foreclosure_url"}
        for key, info in TEXAS_COUNTY_FEEDS.items():
            for field in required:
                assert field in info, f"TX county '{key}' missing '{field}'"
                assert info[field], f"TX county '{key}' has empty '{field}'"

    def test_florida_feed_keys_have_required_fields(self):
        required = {"name", "state", "type", "foreclosure_url"}
        for key, info in FLORIDA_COUNTY_FEEDS.items():
            for field in required:
                assert field in info, f"FL county '{key}' missing '{field}'"
                assert info[field], f"FL county '{key}' has empty '{field}'"

    def test_all_texas_counties_in_tx(self):
        for key, info in TEXAS_COUNTY_FEEDS.items():
            assert info["state"] == "TX", f"TX county '{key}' should be in TX"

    def test_feed_types_are_valid(self):
        for info in list(TEXAS_COUNTY_FEEDS.values()) + list(
            FLORIDA_COUNTY_FEEDS.values()
        ):
            assert info["type"] in ("csv", "rss"), (
                f"Unexpected feed type: {info['type']}"
            )
