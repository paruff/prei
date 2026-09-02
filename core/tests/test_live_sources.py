"""Live integration tests for property discovery sources and external APIs.

These tests hit real external services and are gated by API key presence.
Run with:  make test-live-sources
Skipped automatically when required keys are missing.
"""

from __future__ import annotations

import os

import pytest
from django.conf import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _key(name: str) -> str:
    """Return the raw value of an env/Django key, empty string if absent."""
    return getattr(settings, name, "") or os.environ.get(name, "")


# ---------------------------------------------------------------------------
# Key presence
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_hud_fmr_token_present() -> None:
    """HUD_FMR_TOKEN or HUD_API_KEY must be configured for FMR tests."""
    key = _key("HUD_FMR_TOKEN") or _key("HUD_API_KEY")
    assert key, "HUD_FMR_TOKEN or HUD_API_KEY not configured"


@pytest.mark.live
def test_attom_api_key_present() -> None:
    """ATTOM_API_KEY must be configured for ATTOM tests."""
    assert _key("ATTOM_API_KEY"), "ATTOM_API_KEY not configured"


@pytest.mark.live
def test_census_api_key_present() -> None:
    """CENSUS_API_KEY must be configured for Census tests."""
    assert _key("CENSUS_API_KEY"), "CENSUS_API_KEY not configured"


@pytest.mark.live
def test_fred_api_key_present() -> None:
    """FRED_API_KEY must be configured for FRED tests."""
    assert _key("FRED_API_KEY"), "FRED_API_KEY not configured"


# ---------------------------------------------------------------------------
# Tarrant County — live fetch
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_tarrant_county_live_fetch() -> None:
    """Tarrant County source must connect and return listings."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
    django.setup()

    from core.services.sources.county import TexasCountyForeclosureSource

    source = TexasCountyForeclosureSource(county="tarrant")
    listings = source.fetch()
    assert len(listings) > 0, "Tarrant source returned 0 listings — feed may be down"
    sample = listings[0]
    assert "id" in sample
    assert sample.get("county") == "Tarrant"
    assert sample.get("state") == "TX"
    assert sample.get("source_url"), "source_url missing"


# ---------------------------------------------------------------------------
# VA VRM scraper — live fetch
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_va_vrm_scraper_live_fetch() -> None:
    """VRM scraper must connect to vrmproperties.com and return VA listings."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
    django.setup()

    from core.integrations.sources.vrm_scraper import VrmScraper

    scraper = VrmScraper(delay_seconds=0.3)
    props = scraper.collect_state_listings("VA")
    assert len(props) > 0, "VRM scraper returned 0 VA listings — site may be down"
    sample = props[0]
    assert "address" in sample
    assert sample.get("state") == "VA"
    assert "list_price" in sample


# ---------------------------------------------------------------------------
# HUD FMR API — live connection
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_hud_fmr_list_counties_tx() -> None:
    """HUD FMR API must return Texas counties when a valid token is present."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
    django.setup()

    from core.integrations.market.hud_fmr import FMRClient

    token = _key("HUD_FMR_TOKEN") or _key("HUD_API_KEY")
    client = FMRClient(api_key=token)
    counties = client.list_counties("TX")
    assert len(counties) > 0, (
        "HUD FMR returned 0 TX counties — token may lack FMR permission"
    )
    tarrant = [c for c in counties if "Tarrant" in c.get("county_name", "")]
    assert tarrant, "Tarrant County not found in HUD FMR response"


# ---------------------------------------------------------------------------
# Census API — live connection
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_census_place_growth_metrics() -> None:
    """Census API must return growth metrics for Fort Worth, TX (place FIPS 27000)."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
    django.setup()

    from core.integrations.market.census import fetch_place_growth_metrics

    api_key = _key("CENSUS_API_KEY")
    result = fetch_place_growth_metrics("TX", "27000", api_key, place_name="Fort Worth")
    assert result is not None, (
        "Census API returned None — key may be invalid or rate-limited"
    )
    assert result.get("population_current", 0) > 0, "Census returned zero population"
    assert "population_growth_rate" in result


# ---------------------------------------------------------------------------
# FRED / BLS — live connection
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_fred_employment_growth_tx() -> None:
    """FRED/BLS must return employment growth for Texas."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
    django.setup()

    from core.integrations.market.bls import fetch_employment_growth

    api_key = _key("FRED_API_KEY")
    growth_rate = fetch_employment_growth("TX", api_key)
    assert growth_rate is not None, "FRED/BLS returned None — key may be invalid"
    assert growth_rate > 0, "Employment growth should be positive"
