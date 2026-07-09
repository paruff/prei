"""BLS Local Area Unemployment Statistics (LAUS) — county-level.

Fetches county-level unemployment rates and employment levels from
the Bureau of Labor Statistics LAUS program.

BLS series ID format for county LAUS:
  LAUCN{SS}{CCC}0000000003  — unemployment rate (percent)
  LAUCN{SS}{CCC}0000000005  — employment level (jobs)
  LAUCN{SS}{CCC}0000000006  — labor force level
  LAUCN{SS}{CCC}0000000007  — unemployed level

Where SS = 2-digit state FIPS, CCC = 3-digit county FIPS.

API: https://www.bls.gov/developers/
Free API key at https://data.bls.gov/registrationEngine/
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import requests

logger = logging.getLogger(__name__)

BLS_API_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# State → 2-digit FIPS mapping (shared with bls.py)
STATE_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "DC": "11",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
    "PR": "72",
}


def fetch_county_unemployment(
    state_code: str,
    county_fips_3: str,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Fetch county-level unemployment rate from BLS LAUS.

    Args:
        state_code: 2-letter state code (e.g., "TX").
        county_fips_3: 3-digit county FIPS code (e.g., "113" for Dallas, TX).
        api_key: BLS API key. Falls back to BLS_API_KEY env/settings.

    Returns:
        Dict with ``rate`` (Decimal, percentage) and ``year`` (str),
        or ``None`` on failure.
    """
    from django.conf import settings

    key = api_key or getattr(settings, "BLS_API_KEY", "")

    state_fips = STATE_FIPS.get(state_code.upper())
    if not state_fips:
        logger.warning("Unknown state code: %s", state_code)
        return None

    series_id = f"LAUCN{state_fips}{county_fips_3}0000000003"

    payload: dict[str, Any] = {
        "seriesid": [series_id],
        "startyear": "2025",
        "endyear": "2026",
        "registrationkey": key,
    }

    try:
        resp = requests.post(BLS_API_BASE, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning(
            "BLS LAUS request failed for %s %s: %s", state_code, county_fips_3, exc
        )
        return None

    if data.get("status") == "REQUEST_FAILED":
        logger.warning("BLS LAUS error: %s", data.get("message", "unknown"))
        return None

    series = (data.get("Results", {}) or {}).get("series", [])
    if not series:
        return None

    observations = series[0].get("data", [])
    if not observations:
        return None

    # Most recent observation is first
    latest = observations[0]
    try:
        rate = Decimal(latest["value"])
    except (ValueError, TypeError, KeyError):
        return None

    return {
        "rate": rate,
        "year": latest.get("year", ""),
        "period": latest.get("periodName", ""),
    }


def fetch_county_employment(
    state_code: str,
    county_fips_3: str,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Fetch county-level employment level (number of jobs) from BLS LAUS.

    Args:
        state_code: 2-letter state code.
        county_fips_3: 3-digit county FIPS code.
        api_key: BLS API key.

    Returns:
        Dict with ``level`` (int) and ``year`` (str), or ``None``.
    """
    from django.conf import settings

    key = api_key or getattr(settings, "BLS_API_KEY", "")

    state_fips = STATE_FIPS.get(state_code.upper())
    if not state_fips:
        return None

    series_id = f"LAUCN{state_fips}{county_fips_3}0000000005"

    payload = {
        "seriesid": [series_id],
        "startyear": "2025",
        "endyear": "2026",
        "registrationkey": key,
    }

    try:
        resp = requests.post(BLS_API_BASE, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("BLS LAUS employment request failed: %s", exc)
        return None

    series = (data.get("Results", {}) or {}).get("series") or []
    if not series:
        return None

    observations = series[0].get("data", [])
    if not observations:
        return None

    latest = observations[0]
    try:
        level = int(latest["value"])
    except (ValueError, TypeError, KeyError):
        return None

    return {
        "level": level,
        "year": latest.get("year", ""),
        "period": latest.get("periodName", ""),
    }
