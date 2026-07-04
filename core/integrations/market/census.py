"""Census API adapter for ZIP-level and place-level demographic data.

Fetches population, population growth, and median household income
from the U.S. Census Bureau API. Free registration required.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

logger = logging.getLogger(__name__)

CENSUS_API_BASE = "https://api.census.gov/data"
# American Community Survey 5-Year (most recent available)
ACS_VINTAGE = "2022"
ACS_DATASET = "acs/acs5"
# 5-year prior vintage for growth calculation
ACS_VINTAGE_PRIOR = "2017"

# State FIPS codes for Census "place" geography
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


def fetch_zip_demographics(zip_code: str, api_key: str) -> dict | None:
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


def _fetch_acs_data(
    vintage: str,
    variables: str,
    geography: str,
    api_key: str,
    state_fips: str | None = None,
) -> dict[str, Any] | None:
    """Internal helper to fetch ACS data for a given vintage and geography.

    Args:
        vintage: ACS vintage year (e.g., "2022", "2017")
        variables: Comma-separated Census variable codes
        geography: Census geography string (e.g., "place:12345", "metropolitan statistical area/micropolitan statistical area:12345")
        api_key: Census API key
        state_fips: State FIPS code for "place" geography (required for place)

    Returns:
        Parsed JSON response or None on error
    """
    if not api_key:
        logger.warning("Census API key not provided")
        return None

    url = f"{CENSUS_API_BASE}/{vintage}/{ACS_DATASET}/get"

    params: dict[str, str] = {
        "get": variables,
        "for": geography,
        "key": api_key,
    }
    if state_fips:
        params["in"] = f"state:{state_fips}"

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Census API request failed for geography=%s: %s", geography, exc)
        return None

    try:
        data = resp.json()
    except (ValueError, TypeError) as exc:
        logger.error(
            "Census API returned invalid JSON for geography=%s: %s", geography, exc
        )
        return None

    if not isinstance(data, list) or len(data) < 2:
        logger.warning(
            "Census API returned unexpected structure for geography=%s", geography
        )
        return None

    return {"headers": data[0], "values": data[1]}


def _parse_acs_response(
    response: dict[str, Any],
    var_codes: list[str],
) -> dict[str, Any] | None:
    """Parse ACS response for specific variable codes.

    Args:
        response: Output from _fetch_acs_data
        var_codes: List of variable codes to extract (e.g., ["B01001_001E", "B19013_001E"])

    Returns:
        Dict mapping variable codes to parsed values, or None on error
    """
    headers = response["headers"]
    values = response["values"]

    result = {}
    for var in var_codes:
        try:
            idx = headers.index(var)
        except ValueError as exc:
            logger.error(
                "Census API response missing expected variable %s: %s", var, exc
            )
            return None

        raw = values[idx]
        if raw in ("null", "-1", ""):
            logger.warning("Census API returned null for variable %s", var)
            return None

        result[var] = raw

    return result


def _estimate_population_growth(
    zip_code: str, api_key: str, current_population: int
) -> Decimal | None:
    """Estimate 5-year population growth from ACS migration data.

    Uses B07001 (geographic mobility) as a proxy if available.
    Returns None if estimation is not possible.
    """
    # Try to get 5-year-ago population estimate from B01001 (not available in ACS)
    # For MVP, return None — growth data requires decennial census comparison
    return None


def fetch_place_growth_metrics(
    state_code: str,
    place_code: str,
    api_key: str,
    place_name: str = "",
) -> dict | None:
    """Fetch place-level (city) population and income growth from Census ACS.

    Compares two ACS vintages (current and 5 years prior) to compute growth rates.
    Used for populating the GrowthArea model (city/metro-level).

    Args:
        state: 2-letter state code (e.g., "CA")
        place_name: City name for logging (e.g., "Los Angeles")
        place_code: Census place FIPS code (e.g., "44000" for Los Angeles)
        api_key: Census API key (free registration at api.census.gov)

    Returns:
        dict with keys:
            - population (int): Current population
            - population_growth_rate (Decimal): 5-year growth rate as fraction (e.g., 0.0234)
            - median_household_income (Decimal): Current median household income
            - median_income_growth (Decimal): 5-year income growth rate as fraction
        Returns None on any error.
    """
    if not api_key:
        logger.warning("Census API key not provided")
        return None

    state_code = state_code.strip().upper()
    if state_code not in STATE_FIPS:
        logger.error("Invalid state code for Census place geography: %s", state_code)
        return None

    state_fips = STATE_FIPS[state_code]
    variables = "B01001_001E,B19013_001E"
    geography = f"place:{place_code}"

    # Fetch current vintage (2022)
    current_data = _fetch_acs_data(
        ACS_VINTAGE, variables, geography, api_key, state_fips
    )
    if not current_data:
        return None

    # Fetch prior vintage (2017) for 5-year comparison
    prior_data = _fetch_acs_data(
        ACS_VINTAGE_PRIOR, variables, geography, api_key, state_fips
    )
    if not prior_data:
        return None

    # Parse both responses
    current_parsed = _parse_acs_response(current_data, ["B01001_001E", "B19013_001E"])
    prior_parsed = _parse_acs_response(prior_data, ["B01001_001E", "B19013_001E"])
    if not current_parsed or not prior_parsed:
        return None

    try:
        current_pop = int(current_parsed["B01001_001E"])
        current_income = Decimal(current_parsed["B19013_001E"])
        prior_pop = int(prior_parsed["B01001_001E"])
        prior_income = Decimal(prior_parsed["B19013_001E"])
    except (InvalidOperation, ValueError, TypeError) as exc:
        logger.error("Census API parse error for place=%s: %s", place_code, exc)
        return None

    # Compute growth rates (handle zero prior values)
    if prior_pop == 0:
        logger.warning("Prior population is zero for place=%s", place_code)
        pop_growth = None
    else:
        pop_growth = (Decimal(current_pop) - Decimal(prior_pop)) / Decimal(prior_pop)

    if prior_income == 0:
        logger.warning("Prior income is zero for place=%s", place_code)
        income_growth = None
    else:
        income_growth = (current_income - prior_income) / prior_income

    return {
        "population_current": current_pop,
        "population_prior": prior_pop,
        "population_growth_rate": pop_growth.quantize(Decimal("0.01"))
        if pop_growth is not None
        else None,
        "median_income_current": current_income,
        "median_income_prior": prior_income,
        "median_income_growth_rate": income_growth.quantize(Decimal("0.01"))
        if income_growth is not None
        else None,
    }


def fetch_housing_demand_index(
    state_code: str,
    place_code: str,
    api_key: str,
    population_growth_rate: Decimal | None = None,
) -> int | None:
    """Fetch housing demand proxy index for a Census place (city).

    Uses ACS table B25002 (Occupancy Status) to compute vacancy rate,
    then combines with population growth to produce a demand index (0-100).

    This is a HEURISTIC, not an official index — label as such in any UI.

    Args:
        state_code: 2-letter US state code (e.g. "CA").
        place_code: Census place FIPS code (5 digits, e.g. "67000" for San Francisco).
        api_key: Census API key (free registration at api.census.gov).
        population_growth_rate: Optional population growth rate (fraction) from
            fetch_place_growth_metrics. If provided, used to weight the index.

    Returns:
        Integer demand index (0-100), or None on error.
    """
    if not api_key:
        logger.warning("Census API key not provided for housing demand")
        return None

    state_code = state_code.strip().upper()
    if state_code not in STATE_FIPS:
        logger.error("Invalid state code for housing demand: %s", state_code)
        return None

    state_fips = STATE_FIPS[state_code]

    # Fetch occupancy data (current vintage)
    # B25002_001E = total housing units
    # B25002_003E = vacant housing units
    variables = "B25002_001E,B25002_003E"
    geography = f"place:{place_code}"

    data = _fetch_acs_data(ACS_VINTAGE, variables, geography, api_key, state_fips)
    if not data:
        return None

    parsed = _parse_acs_response(data, ["B25002_001E", "B25002_003E"])
    if not parsed:
        return None

    try:
        total_units = int(parsed["B25002_001E"])
        vacant_units = int(parsed["B25002_003E"])
    except (ValueError, TypeError) as exc:
        logger.error("Housing demand parse error for place=%s: %s", place_code, exc)
        return None

    if total_units <= 0:
        logger.warning("Total housing units is zero for place=%s", place_code)
        return None

    # Compute vacancy rate
    vacancy_rate = Decimal(vacant_units) / Decimal(total_units)

    # Heuristic: lower vacancy + higher population growth = higher demand
    # Scale: (1 - vacancy_rate) * 100 gives 0-100 based on occupancy
    # Then adjust by population growth if available
    occupancy_score = (Decimal("1") - vacancy_rate) * Decimal("100")

    if population_growth_rate is not None and population_growth_rate > 0:
        # Boost score by up to 20 points for strong population growth
        # growth_rate of 0.1 (10%) adds ~10 points
        growth_bonus = min(population_growth_rate * Decimal("100"), Decimal("20"))
        occupancy_score += growth_bonus

    # Clamp to 0-100
    demand_index = max(0, min(100, int(occupancy_score.quantize(Decimal("1")))))
    return demand_index
