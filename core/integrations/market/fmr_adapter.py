"""HUD Fair Market Rent (FMR) adapter for GACS rent benchmark.

Fetches HUD entity IDs from ``listCounties/{state}``, then retrieves
2BR FMR data for both current and prior fiscal years to compute
year-over-year rent growth.  The resulting 2BR FMR is a *rent floor
benchmark* (40th percentile), not a market rent estimate.

Requires ``HUD_API_KEY`` environment variable or Django setting.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, cast

from django.conf import settings

from core.integrations.market.hud_fmr import FMRClient

logger = logging.getLogger(__name__)

# Cache failed states to avoid spamming warnings for every city
_fmr_failed: set[str] = set()

CURRENT_FMR_YEAR = 2026
PRIOR_FMR_YEAR = 2025


def fetch_fmr_entity_id(state_code: str, city_name: str) -> str | None:
    """Look up the HUD entity ID for a county by city name.

    Calls ``listCounties/{state}`` and searches for a county whose
    name matches ``{city_name} County`` (case-insensitive).

    Args:
        state_code: 2-letter state code (e.g. ``"TX"``).
        city_name: City name (e.g. ``"Dallas"``).

    Returns:
        HUD entity ID string, or ``None`` if not found.
    """
    api_key = getattr(settings, "HUD_API_KEY", "")
    if not api_key:
        logger.warning("HUD_API_KEY not configured — cannot look up entity ID")
        return None

    client = FMRClient(api_key=api_key)
    try:
        counties = client.list_counties(state_code)
    except Exception as exc:
        if state_code not in _fmr_failed:
            logger.warning("Failed to list counties for %s: %s", state_code, exc)
            _fmr_failed.add(state_code)
        return None

    expected = f"{city_name} County".lower()
    for county in counties:
        cname = (county.get("county_name") or "").lower()
        if cname == expected:
            fips = county.get("fips_code", "")
            logger.info(
                "Found HUD entity %s for %s, %s",
                fips,
                city_name,
                state_code,
            )
            return fips

    logger.warning(
        "No HUD entity ID found for %s in %s",
        city_name,
        state_code,
    )
    return None


def fetch_fmr_data(
    state_code: str,
    county_fips: str,  # noqa: ARG001  # kept for API consistency with existing callers
    city_name: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Fetch HUD FMR 2BR rent benchmark and year-over-year growth.

    Args:
        state_code: 2-letter state code.
        county_fips: 5-character county FIPS code (reserved for future use).
        city_name: City name for entity ID lookup (fallback if
            *entity_id* not provided).
        entity_id: Optional pre-resolved HUD entity ID.  If not
            provided, ``fetch_fmr_entity_id`` is called with
            *city_name*.

    Returns:
        Dict with keys:
            ``fmr_2br`` — HUD FY2026 2BR Fair Market Rent (Decimal or None)
            ``fmr_year`` — Fiscal year of the current data (int)
            ``rent_growth_rate`` — Year-over-year 2BR FMR growth rate (Decimal or None)

        Returns ``None`` if the HUD API key is missing or the entity
        ID cannot be resolved.
    """
    api_key = getattr(settings, "HUD_API_KEY", "")
    if not api_key:
        logger.info("HUD_API_KEY not set — skipping FMR data fetch")
        return None

    if not entity_id:
        if not city_name:
            logger.warning("entity_id or city_name required to fetch FMR data")
            return None
        entity_id = fetch_fmr_entity_id(state_code, city_name)
        if not entity_id:
            return None

    client = FMRClient(api_key=api_key)

    # Fetch current year FMR
    current_data = client.get_county_data(entity_id, year=CURRENT_FMR_YEAR)
    if current_data is None or current_data.get("two_bedroom") is None:
        logger.info(
            "No FY%d FMR data for entity %s (%s, %s)",
            CURRENT_FMR_YEAR,
            entity_id,
            city_name,
            state_code,
        )
        return None

    fmr_2br = cast(Decimal, current_data["two_bedroom"])
    fmr_year = cast(int, current_data.get("year", CURRENT_FMR_YEAR))
    if isinstance(fmr_year, str):
        fmr_year = int(fmr_year)

    # Fetch prior year FMR for rent growth computation
    rent_growth_rate: Decimal | None = None
    prior_data = client.get_county_data(entity_id, year=PRIOR_FMR_YEAR)
    if prior_data is not None and prior_data.get("two_bedroom") is not None:
        prior_fmr = cast(Decimal, prior_data["two_bedroom"])
        if prior_fmr > 0:
            growth = (fmr_2br - prior_fmr) / prior_fmr
            # Round to 2 decimal places (e.g. 0.03 = 3%)
            rent_growth_rate = growth.quantize(Decimal("0.01"))
            logger.info(
                "FMR growth for %s: FY%d=%.0f, FY%d=%.0f, rate=%s",
                entity_id,
                PRIOR_FMR_YEAR,
                prior_fmr,
                CURRENT_FMR_YEAR,
                fmr_2br,
                rent_growth_rate,
            )

    return {
        "fmr_2br": fmr_2br,
        "fmr_year": fmr_year,
        "rent_growth_rate": rent_growth_rate,
    }
