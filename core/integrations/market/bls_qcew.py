"""BLS Quarterly Census of Employment and Wages (QCEW) — county-level employment.

QCEW provides county-level employment and wage data by industry sector.
This replaces the state-level FRED data currently used in GACS with
actual county-level job counts.

Series ID format: ENU{SS}{CCC}XXXXX
  SS  = 2-digit state FIPS
  CCC = 3-digit county FIPS
  XXXXX = industry code (00000 = total, 10260 = construction, etc.)

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


def fetch_county_employment_growth(
    state_code: str,
    county_fips_3: str,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Fetch county-level total employment growth from BLS QCEW.

    Gets current and year-prior annual employment levels and computes
    the growth rate. This replaces the state-level FRED data in GACS.

    Args:
        state_code: 2-letter state code (e.g., "TX").
        county_fips_3: 3-digit county FIPS (e.g., "113" for Dallas).
        api_key: BLS API key. Falls back to BLS_API_KEY setting.

    Returns:
        Dict with keys: ``growth_rate`` (Decimal fraction), ``current_level`` (int),
        ``prior_level`` (int), ``year`` (str). Or None on failure.
    """
    from django.conf import settings

    key = api_key or getattr(settings, "BLS_API_KEY", "")
    if not key:
        logger.warning("BLS_API_KEY not configured")
        return None

    state_fips = STATE_FIPS.get(state_code.upper())
    if not state_fips:
        logger.warning("Unknown state code: %s", state_code)
        return None

    # QCEW total employment series: ENU{SS}{CCC}00000
    series_id = f"ENU{state_fips}{county_fips_3}00000"

    payload: dict[str, Any] = {
        "seriesid": [series_id],
        "startyear": "2024",
        "endyear": "2026",
        "registrationkey": key,
    }

    try:
        resp = requests.post(BLS_API_BASE, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("BLS QCEW request failed: %s", exc)
        return None

    if data.get("status") == "REQUEST_FAILED":
        logger.warning("BLS QCEW error: %s", data.get("message", "unknown"))
        return None

    series = (data.get("Results", {}) or {}).get("series", [])
    if not series:
        return None

    observations = series[0].get("data", [])
    if not observations:
        return None

    # Observations are sorted newest-first. Get the two most recent annual
    # values (period "Annual" or "2025" format)
    annual_obs = [o for o in observations if o.get("period") == "0"]
    if len(annual_obs) < 2:
        annual_obs = sorted(observations, key=lambda o: o.get("year", ""), reverse=True)
        if len(annual_obs) < 2:
            return None

    try:
        current = int(annual_obs[0]["value"])
        prior = int(annual_obs[1]["value"])
    except ValueError, TypeError, KeyError:
        return None

    if prior == 0:
        return None

    growth_rate = (Decimal(current) - Decimal(prior)) / Decimal(prior)

    return {
        "growth_rate": growth_rate.quantize(Decimal("0.0001")),
        "current_level": current,
        "prior_level": prior,
        "current_year": annual_obs[0].get("year", ""),
        "prior_year": annual_obs[1].get("year", ""),
    }
