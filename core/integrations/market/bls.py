"""BLS API adapter for state-level unemployment data.

Fetches current unemployment rates from the Bureau of Labor Statistics.
Free registration required for API key access.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

import requests

logger = logging.getLogger(__name__)

BLS_API_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# State FIPS codes to BLS series ID prefixes
# BLS series format: LAUCN{FIPS}0000000003 (0000000003 = unemployment rate)
STATE_FIPS = {
    "AL": "01001",
    "AK": "02001",
    "AZ": "04001",
    "AR": "05001",
    "CA": "06001",
    "CO": "08001",
    "CT": "09001",
    "DE": "10001",
    "DC": "11001",
    "FL": "12001",
    "GA": "13001",
    "HI": "15001",
    "ID": "16001",
    "IL": "17001",
    "IN": "18001",
    "IA": "19001",
    "KS": "20001",
    "KY": "21001",
    "LA": "22001",
    "ME": "23001",
    "MD": "24001",
    "MA": "25001",
    "MI": "26001",
    "MN": "27001",
    "MS": "28001",
    "MO": "29001",
    "MT": "30001",
    "NE": "31001",
    "NV": "32001",
    "NH": "33001",
    "NJ": "34001",
    "NM": "35001",
    "NY": "36001",
    "NC": "37001",
    "ND": "38001",
    "OH": "39001",
    "OK": "40001",
    "OR": "41001",
    "PA": "42001",
    "RI": "44001",
    "SC": "45001",
    "SD": "46001",
    "TN": "47001",
    "TX": "48001",
    "UT": "49001",
    "VT": "50001",
    "VA": "51001",
    "WA": "53001",
    "WV": "54001",
    "WI": "55001",
    "WY": "56001",
}


def fetch_unemployment_rate(state_code: str, api_key: str) -> Decimal | None:
    """Fetch current unemployment rate for a state from the BLS API.

    Args:
        state_code: 2-letter US state code (e.g. "VA").
        api_key: BLS API key (free registration at bls.gov).

    Returns:
        Decimal representing unemployment rate as fraction (e.g. 0.045 = 4.5%).
        Returns None on any error.
    """
    if not api_key:
        logger.warning("BLS API key not provided")
        return None

    state_code = state_code.strip().upper()
    if state_code not in STATE_FIPS:
        logger.error("Invalid state code for BLS: %s", state_code)
        return None

    # Use statewide seasonally adjusted unemployment rate
    # Series format: LAUST{FIPS}0000000003 (SA = seasonally adjusted)
    fips = STATE_FIPS[state_code]
    series_id = f"LAUST{fips}0000000003"

    headers = {"Content-Type": "application/json"}
    payload = {
        "seriesid": [series_id],
        "startyear": "2023",
        "endyear": "2024",
    }

    # BLS registration key is passed as query parameter
    params = {"key": api_key}

    try:
        resp = requests.post(
            BLS_API_BASE,
            json=payload,
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("BLS API request failed for state=%s: %s", state_code, exc)
        return None

    try:
        data = resp.json()
    except (ValueError, TypeError) as exc:
        logger.error("BLS API returned invalid JSON for state=%s: %s", state_code, exc)
        return None

    # BLS response structure: {"Results": {"series": [{"seriesId": ..., "data": [...]}]}}
    results = data.get("Results", {})
    series_list = results.get("series", [])

    if not series_list:
        logger.warning("BLS API returned no series data for state=%s", state_code)
        return None

    series_data = series_list[0].get("data", [])
    if not series_data:
        logger.warning("BLS API returned empty data for state=%s", state_code)
        return None

    # Get the most recent period's value
    # Data is sorted by year/period descending
    latest = series_data[0]
    raw_value = latest.get("value")

    if raw_value is None or raw_value in ("null", "-1", ""):
        logger.warning("BLS API returned null value for state=%s", state_code)
        return None

    try:
        # BLS returns percentage as string (e.g. "4.5"), convert to fraction
        percentage = Decimal(raw_value)
        return percentage / Decimal("100")
    except (InvalidOperation, ValueError, TypeError) as exc:
        logger.error("BLS API parse error for state=%s: %s", state_code, exc)
        return None
