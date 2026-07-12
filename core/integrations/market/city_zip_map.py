"""City → representative ZIP code mapping for GreatSchools and FMR lookups.

Maps (state_code, city_name) → a representative ZIP code for the city.
Used by the growth explorer to resolve school ratings and rent data
when the Census ACS place-level data does not provide a ZIP code.

Source: manually curated from USPS city/ZIP data for common US cities.
"""

from __future__ import annotations

CITY_ZIP: dict[tuple[str, str], str] = {
    # Alabama
    ("AL", "Birmingham"): "35203",
    ("AL", "Montgomery"): "36104",
    ("AL", "Huntsville"): "35801",
    # Arizona
    ("AZ", "Phoenix"): "85004",
    ("AZ", "Tucson"): "85701",
    ("AZ", "Mesa"): "85201",
    # California
    ("CA", "Los Angeles"): "90012",
    ("CA", "San Diego"): "92101",
    ("CA", "San Jose"): "95112",
    ("CA", "San Francisco"): "94102",
    ("CA", "Fresno"): "93721",
    ("CA", "Sacramento"): "95814",
    # Colorado
    ("CO", "Denver"): "80202",
    ("CO", "Colorado Springs"): "80903",
    # Florida
    ("FL", "Miami"): "33130",
    ("FL", "Tampa"): "33602",
    ("FL", "Orlando"): "32801",
    ("FL", "Jacksonville"): "32202",
    ("FL", "St. Petersburg"): "33701",
    ("FL", "Fort Lauderdale"): "33301",
    ("FL", "Tallahassee"): "32301",
    ("FL", "Cape Coral"): "33904",
    ("FL", "Port St. Lucie"): "34952",
    ("FL", "Hialeah"): "33010",
    # Georgia
    ("GA", "Atlanta"): "30303",
    # Illinois
    ("IL", "Chicago"): "60601",
    # Indiana
    ("IN", "Indianapolis"): "46204",
    # Michigan
    ("MI", "Detroit"): "48226",
    # Minnesota
    ("MN", "Minneapolis"): "55401",
    # Missouri
    ("MO", "Kansas City"): "64106",
    ("MO", "St. Louis"): "63101",
    # Nevada
    ("NV", "Las Vegas"): "89101",
    # New York
    ("NY", "New York"): "10001",
    # North Carolina
    ("NC", "Charlotte"): "28202",
    ("NC", "Raleigh"): "27601",
    # Ohio
    ("OH", "Columbus"): "43215",
    ("OH", "Cleveland"): "44113",
    ("OH", "Cincinnati"): "45202",
    # Oklahoma
    ("OK", "Oklahoma City"): "73102",
    # Oregon
    ("OR", "Portland"): "97204",
    # Pennsylvania
    ("PA", "Philadelphia"): "19102",
    ("PA", "Pittsburgh"): "15222",
    # Tennessee
    ("TN", "Nashville"): "37201",
    ("TN", "Memphis"): "38103",
    # Texas
    ("TX", "Austin"): "78701",
    ("TX", "Houston"): "77002",
    ("TX", "Dallas"): "75201",
    ("TX", "San Antonio"): "78205",
    ("TX", "Fort Worth"): "76102",
    ("TX", "El Paso"): "79901",
    # Washington
    ("WA", "Seattle"): "98101",
    # Wisconsin
    ("WI", "Milwaukee"): "53202",
}


def lookup_city_zip(state_code: str, city_name: str) -> str | None:
    """Look up a representative ZIP code for a state/city pair."""
    return CITY_ZIP.get((state_code.strip().upper(), city_name.strip()))
