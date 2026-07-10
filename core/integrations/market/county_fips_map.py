"""County FIPS code lookup for US cities.

Each entry maps (state_code, city_name) to a 5-character county FIPS code
(state FIPS + county FIPS).  Used by BLS QCEW county-level employment lookup.

Sources: Census Bureau county FIPS codes, ACS place-to-county crosswalk.
"""

CITY_COUNTY_FIPS: dict[tuple[str, str], str] = {
    # ── California ─────────────────────────────────────────────────
    ("CA", "San Francisco"): "06075",  # San Francisco County
    ("CA", "Los Angeles"): "06037",  # Los Angeles County
    ("CA", "San Diego"): "06073",  # San Diego County
    ("CA", "San Jose"): "06085",  # Santa Clara County
    ("CA", "Sacramento"): "06067",  # Sacramento County
    ("CA", "Oakland"): "06001",  # Alameda County
    ("CA", "Fresno"): "06019",  # Fresno County
    ("CA", "Long Beach"): "06037",  # Los Angeles County
    # ── Texas ──────────────────────────────────────────────────────
    ("TX", "Houston"): "48201",  # Harris County
    ("TX", "San Antonio"): "48029",  # Bexar County
    ("TX", "Dallas"): "48113",  # Dallas County
    ("TX", "Austin"): "48453",  # Travis County
    ("TX", "Fort Worth"): "48439",  # Tarrant County
    # ── New York ───────────────────────────────────────────────────
    ("NY", "New York"): "36061",  # New York County (Manhattan)
    ("NY", "Buffalo"): "36029",  # Erie County
    # ── Florida ────────────────────────────────────────────────────
    ("FL", "Miami"): "12086",  # Miami-Dade County
    ("FL", "Tampa"): "12057",  # Hillsborough County
    ("FL", "Orlando"): "12095",  # Orange County
    ("FL", "Jacksonville"): "12031",  # Duval County
    # ── Illinois ───────────────────────────────────────────────────
    ("IL", "Chicago"): "17031",  # Cook County
    # ── Pennsylvania ───────────────────────────────────────────────
    ("PA", "Philadelphia"): "42101",  # Philadelphia County
    ("PA", "Pittsburgh"): "42003",  # Allegheny County
    # ── Ohio ───────────────────────────────────────────────────────
    ("OH", "Columbus"): "39049",  # Franklin County
    ("OH", "Cleveland"): "39035",  # Cuyahoga County
    ("OH", "Cincinnati"): "39061",  # Hamilton County
    # ── Georgia ────────────────────────────────────────────────────
    ("GA", "Atlanta"): "13121",  # Fulton County
    # ── North Carolina ─────────────────────────────────────────────
    ("NC", "Charlotte"): "37119",  # Mecklenburg County
    ("NC", "Raleigh"): "37183",  # Wake County
    # ── Michigan ───────────────────────────────────────────────────
    ("MI", "Detroit"): "26163",  # Wayne County
    # ── Washington ─────────────────────────────────────────────────
    ("WA", "Seattle"): "53033",  # King County
    # ── Arizona ────────────────────────────────────────────────────
    ("AZ", "Phoenix"): "04013",  # Maricopa County
    # ── Massachusetts ──────────────────────────────────────────────
    ("MA", "Boston"): "25025",  # Suffolk County
    # ── Colorado ───────────────────────────────────────────────────
    ("CO", "Denver"): "08031",  # Denver County
    # ── Tennessee ──────────────────────────────────────────────────
    ("TN", "Nashville"): "47037",  # Davidson County
    ("TN", "Memphis"): "47157",  # Shelby County
    # ── Missouri ───────────────────────────────────────────────────
    ("MO", "Kansas City"): "29095",  # Jackson County
    ("MO", "St. Louis"): "29510",  # St. Louis city
    # ── Indiana ────────────────────────────────────────────────────
    ("IN", "Indianapolis"): "18097",  # Marion County
    # ── Nevada ─────────────────────────────────────────────────────
    ("NV", "Las Vegas"): "32003",  # Clark County
    # ── District of Columbia ───────────────────────────────────────
    ("DC", "Washington"): "11001",  # District of Columbia
    # ── Oregon ─────────────────────────────────────────────────────
    ("OR", "Portland"): "41051",  # Multnomah County
}


def lookup_county_fips(state_code: str, city_name: str) -> str | None:
    """Look up county FIPS code for a state/city pair.

    Args:
        state_code: 2-letter state code (e.g., "TX").
        city_name: City name (e.g., "Dallas").

    Returns:
        5-character county FIPS code, or None if not found.
    """
    return CITY_COUNTY_FIPS.get((state_code.strip().upper(), city_name.strip().title()))
