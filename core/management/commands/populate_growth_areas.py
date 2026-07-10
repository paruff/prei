"""Management command to populate GrowthArea model with real Census and FRED data.

Usage:
    python manage.py populate_growth_areas --state=CA --city="San Francisco"
    python manage.py populate_growth_areas --state=CA --city="San Francisco" --force
    python manage.py populate_growth_areas --file=growth_cities.txt
    python manage.py populate_growth_areas --state=CA --city="San Francisco" --state=TX --city="Austin"

Employment growth is fetched from FRED (Federal Reserve) rather than BLS,
because the BLS free tier is limited to 25 requests/day.
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.integrations.market.census import (
    compute_supply_constraint_index,
    fetch_housing_demand_index,
    fetch_place_growth_metrics,
)
from core.integrations.market.fmr_adapter import fetch_fmr_data
from core.integrations.sources.fred_adapter import FREDAdapter
from core.models import GrowthArea

# Cache TTL: re-fetch if data older than this
CACHE_TTL_DAYS = 30

# Common major cities with their Census place codes
# Format: (state_code, city_name, place_code)
MAJOR_CITIES = [
    ("CA", "San Francisco", "67000"),
    ("CA", "Los Angeles", "44000"),
    ("CA", "San Diego", "66000"),
    ("CA", "San Jose", "68000"),
    ("CA", "Sacramento", "64000"),
    ("CA", "Oakland", "53000"),
    ("CA", "Fresno", "27000"),
    ("CA", "Long Beach", "43000"),
    ("NY", "New York", "51000"),
    ("NY", "Buffalo", "11000"),
    ("TX", "Houston", "35000"),
    ("TX", "San Antonio", "65000"),
    ("TX", "Dallas", "19000"),
    ("TX", "Austin", "05000"),
    ("TX", "Fort Worth", "27000"),
    ("FL", "Miami", "45000"),
    ("FL", "Tampa", "71000"),
    ("FL", "Orlando", "53000"),
    ("FL", "Jacksonville", "35000"),
    ("IL", "Chicago", "14000"),
    ("PA", "Philadelphia", "60000"),
    ("PA", "Pittsburgh", "61000"),
    ("OH", "Columbus", "18000"),
    ("OH", "Cleveland", "16000"),
    ("OH", "Cincinnati", "15000"),
    ("GA", "Atlanta", "04000"),
    ("NC", "Charlotte", "12000"),
    ("NC", "Raleigh", "55000"),
    ("MI", "Detroit", "22000"),
    ("WA", "Seattle", "63000"),
    ("AZ", "Phoenix", "55000"),
    ("MA", "Boston", "07000"),
    ("CO", "Denver", "20000"),
    ("TN", "Nashville", "52006"),
    ("TN", "Memphis", "48000"),
    ("MO", "Kansas City", "38000"),
    ("MO", "St. Louis", "65000"),
    ("IN", "Indianapolis", "36003"),
    ("NV", "Las Vegas", "40000"),
    ("DC", "Washington", "50000"),
    ("OR", "Portland", "59000"),
]


def _lookup_place_code(state_code: str, city_name: str) -> str | None:
    """Look up Census place code for a given state and city."""
    state_code = state_code.strip().upper()
    city_name = city_name.strip().title()

    for st, city, code in MAJOR_CITIES:
        if st == state_code and city.lower() == city_name.lower():
            return code

    return None


class Command(BaseCommand):
    help = "Populate GrowthArea with Census/FRED growth metrics for cities"

    def add_arguments(self, parser):
        parser.add_argument(
            "--state",
            action="append",
            dest="states",
            help="2-letter state code (repeat for multiple, use with --city)",
        )
        parser.add_argument(
            "--city",
            action="append",
            dest="cities",
            help="City name (repeat for multiple, must match --state order)",
        )
        parser.add_argument(
            "--file",
            type=str,
            help="Path to file with lines: state,city,place_code (one per line)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Force re-fetch even if cached data is fresh (< 30 days)",
        )
        parser.add_argument(
            "--list-cities",
            action="store_true",
            default=False,
            help="List all supported cities with their place codes and exit",
        )

    def handle(self, *args, **options):
        # List cities mode
        if options.get("list_cities"):
            self.stdout.write("Supported cities (state, city, place_code):")
            for st, city, code in MAJOR_CITIES:
                self.stdout.write(f"  {st}, {city}, {code}")
            return

        states = options.get("states") or []
        cities = options.get("cities") or []
        file_path = options.get("file")
        force = options.get("force", False)

        # Build list of (state, city, place_code) tuples
        targets: list[tuple[str, str, str]] = []

        if file_path:
            targets.extend(self._parse_file(file_path))
        elif states and cities:
            if len(states) != len(cities):
                raise CommandError(
                    "--state and --city must be provided in pairs (same count)"
                )
            for state, city in zip(states, cities):
                place_code = _lookup_place_code(state, city)
                if not place_code:
                    raise CommandError(
                        f"City '{city}' in state '{state}' not in supported list. "
                        f"Use --list-cities to see supported cities, or provide place_code via --file."
                    )
                targets.append(
                    (state.strip().upper(), city.strip().title(), place_code)
                )
        else:
            raise CommandError(
                "Provide either --state/--city pairs or --file. "
                "Use --list-cities to see supported cities."
            )

        if not targets:
            raise CommandError("No valid city targets to process")

        # Check API keys
        census_api_key = os.getenv("CENSUS_API_KEY", "")

        if not census_api_key:
            raise CommandError(
                "CENSUS_API_KEY not set. Required for population/income growth and housing demand."
            )
        # FRED API key is optional — FREDAdapter reads from FRED_API_KEY env var automatically

        self.stdout.write(f"Processing {len(targets)} cities...")

        refreshed = 0
        skipped = 0
        errors = 0

        # State-level FRED cache: avoids duplicate API calls for cities in the same state.
        # Employment growth is state-level, not city-level, so we cache per state_code.
        _fred_cache: dict[str, Decimal | None] = {}

        for state_code, city_name, place_code in targets:
            self.stdout.write(
                f"Processing {city_name}, {state_code} (place={place_code})..."
            )

            # Check cache freshness
            if not force:
                existing = GrowthArea.objects.filter(
                    state=state_code, city_name=city_name
                ).first()
                if existing and existing.data_timestamp:
                    age = timezone.now() - existing.data_timestamp
                    if age < timedelta(days=CACHE_TTL_DAYS):
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Cached data is {age.days} days old "
                                f"(< {CACHE_TTL_DAYS}). Use --force to refresh."
                            )
                        )
                        skipped += 1
                        continue

            try:
                # 1. Census: population + income growth (two-vintage)
                census_data = fetch_place_growth_metrics(
                    state_code=state_code,
                    place_code=place_code,
                    api_key=census_api_key,
                )

                if census_data is None:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed to fetch Census data for {city_name}, {state_code}"
                        )
                    )
                    errors += 1
                    continue

                pop_growth = census_data.get("population_growth_rate")
                income_growth = census_data.get("median_income_growth_rate")
                units_growth = census_data.get("housing_units_growth_rate")

                # 2. Employment growth via FRED (state-level, cached per state)
                # FRED replaces BLS because the BLS free tier is rate-limited to 25 req/day
                if state_code not in _fred_cache:
                    fed = FREDAdapter()
                    _fred_cache[state_code] = fed.fetch_state_employment_growth(
                        state_code=state_code,
                    )
                emp_growth = _fred_cache[state_code]

                if emp_growth is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Employment growth unavailable from FRED for {state_code}"
                        )
                    )

                # 2b. QCEW county-level employment (replaces FRED when county is known)
                county_fips = ""
                from core.integrations.market.county_fips_map import lookup_county_fips
                from core.integrations.market.qcew_adapter import (
                    fetch_county_employment_growth,
                )

                cfips = lookup_county_fips(state_code, city_name)
                if cfips:
                    qcew_growth = fetch_county_employment_growth(cfips, year=2024)
                    if qcew_growth is not None:
                        emp_growth = qcew_growth
                        county_fips = cfips
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  QCEW county employment for {city_name}: {qcew_growth}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  QCEW data unavailable for FIPS {cfips}, using FRED"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  No county FIPS for {city_name}, {state_code} — using FRED"
                        )
                    )

                # 3. Census: housing demand proxy
                housing_demand = fetch_housing_demand_index(
                    state_code=state_code,
                    place_code=place_code,
                    api_key=census_api_key,
                    population_growth_rate=pop_growth,
                )

                if housing_demand is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Housing demand index unavailable for {city_name}, {state_code}"
                        )
                    )
                    housing_demand = 50  # neutral default

                # 4. Supply constraint index (GA-6)
                supply_constraint = compute_supply_constraint_index(
                    population_growth_rate=pop_growth,
                    housing_units_growth_rate=units_growth,
                )
                if supply_constraint is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Supply constraint index unavailable for {city_name}, {state_code}"
                        )
                    )
                    supply_constraint = 50  # neutral default

                # Compute net migration from population data
                from core.models.growth import compute_net_migration

                net_mig, net_mig_rate = compute_net_migration(
                    census_data.get("population_current"), pop_growth
                )

                # 5. HUD FMR: 2BR rent benchmark + year-over-year growth
                from core.integrations.market.county_fips_map import (
                    lookup_county_fips,
                )

                cfips = lookup_county_fips(state_code, city_name)
                fmr_defaults: dict[str, Any] = {}
                if cfips:
                    fmr_data = fetch_fmr_data(state_code, cfips, city_name=city_name)
                    if fmr_data:
                        fmr_defaults["fmr_2br"] = fmr_data["fmr_2br"]
                        fmr_defaults["fmr_year"] = fmr_data["fmr_year"]
                        fmr_defaults["rent_growth_rate"] = fmr_data.get(
                            "rent_growth_rate"
                        )

                # 6. Upsert GrowthArea
                growth_area, created = GrowthArea.objects.update_or_create(
                    state=state_code,
                    city_name=city_name,
                    defaults={
                        "metro_area": "",  # TODO: populate from Census CBSA API
                        "population": census_data.get("population_current"),
                        "population_growth_rate": pop_growth,
                        "employment_growth_rate": emp_growth,
                        "median_income_growth": income_growth,
                        "housing_demand_index": housing_demand,
                        "supply_constraint_index": supply_constraint,
                        "net_migration": net_mig,
                        "net_migration_rate": net_mig_rate,
                        "county_fips": county_fips,
                        "data_timestamp": timezone.now(),
                        **fmr_defaults,
                    },
                )

                action = "Created" if created else "Updated"
                emp_str = f"{emp_growth}" if emp_growth is not None else "N/A"
                fmr_str = (
                    f", fmr_2br={fmr_defaults.get('fmr_2br')}"
                    if fmr_defaults.get("fmr_2br")
                    else ""
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {action} GrowthArea: pop_growth={pop_growth}, "
                        f"emp_growth={emp_str}, income_growth={income_growth}, "
                        f"housing_demand={housing_demand}, supply={supply_constraint}"
                        f"{fmr_str}"
                    )
                )
                refreshed += 1

            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"  Error processing {city_name}, {state_code}: {exc}"
                    )
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Refreshed={refreshed}, Skipped={skipped}, Errors={errors}"
            )
        )

    def _parse_file(self, file_path: str) -> list[tuple[str, str, str]]:
        """Parse a file with lines: state,city,place_code"""
        targets = []
        try:
            with open(file_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) != 3:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Line {line_num}: invalid format (expected state,city,place_code)"
                            )
                        )
                        continue
                    state, city, place_code = parts
                    targets.append((state.upper(), city.title(), place_code))
        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")
        return targets
