"""HUD Income Limits (IL) API adapter.

Fetches area median income and income limits by county/metro area.
Same API pattern as the FMR adapter — uses Bearer token auth.

Income Limits are calculated annually by HUD and represent:
  - Area Median Income (AMI) by family size
  - Low Income (80% of AMI), Very Low Income (50%), Extremely Low (30%)
  - Used to assess rental affordability and market strength
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, cast

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

IL_API_BASE = "https://www.huduser.gov/hudapi/public/il"
REQUEST_TIMEOUT = 30


class ILError(Exception):
    """Base exception for HUD Income Limits API errors."""


class ILClient:
    """Client for the HUD Income Limits API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or getattr(settings, "HUD_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """Make a GET request to the HUD IL API."""
        url = f"{IL_API_BASE}/{path.lstrip('/')}"
        resp = requests.get(
            url, headers=self._headers(), params=params, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 401:
            raise ILError("HUD API key is missing or invalid")
        if resp.status_code == 403:
            raise ILError(
                "HUD API key not authorized for Income Limits dataset. "
                "Go to https://www.huduser.gov/portal/dataset/fmr-api.html, "
                "ensure Income Limits is selected, and create a new token."
            )
        if resp.status_code == 404:
            raise ILError(f"No Income Limits data found: {path}")
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    def get_county_data(self, entity_id: str) -> dict[str, Any] | None:
        """Get Income Limits data for a county/metro area by entity ID."""
        try:
            data = self._get(f"data/{entity_id}")
        except ILError:
            return None

        result = data.get("data", {})
        if not result:
            return None

        return {
            "entity_id": entity_id,
            "median_income": _parse_il(result.get("median_family_income")),
            "very_low_income_1": _parse_il(result.get("very_low_income_1")),
            "very_low_income_4": _parse_il(result.get("very_low_income_4")),
            "low_income_4": _parse_il(result.get("low_income_4")),
            "year": result.get("year", ""),
        }

    def get_state_data(self, state_code: str) -> list[dict[str, Any]]:
        """Get Income Limits for all areas in a state."""
        data = self._get(f"statedata/{state_code}")
        result = data.get("data", {})
        return cast(
            list[dict[str, Any]],
            result.get("counties", []) + result.get("metroareas", []),
        )


def _parse_il(value: Any) -> Decimal | None:
    """Parse an Income Limits value to Decimal."""
    if value is None or value == "":
        return None
    try:
        return cast(Decimal, Decimal(str(value)))
    except Exception:
        return None


def fetch_area_median_income(entity_id: str) -> dict[str, Any] | None:
    """Fetch area median income for a county/metro area.

    Args:
        entity_id: HUD entity ID (FIPS code or metro code).

    Returns:
        Dict with median_income, very_low_income_1, very_low_income_4,
        low_income_4, year — or None if unavailable.
    """
    api_key = getattr(settings, "HUD_API_KEY", "")
    if not api_key:
        logger.info("HUD_API_KEY not set — skipping Income Limits fetch")
        return None

    client = ILClient(api_key=api_key)
    return client.get_county_data(entity_id)
