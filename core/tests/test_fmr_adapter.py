"""Tests for the HUD FMR adapter (GACS-FMR-1).

Covers:
  - fetch_fmr_entity_id: entity ID lookup by city name
  - fetch_fmr_data: full fetch with mocked HUD API
  - Missing API key returns None
  - Entity ID not found returns None
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

from core.integrations.market.fmr_adapter import fetch_fmr_data, fetch_fmr_entity_id
from core.integrations.market.hud_fmr import get_rent_estimate


# ── Entity ID lookup ─────────────────────────────────────────────────


def test_fetch_entity_id_found() -> None:
    """Matching county name returns the HUD entity ID."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.list_counties"
        ) as mock_list,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_list.return_value = [
            {"fips_code": "4804800999", "county_name": "Dallas County"},
            {"fips_code": "4820100000", "county_name": "Harris County"},
        ]
        entity = fetch_fmr_entity_id("TX", "Dallas")
        assert entity == "4804800999"


def test_fetch_entity_id_not_found() -> None:
    """Non-matching city name returns None."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.list_counties"
        ) as mock_list,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_list.return_value = [
            {"fips_code": "4804800999", "county_name": "Dallas County"},
        ]
        entity = fetch_fmr_entity_id("TX", "Nowhere")
        assert entity is None


def test_fetch_entity_id_no_api_key() -> None:
    """Missing HUD_API_KEY returns None."""
    with patch("core.integrations.market.fmr_adapter.settings") as mock_settings:
        mock_settings.HUD_API_KEY = ""
        entity = fetch_fmr_entity_id("TX", "Dallas")
        assert entity is None


def test_fetch_entity_id_api_error() -> None:
    """API error during list_counties returns None (graceful deg)."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.list_counties"
        ) as mock_list,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_list.side_effect = Exception("API down")
        entity = fetch_fmr_entity_id("TX", "Dallas")
        assert entity is None


# ── Full FMR data fetch ─────────────────────────────────────────────


def _mock_current() -> dict:
    return {
        "fips_code": "4804800999",
        "county_name": "Dallas County",
        "year": "2026",
        "two_bedroom": Decimal("1520"),
    }


def _mock_prior() -> dict:
    return {
        "fips_code": "4804800999",
        "county_name": "Dallas County",
        "year": "2025",
        "two_bedroom": Decimal("1460"),
    }


def _small_area_current() -> dict:
    return {
        "data": {
            "county_name": "Dallas County",
            "metro_name": "Dallas, TX HUD Metro FMR Area",
            "basicdata": [
                {
                    "ZIP Code": "75201",
                    "year": "2026",
                    "Efficiency": "1200",
                    "One-Bedroom": "1450",
                    "Two-Bedroom": "1700",
                    "Three-Bedroom": "2150",
                    "Four-Bedroom": "2500",
                },
                {
                    "ZIP Code": "MSA level",
                    "year": "2026",
                    "Efficiency": "1000",
                    "One-Bedroom": "1250",
                    "Two-Bedroom": "1500",
                    "Three-Bedroom": "1900",
                    "Four-Bedroom": "2250",
                },
            ],
        }
    }


def _small_area_prior() -> dict:
    return {
        "data": {
            "county_name": "Dallas County",
            "metro_name": "Dallas, TX HUD Metro FMR Area",
            "basicdata": [
                {
                    "ZIP Code": "MSA level",
                    "year": "2025",
                    "Efficiency": "950",
                    "One-Bedroom": "1175",
                    "Two-Bedroom": "1400",
                    "Three-Bedroom": "1775",
                    "Four-Bedroom": "2100",
                }
            ],
        }
    }


