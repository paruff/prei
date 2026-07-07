"""BLS API adapter for state-level unemployment and employment data.

Fetches current unemployment rates and employment growth from the
Bureau of Labor Statistics. Free registration required for API key access.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

import requests

logger = logging.getLogger(__name__)

BLS_API_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# State FIPS codes (2-digit) for BLS state-level series IDs
# BLS LAUS series format: LAUST{SS}000000000X
# Where SS = 2-digit state FIPS (e.g., "06" for California)
# Measure codes: 0000000003 = unemployment rate, 0000000005 = employment level
# NOTE: The prior code incorrectly used 5-digit county FIPS codes ("06001" for CA)
# instead of 2-digit state FIPS codes ("06" for CA). This has been corrected.
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
    # Series format: LAUST{SS}0000000000003
    # Where SS = 2-digit state FIPS, and the 13-digit suffix encodes
    # the measure type (0000000000003 = unemployment rate).
    fips = STATE_FIPS[state_code]
    series_id = f"LAUST{fips}0000000000003"

    return _fetch_bls_value(series_id, api_key, state_code)


def fetch_employment_growth(
    state_code: str, api_key: str, years_back: int = 5
) -> Decimal | None:
    """Fetch employment growth rate for a state over the specified period.

    Uses BLS LAUS employment level data (measure code 0000000005) to compute
    percentage growth between two time points.

    Args:
        state_code: 2-letter US state code (e.g. "VA").
        api_key: BLS API key (free registration at bls.gov).
        years_back: Number of years to look back for comparison (default 5).

    Returns:
        Decimal representing employment growth rate as fraction
        (e.g. 0.0234 = 2.34% growth). Returns None on error or missing data.
    """
    if not api_key:
        logger.warning("BLS API key not provided for employment growth")
        return None

    state_code = state_code.strip().upper()
    if state_code not in STATE_FIPS:
        logger.error("Invalid state code for BLS employment: %s", state_code)
        return None

    fips = STATE_FIPS[state_code]
    # Employment level measure code = 0000000000005
    # Series format: LAUST{SS}0000000000005
    # Where SS = 2-digit state FIPS and the 13-digit suffix encodes
    # the measure type (0000000000005 = employment level).
    series_id = f"LAUST{fips}0000000000005"

    # Calculate year range
    from datetime import datetime

    current_year = datetime.now().year
    start_year = str(current_year - years_back)
    end_year = str(current_year)

    headers = {"Content-Type": "application/json"}
    payload = {
        "seriesid": [series_id],
        "startyear": start_year,
        "endyear": end_year,
    }
    # BLS API v2 uses "registrationkey" (not "key") for authentication.
    # Pass it in the POST body as the API docs require.
    params = {"registrationkey": api_key}

    try:
        resp = requests.post(
            BLS_API_BASE,
            json=payload,
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error(
            "BLS employment API request failed for state=%s: %s", state_code, exc
        )
        return None

    try:
        data = resp.json()
    except (ValueError, TypeError) as exc:
        logger.error(
            "BLS employment API returned invalid JSON for state=%s: %s", state_code, exc
        )
        return None

    # BLS API v2 returns HTTP 200 even for errors; check status field
    status = data.get("status")
    if status and status != "REQUEST_SUCCEEDED":
        logger.warning(
            "BLS employment API error for state=%s: status=%s message=%s",
            state_code,
            status,
            data.get("message", "Unknown"),
        )
        return None

    results = data.get("Results", {})
    series_list = results.get("series", [])

    if not series_list:
        logger.warning("BLS employment API returned no series for state=%s", state_code)
        return None

    series_data = series_list[0].get("data", [])
    if not series_data:
        logger.warning(
            "BLS employment API returned empty data for state=%s", state_code
        )
        return None

    # Find the earliest and latest data points
    # Data is typically sorted by year/period descending
    values_by_year: dict[str, int] = {}
    for item in series_data:
        year = item.get("year")
        period = item.get("period")  # e.g., "M01" for January
        value = item.get("value")
        if year and period and value and value not in ("null", "-1", ""):
            # Use annual average (M13) or first available month
            if period == "M13":
                values_by_year[year] = int(value)
            elif year not in values_by_year:
                values_by_year[year] = int(value)

    if len(values_by_year) < 2:
        logger.warning("Insufficient employment data points for state=%s", state_code)
        return None

    # Get earliest and latest years available
    years = sorted(values_by_year.keys())
    earliest_year = years[0]
    latest_year = years[-1]

    earliest_emp = values_by_year[earliest_year]
    latest_emp = values_by_year[latest_year]

    if earliest_emp <= 0:
        logger.warning("Earliest employment is zero/negative for state=%s", state_code)
        return None

    try:
        growth = (Decimal(latest_emp) - Decimal(earliest_emp)) / Decimal(earliest_emp)
        return growth.quantize(Decimal("0.0001"))
    except (InvalidOperation, ValueError, TypeError, ZeroDivisionError) as exc:
        logger.error(
            "Employment growth calculation error for state=%s: %s", state_code, exc
        )
        return None


def _fetch_bls_value(series_id: str, api_key: str, state_code: str) -> Decimal | None:
    """Internal helper to fetch a single BLS series value.

    Args:
        series_id: Full BLS series ID.
        api_key: BLS API key.
        state_code: State code for logging.

    Returns:
        Decimal value as fraction (for rates) or raw value, or None on error.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "seriesid": [series_id],
        "startyear": "2023",
        "endyear": "2024",
    }
    # BLS API v2 uses "registrationkey" (not "key") for authentication.
    params = {"registrationkey": api_key}

    try:
        resp = requests.post(
            BLS_API_BASE,
            json=payload,
            headers=headers,
            params=params,
            timeout=15,
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

    # BLS API v2 returns HTTP 200 even for errors; check status field
    status = data.get("status")
    if status and status != "REQUEST_SUCCEEDED":
        logger.warning(
            "BLS API error for state=%s: status=%s message=%s",
            state_code,
            status,
            data.get("message", "Unknown"),
        )
        return None

    results = data.get("Results", {})
    series_list = results.get("series", [])

    if not series_list:
        logger.warning("BLS API returned no series data for state=%s", state_code)
        return None

    series_data = series_list[0].get("data", [])
    if not series_data:
        logger.warning("BLS API returned empty data for state=%s", state_code)
        return None

    latest = series_data[0]
    raw_value = latest.get("value")

    if raw_value is None or raw_value in ("null", "-1", ""):
        logger.warning("BLS API returned null value for state=%s", state_code)
        return None

    try:
        percentage = Decimal(raw_value)
        return percentage / Decimal("100")
    except (InvalidOperation, ValueError, TypeError) as exc:
        logger.error("BLS API parse error for state=%s: %s", state_code, exc)
        return None
