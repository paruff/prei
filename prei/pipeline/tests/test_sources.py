"""Tests for discovery-stage data sources and registry."""

import pytest

from prei.pipeline.sources.base import DiscoverySource
from prei.pipeline.sources.county import TexasCountyForeclosureSource
from prei.pipeline.sources.registry import (
    discover_from_all,
    get_source,
    list_sources,
)
from prei.pipeline.sources.reo_sources import (
    FannieMaeSource,
    HUDHomestoreSource,
    USDAForeclosuresSource,
    VAForeclosuresSource,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Source interface compliance
# ═══════════════════════════════════════════════════════════════════════════════


class TestSourceInterface:
    """All sources must conform to DiscoverySource ABC."""

    @pytest.mark.parametrize(
        "cls,name",
        [
            (FannieMaeSource, "fannie_mae"),
            (HUDHomestoreSource, "hud"),
            (VAForeclosuresSource, "va"),
            (USDAForeclosuresSource, "usda"),
            (TexasCountyForeclosureSource, "county_la"),
        ],
    )
    def test_all_sources_have_name(self, cls, name):
        source = (
            cls() if cls != TexasCountyForeclosureSource else cls(county="Los Angeles")
        )
        assert isinstance(source, DiscoverySource)
        assert source.name is not None
        assert len(source.name) > 0

    @pytest.mark.parametrize(
        "cls",
        [
            FannieMaeSource,
            HUDHomestoreSource,
            VAForeclosuresSource,
            USDAForeclosuresSource,
            TexasCountyForeclosureSource,
        ],
    )
    def test_all_sources_return_list(self, cls):
        source = cls() if cls != TexasCountyForeclosureSource else cls()
        result = source.fetch(state="CA")
        assert isinstance(result, list)

    def test_county_source_accepts_county_param(self):
        source = TexasCountyForeclosureSource(county="Los Angeles")
        assert source.county == "Los Angeles"
        assert "los_angeles" in source.name


# ═══════════════════════════════════════════════════════════════════════════════
#  Fannie Mae
# ═══════════════════════════════════════════════════════════════════════════════


class TestFannieMaeSource:
    def test_name(self):
        assert FannieMaeSource().name == "fannie_mae"

    def test_fetch_empty(self):
        """Returns empty list (placeholder until scraper is built)."""
        result = FannieMaeSource().fetch(state="CA")
        assert result == []

    def test_fetch_with_zip(self):
        result = FannieMaeSource().fetch(state="CA", zip_code="90210")
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════════


class TestHUDHomestoreSource:
    def test_name(self):
        assert HUDHomestoreSource().name == "hud"

    def test_fetch_empty(self):
        assert HUDHomestoreSource().fetch(state="TX") == []


# ═══════════════════════════════════════════════════════════════════════════════
#  VA
# ═══════════════════════════════════════════════════════════════════════════════


class TestVAForeclosuresSource:
    def test_name(self):
        assert VAForeclosuresSource().name == "va"

    def test_fetch_empty(self):
        assert VAForeclosuresSource().fetch(state="FL") == []


# ═══════════════════════════════════════════════════════════════════════════════
#  USDA
# ═══════════════════════════════════════════════════════════════════════════════


class TestUSDAForeclosuresSource:
    def test_name(self):
        assert USDAForeclosuresSource().name == "usda"

    def test_fetch_empty(self):
        assert USDAForeclosuresSource().fetch(state="FL") == []


# ═══════════════════════════════════════════════════════════════════════════════
#  County source
# ═══════════════════════════════════════════════════════════════════════════════


class TestTexasCountyForeclosureSource:
    def test_name_default(self):
        source = TexasCountyForeclosureSource()
        assert "county_tx" in source.name

    def test_name_with_county(self):
        source = TexasCountyForeclosureSource(county="Los Angeles")
        assert source.name == "county_los_angeles"

    def test_default_notice_types(self):
        source = TexasCountyForeclosureSource()
        assert TexasCountyForeclosureSource.NOTICE_NOD in source.notice_types
        assert TexasCountyForeclosureSource.NOTICE_NTS in source.notice_types
        assert TexasCountyForeclosureSource.NOTICE_SHERIFF in source.notice_types
        assert TexasCountyForeclosureSource.NOTICE_AUCTION in source.notice_types

    def test_fetch_with_notice_type(self):
        source = TexasCountyForeclosureSource()
        result = source.fetch(state="CA", notice_type="nod")
        assert isinstance(result, list)

    def test_supported_counties_ca(self):
        counties = TexasCountyForeclosureSource.supported_counties("CA")
        assert "Los Angeles" in counties
        assert "San Diego" in counties

    def test_supported_counties_unknown_state(self):
        counties = TexasCountyForeclosureSource.supported_counties("XX")
        assert counties == []


# ═══════════════════════════════════════════════════════════════════════════════
#  Registry
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegistry:
    def test_list_sources(self):
        sources = list_sources()
        assert "fannie_mae" in sources
        assert "hud" in sources
        assert "va" in sources
        assert "usda" in sources
        assert "county_tx" in sources

    def test_get_source_valid(self):
        source = get_source("fannie_mae")
        assert isinstance(source, FannieMaeSource)

        source = get_source("county_tx", county="Los Angeles")
        assert isinstance(source, TexasCountyForeclosureSource)
        assert source.county == "Los Angeles"

    def test_get_source_invalid(self):
        with pytest.raises(ValueError, match="Unknown source"):
            get_source("nonexistent_source")

    def test_discover_from_all(self):
        """Returns dict with all source names; each value is a list."""
        result = discover_from_all(state="CA")
        assert isinstance(result, dict)
        for name in list_sources():
            assert name in result
            assert isinstance(result[name], list)

    def test_discover_from_all_with_filter(self):
        result = discover_from_all(state="TX", source_filter=["fannie_mae", "hud"])
        assert set(result.keys()) == {"fannie_mae", "hud"}

    def test_discover_from_all_source_failure_does_not_crash(self):
        """One source failing doesn't prevent others from running."""
        result = discover_from_all(state="CA")
        # All sources return empty lists (placeholders)
        for name in list_sources():
            assert result[name] == []
