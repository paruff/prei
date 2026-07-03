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

# State FIPS codes for BLS series IDs
# BLS LAUS series format: LAUST{FIPS}000000000X
# Measure codes: 0000000003 = unemployment rate, 0000000005 = employment level
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
    # Employment level measure code = 0000000005
    series_id = f"LAUST{fips}0000000005"

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