@pytest.mark.django_db
def test_fetch_fmr_data_full() -> None:
    """Happy path: returns fmr_2br, fmr_year, and rent_growth_rate."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch("core.integrations.market.fmr_adapter.fetch_fmr_entity_id") as mock_eid,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.get_county_data"
        ) as mock_data,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_eid.return_value = "4804800999"
        mock_data.side_effect = [_mock_current(), _mock_prior()]

        result = fetch_fmr_data("TX", "48113", city_name="Dallas")

    assert result is not None
    assert result["fmr_2br"] == Decimal("1520")
    assert result["fmr_year"] == 2026
    # (1520 - 1460) / 1460 = 60/1460 ≈ 0.0410 → rounded to 0.04
    assert result["rent_growth_rate"] == Decimal("0.04")


@pytest.mark.django_db
def test_fetch_fmr_data_entity_provided() -> None:
    """When entity_id is provided skip lookup."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.get_county_data"
        ) as mock_data,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_data.side_effect = [_mock_current(), _mock_prior()]

        result = fetch_fmr_data("TX", "48113", entity_id="4804800999")

    assert result is not None
    assert result["fmr_2br"] == Decimal("1520")


@pytest.mark.django_db
def test_fetch_fmr_data_no_current() -> None:
    """Current year data missing returns None."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch("core.integrations.market.fmr_adapter.fetch_fmr_entity_id") as mock_eid,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.get_county_data"
        ) as mock_data,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_eid.return_value = "4804800999"
        mock_data.return_value = None  # current year fails

        result = fetch_fmr_data("TX", "48113", city_name="Dallas")
        assert result is None


@pytest.mark.django_db
def test_fetch_fmr_data_no_growth() -> None:
    """Prior year missing: rent_growth_rate is None, but fmr_2br still returned."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch("core.integrations.market.fmr_adapter.fetch_fmr_entity_id") as mock_eid,
        patch(
            "core.integrations.market.fmr_adapter.FMRClient.get_county_data"
        ) as mock_data,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_eid.return_value = "4804800999"
        # Current year succeeds, prior year fails
        mock_data.side_effect = [_mock_current(), None]

        result = fetch_fmr_data("TX", "48113", city_name="Dallas")

    assert result is not None
    assert result["fmr_2br"] == Decimal("1520")
    assert result["rent_growth_rate"] is None


@pytest.mark.django_db
def test_fetch_fmr_data_no_api_key() -> None:
    """Missing HUD_API_KEY returns None."""
    with patch("core.integrations.market.fmr_adapter.settings") as mock_settings:
        mock_settings.HUD_API_KEY = ""
        result = fetch_fmr_data("TX", "48113")
        assert result is None


@pytest.mark.django_db
def test_fetch_fmr_data_no_city_name() -> None:
    """No city_name and no entity_id returns None."""
    with patch("core.integrations.market.fmr_adapter.settings") as mock_settings:
        mock_settings.HUD_API_KEY = "test-key"
        result = fetch_fmr_data("TX", "48113")
        assert result is None


@pytest.mark.django_db
def test_fetch_fmr_data_small_area_uses_msa_row() -> None:
    """Small Area basicdata lists should fall back to MSA-level row."""
    with (
        patch("core.integrations.market.fmr_adapter.settings") as mock_settings,
        patch("core.integrations.market.hud_fmr.FMRClient._get") as mock_get,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_get.side_effect = [_small_area_current(), _small_area_prior()]

        result = fetch_fmr_data("TX", "48113", entity_id="4811399999")

    assert result is not None
    assert result["fmr_2br"] == Decimal("1500")
    assert result["fmr_year"] == 2026
    assert result["rent_growth_rate"] == Decimal("0.07")


def test_get_rent_estimate_small_area_uses_zip_and_entity_id() -> None:
    """5-digit FIPS should map to HUD entity id and select the ZIP row."""
    with (
        patch("core.integrations.market.hud_fmr.settings") as mock_settings,
        patch("core.integrations.market.hud_fmr.FMRClient._get") as mock_get,
    ):
        mock_settings.HUD_API_KEY = "test-key"
        mock_get.return_value = _small_area_current()

        rent = get_rent_estimate(zip_code="75201", fips_code="48113", bedrooms=2)

    assert rent == Decimal("1700")
    assert mock_get.call_args.args[0] == "data/4811399999"
