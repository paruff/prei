"""County FIPS code lookup for US cities.

Each entry maps (state_code, city_name) to a 5-character county FIPS code
(state FIPS + county FIPS).  Used by BLS QCEW county-level employment lookup.

Sources: Census Bureau county FIPS codes, ACS place-to-county crosswalk.
"""

CITY_COUNTY_FIPS: dict[tuple[str, str], str] = {
    # ── California ─────────────────────────────────────────────────
    ("CA", "San Francisco"): "06075",
    ("CA", "Los Angeles"): "06037",
    ("CA", "San Diego"): "06073",
    ("CA", "San Jose"): "06085",
    ("CA", "Sacramento"): "06067",
    ("CA", "Oakland"): "06001",
    ("CA", "Fresno"): "06019",
    ("CA", "Long Beach"): "06037",
    # ── Texas ──────────────────────────────────────────────────────
    ("TX", "Houston"): "48201",
    ("TX", "San Antonio"): "48029",
    ("TX", "Dallas"): "48113",
    ("TX", "Austin"): "48453",
    ("TX", "Fort Worth"): "48439",
    # ── New York ───────────────────────────────────────────────────
    ("NY", "New York"): "36061",
    ("NY", "Buffalo"): "36029",
    # ── Florida ────────────────────────────────────────────────────
    ("FL", "Miami"): "12086",
    ("FL", "Tampa"): "12057",
    ("FL", "Orlando"): "12095",
    ("FL", "Jacksonville"): "12031",
    # ── Illinois ───────────────────────────────────────────────────
    ("IL", "Chicago"): "17031",
    # ── Pennsylvania ───────────────────────────────────────────────
    ("PA", "Philadelphia"): "42101",
    ("PA", "Pittsburgh"): "42003",
    # ── Ohio ───────────────────────────────────────────────────────
    ("OH", "Columbus"): "39049",
    ("OH", "Cleveland"): "39035",
    ("OH", "Cincinnati"): "39061",
    # ── Georgia ────────────────────────────────────────────────────
    ("GA", "Atlanta"): "13121",
    # ── North Carolina ─────────────────────────────────────────────
    ("NC", "Charlotte"): "37119",
    ("NC", "Raleigh"): "37183",
    # ── Michigan ───────────────────────────────────────────────────
    ("MI", "Detroit"): "26163",
    # ── Washington ─────────────────────────────────────────────────
    ("WA", "Seattle"): "53033",
    # ── Arizona ────────────────────────────────────────────────────
    ("AZ", "Phoenix"): "04013",
    # ── Massachusetts ──────────────────────────────────────────────
    ("MA", "Boston"): "25025",
    # ── Colorado ───────────────────────────────────────────────────
    ("CO", "Denver"): "08031",
    # ── Tennessee ──────────────────────────────────────────────────
    ("TN", "Nashville"): "47037",
    ("TN", "Memphis"): "47157",
    # ── Missouri ───────────────────────────────────────────────────
    ("MO", "Kansas City"): "29095",
    ("MO", "St. Louis"): "29510",
    # ── Indiana ────────────────────────────────────────────────────
    ("IN", "Indianapolis"): "18097",
    # ── Nevada ─────────────────────────────────────────────────────
    ("NV", "Las Vegas"): "32003",
    # ── District of Columbia ───────────────────────────────────────
    ("DC", "Washington"): "11001",
    # ── Oregon ─────────────────────────────────────────────────────
    ("OR", "Portland"): "41051",
}


def lookup_county_fips(state_code: str, city_name: str) -> str | None:
    """Look up county FIPS code for a state/city pair."""
    return CITY_COUNTY_FIPS.get((state_code.strip().upper(), city_name.strip().title()))
