"""HUD Fair Market Rent (FMR) API adapter.

Fetches annual rent estimates by county and ZIP code from HUD's
Fair Market Rent database.  Free API key available at:
  https://www.huduser.gov/portal/dataset/fmr-api.html

FMRs are 40th-percentile gross rent estimates for standard quality
units, published annually by county and ZIP code (Small Area FMRs)
for 0BR through 4BR unit sizes.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, cast

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

FMR_API_BASE = "https://www.huduser.gov/hudapi/public/fmr"
REQUEST_TIMEOUT = 30
FMR_YEAR = 2026  # fiscal year queried; HUD's default year is older


class FMRError(Exception):
    """Base exception for HUD FMR API errors."""


class FMRClient:
    """Client for the HUD Fair Market Rent API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (
            api_key
            or getattr(settings, "HUD_FMR_TOKEN", "")
            or getattr(settings, "HUD_API_KEY", "")
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """Make a GET request to the HUD FMR API."""
        url = f"{FMR_API_BASE}/{path.lstrip('/')}"
        resp = requests.get(
            url, headers=self._headers(), params=params, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 401:
            raise FMRError("HUD API key is missing or invalid")
        if resp.status_code == 403:
            raise FMRError(
                "HUD API key not authorized for FMR dataset. "
                "The key authenticates (not a 401) but lacks FMR permission. "
                "Fix:\n"
                "1. Go to https://www.huduser.gov/portal/dataset/fmr-api.html\n"
                "2. Ensure FAIR MARKET RENT is the Selected Dataset\n"
                "3. Create a NEW token (tokens created before selecting FMR\n"
                "   may not have FMR access even if the dataset is now selected)\n"
                "4. Set the new token as HUD_API_KEY in your environment"
            )
        if resp.status_code == 404:
            raise FMRError(f"No data found: {path}")
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return {"data": data}  # API returned list, wrap in dict
        return cast(dict[str, Any], data)

    def list_states(self) -> list[dict[str, str]]:
        """List all states with FMR data."""
        data = self._get("listStates")
        return cast(list[dict[str, str]], data.get("data", []))

    def list_counties(self, state_code: str) -> list[dict[str, str]]:
        """List counties in a state with their FIPS codes."""
        data = self._get(f"listCounties/{state_code}")
        return cast(list[dict[str, str]], data.get("data", []))

    def get_county_data(
        self,
        fips_code: str,
        year: int | None = None,
        zip_code: str | None = None,
    ) -> dict[str, Any] | None:
        """Get FMR data for a specific county by FIPS code.

        Returns a dict with rent estimates for 0BR-4BR units,
        or ``None`` if no data is found.
        """
        params = {"year": str(year)} if year else {}
        try:
            data = self._get(f"data/{fips_code}", params=params)
        except FMRError:
            return None

        result = data.get("data", {})
        basic = _select_basicdata_row(result.get("basicdata"), zip_code)
        if not basic:
            return None

        return {
            "fips_code": fips_code,
            "county_name": result.get("county_name", ""),
            "metro_name": result.get("metro_name", ""),
            "year": _field_value(basic, "year") or str(year or "latest"),
            "efficiency": _parse_fmr(_field_value(basic, "Efficiency")),
            "one_bedroom": _parse_fmr(_field_value(basic, "One-Bedroom")),
            "two_bedroom": _parse_fmr(_field_value(basic, "Two-Bedroom")),
            "three_bedroom": _parse_fmr(_field_value(basic, "Three-Bedroom")),
            "four_bedroom": _parse_fmr(_field_value(basic, "Four-Bedroom")),
        }

    def get_state_data(self, state_code: str) -> list[dict[str, Any]]:
        """Get FMR data for all counties/metro areas in a state."""
        data = self._get(f"statedata/{state_code}")
        result = data.get("data", {})
        return cast(
            list[dict[str, Any]],
            result.get("counties", []) + result.get("metroareas", []),
        )


def _parse_fmr(value: Any) -> Decimal | None:
    """Parse an FMR value to Decimal."""
    if value is None or value == "":
        return None
    try:
        return cast(Decimal, Decimal(str(value)))
    except Exception:
        return None


def _normalize_field_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _field_value(row: dict[str, Any], *candidates: str) -> Any:
    for key in candidates:
        if key in row:
            return row[key]

    normalized_candidates = {_normalize_field_name(key) for key in candidates}
    for key, value in row.items():
        if _normalize_field_name(str(key)) in normalized_candidates:
            return value
    return None


def _zip5(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 5:
        return None
    return digits[:5]


def _select_basicdata_row(
    basicdata: Any, zip_code: str | None = None
) -> dict[str, Any] | None:
    if isinstance(basicdata, dict):
        return basicdata
    if not isinstance(basicdata, list):
        return None

    rows = [row for row in basicdata if isinstance(row, dict)]
    if not rows:
        return None

    if zip_code:
        target_zip = _zip5(zip_code)
        if target_zip:
            for row in rows:
                row_zip = _zip5(
                    str(
                        _field_value(
                            row,
                            "zip",
                            "zip_code",
                            "zip-code",
                            "zipcode",
                            "ZIP Code",
                        )
                        or ""
                    )
                )
                if row_zip == target_zip:
                    return row

    for row in rows:
        marker = str(
            _field_value(
                row,
                "zip",
                "zip_code",
                "zip-code",
                "zipcode",
                "ZIP Code",
            )
            or ""
        ).strip()
        if marker.lower() == "msa level":
            return row

    return rows[0]


def _to_hud_entity_id(fips_code: str) -> str:
    stripped = fips_code.strip()
    digits = "".join(ch for ch in stripped if ch.isdigit())
    if len(digits) == 5:
        return f"{digits}99999"
    if len(digits) == 10:
        return digits
    return stripped


def get_rent_estimate(
    zip_code: str | None = None,
    fips_code: str | None = None,
    bedrooms: int = 2,
) -> Decimal | None:
    """Get a rent estimate for a location from HUD FMR data.

    Resolves the county entity id from ``fips_code``; Small Area FMR markets
    return the row for ``zip_code``, others the county/metro row.  Without a
    ``fips_code`` there is no entity id, so it returns ``None``.  New England
    county-subdivision entity ids are not supported.  Requires a
    ``HUD_API_KEY`` environment variable or Django setting.

    Args:
        zip_code: 5-digit ZIP code (preferred for Small Area FMRs).
        fips_code: County FIPS code (fallback).
        bedrooms: Number of bedrooms (0-4, default 2).

    Returns:
        Monthly rent estimate as Decimal, or ``None`` if unavailable.
    """
    client = FMRClient()
    if not client.api_key:
        logger.warning("HUD_API_KEY not configured — cannot fetch rent estimates")
        return None

    bed_key = {
        0: "efficiency",
        1: "one_bedroom",
        2: "two_bedroom",
        3: "three_bedroom",
        4: "four_bedroom",
    }
    key = bed_key.get(bedrooms, "two_bedroom")

    if fips_code:
        entity_id = _to_hud_entity_id(fips_code)
        data = client.get_county_data(entity_id, year=FMR_YEAR, zip_code=zip_code)
        if data and data.get(key) is not None:
            return cast(Decimal | None, data[key])

    return None
