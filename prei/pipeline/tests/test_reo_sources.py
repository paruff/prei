"""Integration tests for REO and county data sources."""

from unittest.mock import patch, MagicMock
from prei.pipeline.sources.reo_sources import (
    FannieMaeSource,
    HUDHomestoreSource,
    VAForeclosuresSource,
    USDAForeclosuresSource,
)
from prei.pipeline.sources.county import (
    TexasCountyForeclosureSource,
    FloridaCountyForeclosureSource,
)
from prei.pipeline.sources.base import DiscoverySource


# ═══════════════════════════════════════════════════════════════════════════════
#  Mock helpers
# ═══════════════════════════════════════════════════════════════════════════════

FANNIE_RESPONSE = {
    "results": [
        {
            "propertyId": "FM-100",
            "address": "123 Main St, Dallas, TX",
            "price": 250000,
            "bedrooms": 3,
            "bathrooms": 2,
            "squareFeet": 1800,
        },
        {
            "propertyId": "FM-101",
            "address": "456 Oak Ave, Houston, TX",
            "price": 210000,
            "bedrooms": 4,
            "bathrooms": 2,
            "squareFeet": 2000,
        },
    ]
}

HUD_RESPONSE = {
    "results": [
        {
            "caseNumber": "HUD-500",
            "displayAddress": "789 Pine Rd, Miami, FL",
            "currentPrice": 180000,
            "bedrooms": 3,
            "bathrooms": 1,
        },
    ]
}

VA_RESPONSE = {
    "data": [
        {
            "propertyNumber": "VA-10",
            "street": "100 Vet Ave",
            "city": "Austin",
            "state": "TX",
            "listPrice": 220000,
            "bedrooms": 3,
            "bathrooms": 2,
        },
    ]
}

COUNTY_CSV = "case_number,property_address,city,state,zip,opening_bid,beds,baths,square_feet,sale_date\n"
COUNTY_CSV += (
    "NOD-2024-001,100 Foreclosure Dr,Houston,TX,77002,150000,3,2,1600,2024-06-15\n"
)
COUNTY_CSV += "NTS-2024-002,200 Default Ln,Dallas,TX,75201,200000,4,2,1800,2024-07-01\n"


# ═══════════════════════════════════════════════════════════════════════════════
#  Fannie Mae
# ═══════════════════════════════════════════════════════════════════════════════


class TestFannieMaeIntegration:
    @patch("prei.pipeline.sources.reo_sources.requests.post")
    def test_fetch_returns_mapped_listings(self, mock_post):
        mock_resp = MagicMock(status_code=200, json=lambda: FANNIE_RESPONSE)
        mock_post.return_value = mock_resp
        source = FannieMaeSource()
        results = source.fetch(state="TX")
        assert len(results) == 2
        assert results[0]["id"] == "fm-FM-100"
        assert results[0]["price"] == 250000
        assert results[0]["beds"] == 3

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    def test_fetch_with_zip(self, mock_post):
        mock_resp = MagicMock(status_code=200, json=lambda: {"properties": []})
        mock_post.return_value = mock_resp
        source = FannieMaeSource()
        results = source.fetch(state="TX", zip_code="77002")
        assert results == []

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    def test_fetch_handles_api_error(self, mock_post):
        mock_post.side_effect = __import__("requests").exceptions.ConnectionError()
        source = FannieMaeSource()
        results = source.fetch(state="TX")
        assert results == []  # graceful fallback

    @patch("prei.pipeline.sources.reo_sources.requests.post")
    def test_fetch_handles_503(self, mock_post):
        mock_resp = MagicMock(status_code=503)
        mock_post.return_value = mock_resp
        source = FannieMaeSource()
        results = source.fetch(state="TX")
        assert results == []

    def test_name_property(self):
        assert FannieMaeSource().name == "fannie_mae"

    def test_is_discovery_source(self):
        assert isinstance(FannieMaeSource(), DiscoverySource)


# ═══════════════════════════════════════════════════════════════════════════════
#  HUD Homestore
# ═══════════════════════════════════════════════════════════════════════════════


class TestHUDIntegration:
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_fetch_returns_mapped_listings(self, mock_get):
        mock_resp = MagicMock(status_code=200, json=lambda: HUD_RESPONSE)
        mock_get.return_value = mock_resp
        source = HUDHomestoreSource()
        results = source.fetch(state="FL")
        assert len(results) == 1
        assert results[0]["id"] == "hud-HUD-500"
        assert results[0]["price"] == 180000

    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_fetch_handles_connection_error(self, mock_get):
        mock_get.side_effect = __import__("requests").exceptions.ConnectionError()
        source = HUDHomestoreSource()
        results = source.fetch(state="FL")
        assert results == []

    def test_name_property(self):
        assert HUDHomestoreSource().name == "hud"


# ═══════════════════════════════════════════════════════════════════════════════
#  VA
# ═══════════════════════════════════════════════════════════════════════════════


class TestVAIntegration:
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_fetch_returns_mapped_listings(self, mock_get):
        mock_resp = MagicMock(status_code=200, json=lambda: VA_RESPONSE)
        mock_get.return_value = mock_resp
        source = VAForeclosuresSource()
        results = source.fetch(state="TX")
        assert len(results) == 1
        assert results[0]["id"] == "va-VA-10"
        assert results[0]["price"] == 220000

    def test_name_property(self):
        assert VAForeclosuresSource().name == "va"


# ═══════════════════════════════════════════════════════════════════════════════
#  USDA
# ═══════════════════════════════════════════════════════════════════════════════


class TestUSDAIntegration:
    @patch("prei.pipeline.sources.reo_sources.requests.get")
    def test_fetch_empty_batch(self, mock_get):
        mock_resp = MagicMock(status_code=200, json=lambda: {"properties": []})
        mock_get.return_value = mock_resp
        source = USDAForeclosuresSource()
        results = source.fetch(state="FL")
        assert results == []

    def test_name_property(self):
        assert USDAForeclosuresSource().name == "usda"


# ═══════════════════════════════════════════════════════════════════════════════
#  Texas County
# ═══════════════════════════════════════════════════════════════════════════════


class TestCountyIntegration:
    @patch("prei.pipeline.sources.county.requests.get")
    def test_csv_parsing(self, mock_get):
        mock_resp = MagicMock(
            status_code=200,
            text=COUNTY_CSV,
            headers={"Content-Type": "text/csv"},
        )
        mock_get.return_value = mock_resp
        source = TexasCountyForeclosureSource(county_key="harris")
        results = source.fetch()
        assert len(results) == 2
        assert results[0]["id"] == "NOD-2024-001"
        assert results[0]["price"] == 150000.0

    def test_available_counties(self):
        counties = TexasCountyForeclosureSource.available_counties()
        assert "harris" in counties
        assert "dallas" in counties
        assert len(counties) >= 4

    def test_florida_available_counties(self):
        counties = FloridaCountyForeclosureSource.available_counties()
        assert "miami-dade" in counties
        assert "orange" in counties

    def test_name_includes_county(self):
        source = TexasCountyForeclosureSource(county_key="harris")
        assert "harris" in source.name
        source2 = FloridaCountyForeclosureSource(county_key="miami-dade")
        assert "miami-dade" in source2.name
