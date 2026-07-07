"""Tests for discovery-stage data sources and registry."""

import pytest
from unittest.mock import MagicMock, patch

from prei.pipeline.sources.base import DiscoverySource
from prei.pipeline.sources.county import (
    FloridaCountyForeclosureSource,
    TexasCountyForeclosureSource,
)
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
            (TexasCountyForeclosureSource, "tx_county_harris"),
        ],
    )
    def test_all_sources_have_name(self, cls, name):
        source = (
            cls() if cls != TexasCountyForeclosureSource else cls(county_key="harris")
        )
        assert isinstance(source, DiscoverySource)
        assert source.name is not None
        assert len(source.name) > 0

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_all_sources_return_list(self, mock_get, mock_post):
        mock_empty = MagicMock(status_code=200, json=lambda: {"results": []})
        mock_get.return_value = mock_empty
        mock_post.return_value = mock_empty
        for source_cls in [
            FannieMaeSource,
            HUDHomestoreSource,
            VAForeclosuresSource,
            USDAForeclosuresSource,
        ]:
            result = source_cls().fetch(state="CA")
            assert isinstance(result, list), (
                f"{source_cls.__name__} did not return a list"
            )

    @patch("prei.pipeline.sources.county.requests.get")
    def test_county_source_returns_list(self, mock_get):
        """County source with mocked HTTP returns a list."""
        mock_resp = MagicMock(
            status_code=200,
            text="case_number,address\n1,test",
            headers={"Content-Type": "text/csv"},
        )
        mock_get.return_value = mock_resp
        source = TexasCountyForeclosureSource(county="harris")
        result = source.fetch(state="TX", limit=1)
        assert isinstance(result, list)

    def test_county_source_accepts_county_param(self):
        source = TexasCountyForeclosureSource(county="harris")
        assert "harris" in source.name


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
        source = TexasCountyForeclosureSource(county_key="harris")
        assert "tx_county" in source.name
        assert "harris" in source.name

    def test_name_with_county_key(self):
        source = TexasCountyForeclosureSource(county_key="dallas")
        assert "dallas" in source.name

    def test_available_counties(self):
        counties = TexasCountyForeclosureSource.available_counties()
        assert "harris" in counties
        assert "dallas" in counties
        assert len(counties) >= 4

    def test_csv_fetch_returns_list(self):
        source = TexasCountyForeclosureSource(county_key="harris")
        result = source.fetch(state="TX")
        assert isinstance(result, list)


class TestFloridaCountyForeclosureSource:
    def test_name_with_county(self):
        source = FloridaCountyForeclosureSource(county_key="miami-dade")
        assert "miami-dade" in source.name

    def test_available_counties(self):
        counties = FloridaCountyForeclosureSource.available_counties()
        assert "miami-dade" in counties
        assert "orange" in counties


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

        source = get_source("county_tx", county="harris")
        assert isinstance(source, TexasCountyForeclosureSource)
        assert "harris" in source.name

    def test_get_source_invalid(self):
        with pytest.raises(ValueError, match="Unknown source"):
            get_source("nonexistent_source")

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_discover_from_all(self, mock_get, mock_post):
        """Returns dict with all source names; each value is a list."""
        mock_empty = MagicMock(status_code=200, json=lambda: {"results": []})
        mock_get.return_value = mock_empty
        mock_post.return_value = mock_empty
        result = discover_from_all(state="CA")
        assert isinstance(result, dict)
        for name in list_sources():
            assert name in result
            assert isinstance(result[name], list)

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_discover_from_all_with_filter(self, mock_get, mock_post):
        mock_empty = MagicMock(status_code=200, json=lambda: {"results": []})
        mock_get.return_value = mock_empty
        mock_post.return_value = mock_empty
        result = discover_from_all(state="TX", source_filter=["fannie_mae", "hud"])
        assert set(result.keys()) == {"fannie_mae", "hud"}

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_discover_from_all_source_failure_does_not_crash(self, mock_get, mock_post):
        """One source failing doesn't prevent others from running."""
        mock_empty = MagicMock(status_code=200, json=lambda: {"results": []})
        mock_get.return_value = mock_empty
        mock_post.return_value = mock_empty
        result = discover_from_all(state="CA")
        for name in list_sources():
            assert result[name] == []
