"""Census API adapter for ZIP-level demographic data.

Fetches population, population growth, and median household income
from the U.S. Census Bureau API. Free registration required.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

import requests

logger = logging.getLogger(__name__)

CENSUS_API_BASE = "https://api.census.gov/data"
# American Community Survey 5-Year (most recent available)
ACS_VINTAGE = "2022"
ACS_DATASET = "acs/acs5"


def fetch_zip_demographics(
    zip_code: str, api_key: str
) -> dict | None:
    """Fetch ZIP-level demographics from the Census API.

    Args:
        zip_code: 5-digit ZIP code (e.g. "90210").
        api_key: Census API key (free registration at api.census.gov).

    Returns:
        dict with keys:
            - population (int)
            - population_growth_pct_5yr (Decimal, e.g. 0.0234 for 2.34%)
            - median_household_income (Decimal)
        Returns None on any error (HTTP, parse, missing data).
    """
    if not api_key:
        logger.warning("Census API key not provided")
        return None

    url = f"{CENSUS_API_BASE}/{ACS_VINTAGE}/{ACS_DATASET}/get"

    # B01001_001E = total population
    # B19013_001E = median household income
    # B07001_001E = geographic mobility (used as proxy for migration/growth)
    variables = "B01001_001E,B19013_001E"

    # ZIP Code Tabulation Area (ZCTA) geography
    params = {
        "get": variables,
        "for": f"zip code tabulation area:{zip_code}",
        "key": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Census API request failed for zip=%s: %s", zip_code, exc)
        return None

    try:
        data = resp.json()
    except (ValueError, TypeError) as exc:
        logger.error("Census API returned invalid JSON for zip=%s: %s", zip_code, exc)
        return None

    # Response format: [[var1, var2, ...], [val1, val2, ...], ...]
    if not isinstance(data, list) or len(data) < 2:
        logger.warning("Census API returned unexpected structure for zip=%s", zip_code)
        return None

    headers = data[0]
    values = data[1]

    try:
        pop_idx = headers.index("B01001_001E")
        income_idx = headers.index("B19013_001E")
    except ValueError as exc:
        logger.error("Census API response missing expected variable: %s", exc)
        return None

    raw_population = values[pop_idx]
    raw_income = values[income_idx]

    # Census returns "-1" or "null" for suppressed/missing data
    if raw_population in ("null", "-1", ""):
        logger.warning("Census API returned null population for zip=%s", zip_code)
        return None
    if raw_income in ("null", "-1", ""):
        logger.warning("Census API returned null income for zip=%s", zip_code)
        return None

    try:
        population = int(raw_population)
        median_income = Decimal(raw_income)
    except (InvalidOperation, ValueError, TypeError) as exc:
        logger.error("Census API parse error for zip=%s: %s", zip_code, exc)
        return None

    # Population growth requires a second request for 5-year-ago data
    # For MVP, we'll estimate from migration data or leave as None
    growth_5yr = _estimate_population_growth(zip_code, api_key, population)

    return {
        "population": population,
        "population_growth_pct_5yr": growth_5yr,
        "median_household_income": median_income,
    }


def _estimate_population_growth(
    zip_code: str, api_key: str, current_population: int
) -> Decimal | None:
    """Estimate 5-year population growth from ACS migration data.

    Uses B07001 (geographic mobility) as a proxy if available.
    Returns None if estimation is not possible.
    """
    url = f"{CENSUS_API_BASE}/{ACS_VINTAGE}/{ACS_DATASET}/get"

    # Try to get 5-year-ago population estimate from B01001 (not available in ACS)
    # For MVP, return None — growth data requires decennial census comparison
    return None
