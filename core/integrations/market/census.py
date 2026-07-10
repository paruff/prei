"""Census API adapter for ZIP-level and place-level demographic data.

Fetches population, population growth, and median household income
from the U.S. Census Bureau API. Free registration required.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import requests

logger = logging.getLogger(__name__)

CENSUS_API_BASE = "https://api.census.gov/data"
ACS_DATASET = "acs/acs5"

# ---------------------------------------------------------------------------
# GA-5: Auto-detected ACS vintages
# ---------------------------------------------------------------------------
# These are populated lazily by _auto_detect_acs_vintages().  The module-level
# constants below are the *fallback* defaults used when the Census data.json
# API is unreachable.  Most callers should use get_acs_vintages() instead of
# reading ACS_VINTAGE / ACS_VINTAGE_PRIOR directly – it returns the
# auto-detected vintages (cached after the first call).
#
# Fallback defaults (updated July 2026):
_ACS_VINTAGE_FALLBACK: str = "2024"
_ACS_VINTAGE_PRIOR_FALLBACK: str = "2019"

# Module-level cache for auto-detected vintages (populated once).
# The _auto_detect_acs_vintages() function caches its result here so that
# subsequent calls in the same process avoid a redundant HTTP request.
_acs_vintage_cache: dict[str, str] | None = None


def get_acs_vintages() -> tuple[str, str]:
    """Return (current_vintage, prior_vintage) for ACS 5-year comparisons.

    Auto-detects the latest available ACS 5-Year Detailed Tables vintage
    from the Census data.json API on first call, then caches the result.
    Falls back to hardcoded defaults if the API is unreachable or the
    response cannot be parsed.

    Returns:
        Tuple of (current_vintage, prior_vintage) as strings.
    """
    global _acs_vintage_cache
    if _acs_vintage_cache is not None:
        c = _acs_vintage_cache
        return c["current"], c["prior"]

    try:
        result = _fetch_latest_acs_vintages()
        if result is not None:
            _acs_vintage_cache = result
            v = result
            logger.info(
                "Auto-detected ACS vintages: current=%s, prior=%s",
                v["current"],
                v["prior"],
            )
            return v["current"], v["prior"]
    except Exception:
        logger.exception("Failed to auto-detect ACS vintages; using fallback defaults")

    # Fallback
    _acs_vintage_cache = {
        "current": _ACS_VINTAGE_FALLBACK,
        "prior": _ACS_VINTAGE_PRIOR_FALLBACK,
    }
    return _ACS_VINTAGE_FALLBACK, _ACS_VINTAGE_PRIOR_FALLBACK


def _fetch_latest_acs_vintages() -> dict[str, str] | None:
    """Query Census /data.json for the latest ACS 5-Year Detailed Tables vintage.

    Returns:
        dict with keys "current" and "prior", or None on failure.
    """
    url = f"{CENSUS_API_BASE}/data.json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        catalog = resp.json()
    except requests.RequestException as exc:
        logger.warning("Census /data.json request failed [15s timeout]: %s", exc)
        return None
    except (ValueError, TypeError) as exc:
        logger.warning("Census /data.json parse error: %s", exc)
        return None

    datasets = catalog.get("dataset", []) if isinstance(catalog, dict) else []
    if not datasets:
        logger.warning("Census /data.json has no datasets")
        return None

    # Find all ACS 5-Year Detailed Tables vintages.
    # The identifier field uses opaque IDs (e.g. https://api.census.gov/data/id/ACSDP1Y2010),
    # so we match on distribution[0].accessURL which contains the actual API path
    # (e.g. http://api.census.gov/data/2024/acs/acs5).
    # Filter: accessURL contains "/acs/acs5" AND title includes "Detailed Tables".
    acs_vintages: set[int] = set()
    for ds in datasets:
        title = ds.get("title", "")
        vintage_str = ds.get("c_vintage", "")
        dist = ds.get("distribution", [{}])
        access_url = (
            dist[0].get("accessURL", "") if isinstance(dist, list) and dist else ""
        )

        # Match ACS 5-Year Detailed Tables (not PUMS, not profiles)
        if "/acs/acs5" not in access_url.lower():
            continue
        if "detailed table" not in title.lower():
            continue
        if not vintage_str:
            continue

        try:
            v = int(vintage_str)
        except ValueError, TypeError:
            continue
        acs_vintages.add(v)

    if not acs_vintages:
        logger.warning("No ACS 5-Year Detailed Tables vintages found in /data.json")
        return None

    latest = max(acs_vintages)
    # Find the prior vintage: nearest to (latest - 5) that exists
    # ACS 5-year releases skip some years (e.g., 2018 is not published).
    target_prior = latest - 5
    # Walk up to 3 years forward/backward from the target
    candidates = [y for y in acs_vintages if target_prior - 2 <= y <= target_prior + 2]
    prior = max(candidates) if candidates else (latest - 5)

    return {
        "current": str(latest),
        "prior": str(prior),
    }


# For backwards compatibility – code that reads the module constant directly
# will still work, but new code should call get_acs_vintages().
# These are updated to sensible defaults as of July 2026 and will be
# overridden at runtime by auto-detection when get_acs_vintages() is called.
ACS_VINTAGE: str = _ACS_VINTAGE_FALLBACK
ACS_VINTAGE_PRIOR: str = _ACS_VINTAGE_PRIOR_FALLBACK

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

    current_vintage, _ = get_acs_vintages()
    # NOTE: The Census API changed in 2024. The old /get suffix path is deprecated.
    url = f"{CENSUS_API_BASE}/{current_vintage}/{ACS_DATASET}"

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

    # NOTE: The Census API changed in 2024. The old /get suffix path is deprecated.
    # Parameters are now passed directly in the query string without /get.
    url = f"{CENSUS_API_BASE}/{vintage}/{ACS_DATASET}"

    params: dict[str, str] = {
        "get": variables,
        "for": geography,
        "key": api_key,
    }
    if state_fips:
        params["in"] = f"state:{state_fips}"

    # Retry up to 2 times on transient 503 / timeout errors (Census API is flaky)
    import time

    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            backoff = 2**attempt  # 2s, 4s
            logger.info(
                "Retrying Census API request (attempt %d/%d) after %ds",
                attempt + 1,
                3,
                backoff,
            )
            time.sleep(backoff)
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            last_exc = None
            break
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Census API request failed (attempt %d/3) for geography=%s [%ds timeout]: %s",
                attempt + 1,
                geography,
                15,
                exc,
            )
            continue

    if last_exc is not None:
        logger.error(
            "Census API request failed after 3 attempts for geography=%s [%ds timeout]: %s",
            geography,
            15,
            last_exc,
        )
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
    optional_vars: list[str] | None = None,
) -> dict[str, Any] | None:
    """Parse ACS response for specific variable codes.

    Args:
        response: Output from _fetch_acs_data
        var_codes: List of variable codes to extract (e.g., ["B01001_001E", "B19013_001E"])
        optional_vars: List of variable codes that are optional (won't fail if missing)

    Returns:
        Dict mapping variable codes to parsed values, or None on error
    """
    headers = response["headers"]
    values = response["values"]

    if optional_vars is None:
        optional_vars = []

    result = {}
    for var in var_codes:
        try:
            idx = headers.index(var)
        except ValueError as exc:
            if var in optional_vars:
                logger.warning("Census API response missing optional variable %s", var)
                continue
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
    current_vintage, prior_vintage = get_acs_vintages()
    variables = "B01001_001E,B19013_001E,B25001_001E"
    geography = f"place:{place_code}"

    # Fetch current vintage
    current_data = _fetch_acs_data(
        current_vintage, variables, geography, api_key, state_fips
    )
    if not current_data:
        return None

    # Fetch prior vintage for comparison
    prior_data = _fetch_acs_data(
        prior_vintage, variables, geography, api_key, state_fips
    )
    if not prior_data:
        return None

    # Parse both responses
    current_parsed = _parse_acs_response(
        current_data,
        ["B01001_001E", "B19013_001E", "B25001_001E"],
        optional_vars=["B25001_001E"],
    )
    prior_parsed = _parse_acs_response(
        prior_data,
        ["B01001_001E", "B19013_001E", "B25001_001E"],
        optional_vars=["B25001_001E"],
    )
    if not current_parsed or not prior_parsed:
        return None

    try:
        current_pop = int(current_parsed["B01001_001E"])
        current_income = Decimal(current_parsed["B19013_001E"])
        current_units = int(current_parsed.get("B25001_001E", 0) or 0)
        prior_pop = int(prior_parsed["B01001_001E"])
        prior_income = Decimal(prior_parsed["B19013_001E"])
        prior_units = int(prior_parsed.get("B25001_001E", 0) or 0)
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

    if prior_units == 0:
        logger.warning("Prior housing units is zero for place=%s", place_code)
        units_growth = None
    else:
        units_growth = (Decimal(current_units) - Decimal(prior_units)) / Decimal(
            prior_units
        )

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
        "housing_units_current": current_units,
        "housing_units_prior": prior_units,
        "housing_units_growth_rate": units_growth.quantize(Decimal("0.01"))
        if units_growth is not None
        else None,
    }


def discover_places_in_state(
    state_code: str,
    api_key: str,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Discover the top N places in a state by population via the Census ACS API.

    Uses the Census "place" geography with a wildcard query to fetch population
    for ALL places in a given state in a single API call. Results are sorted by
    population descending and the top ``limit`` are returned.

    Census place geography supports wildcard via::

        for=place:*
        in=state:<state_fips>

    This is confirmed against live api.census.gov documentation — the place
    geography entry in /data/2022/acs/acs5/geography.json has:
        "requires": ["state"],
        "wildcard": ["state"],
        "optionalWithWCFor": "state"

    Note on employment_growth_rate:
        The employment growth rate returned by bls.fetch_employment_growth() is
        a STATE-level figure, not place-level. Every place discovered by this
        function will share the same employment growth figure when GrowthArea
        rows are built from them.

    Args:
        state_code: 2-letter US state code (e.g. "CA").
        api_key: Census API key (free registration at api.census.gov).
        limit: Maximum number of places to return, sorted by population desc.

    Returns:
        List of dicts with keys:
            - place_code (str): Census place FIPS code (e.g. "44000").
            - place_name (str): Place name without state suffix (e.g. "Los Angeles").
            - population (int): Total population from B01001_001E.
        Empty list on any error.
    """
    if not api_key:
        logger.warning("Census API key not provided")
        return []

    state_code = state_code.strip().upper()
    if state_code not in STATE_FIPS:
        logger.error("Invalid state code for place discovery: %s", state_code)
        return []

    state_fips = STATE_FIPS[state_code]
    current_vintage, _ = get_acs_vintages()
    variables = "B01001_001E,NAME"

    url = f"{CENSUS_API_BASE}/{current_vintage}/{ACS_DATASET}"
    params: dict[str, str] = {
        "get": variables,
        "for": "place:*",
        "in": f"state:{state_fips}",
        "key": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error(
            "Census API request failed for places in state=%s [15s timeout]: %s",
            state_code,
            exc,
        )
        return []

    try:
        data = resp.json()
    except (ValueError, TypeError) as exc:
        logger.error(
            "Census API returned invalid JSON for places in state=%s: %s",
            state_code,
            exc,
        )
        return []

    if not isinstance(data, list) or len(data) < 2:
        logger.warning(
            "Census API returned unexpected structure for places in state=%s",
            state_code,
        )
        return []

    headers = data[0]
    try:
        pop_idx = headers.index("B01001_001E")
        name_idx = headers.index("NAME")
        place_idx = headers.index("place")
    except ValueError as exc:
        logger.error(
            "Census API response missing expected column for state=%s: %s",
            state_code,
            exc,
        )
        return []

    places: list[dict[str, object]] = []
    for row in data[1:]:
        raw_pop = row[pop_idx]
        raw_name = row[name_idx]
        raw_place = row[place_idx]

        # Census returns "-1" or "null" for suppressed/missing data
        if raw_pop in ("null", "-1", ""):
            continue

        try:
            population = int(raw_pop)
        except ValueError, TypeError:
            continue

        # NAME format: "Los Angeles city, California" — extract place name only
        place_name = raw_name.split(",")[0].strip() if raw_name else ""

        places.append(
            {
                "place_code": raw_place,
                "place_name": place_name,
                "population": population,
            }
        )

    # Sort by population descending and return top `limit`
    places.sort(key=lambda p: cast(int, p["population"]), reverse=True)
    return places[:limit]


def compute_supply_constraint_index(
    population_growth_rate: Decimal | None,
    housing_units_growth_rate: Decimal | None,
) -> int | None:
    """Compute a supply constraint heuristic index (0-100).

    A high score means population is growing faster than housing units,
    indicating supply tightness — positive for existing property owners.
    A low score means housing supply is growing faster than population.

    Formula:
        diff = population_growth_rate - housing_units_growth_rate
        index = max(0, min(100, round(diff * 500 + 50)))

    This centres at 50 (neutral), with each percentage point of gap
    adding/subtracting ~5 points.

    Args:
        population_growth_rate: Fractional growth rate (e.g. 0.05 = 5%).
        housing_units_growth_rate: Fractional growth rate for housing units.

    Returns:
        Integer index 0-100, or None if either input is None.
    """
    if population_growth_rate is None or housing_units_growth_rate is None:
        return None

    diff = population_growth_rate - housing_units_growth_rate
    raw = diff * Decimal("500") + Decimal("50")
    clamped = max(Decimal("0"), min(Decimal("100"), raw))
    return int(clamped.quantize(Decimal("1")))


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
    current_vintage, _ = get_acs_vintages()

    # Fetch occupancy data (current vintage)
    # B25002_001E = total housing units
    # B25002_003E = vacant housing units
    variables = "B25002_001E,B25002_003E"
    geography = f"place:{place_code}"

    data = _fetch_acs_data(current_vintage, variables, geography, api_key, state_fips)
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
