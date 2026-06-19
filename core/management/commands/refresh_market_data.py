"""Management command to refresh market data from Census and BLS APIs.

Usage:
    python manage.py refresh_market_data --zip=90210
    python manage.py refresh_market_data --zip=90210 --state=VA --force
    python manage.py refresh_market_data --zip=90210 --zip=23220
"""
from __future__ import annotations

import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.integrations.market.census import fetch_zip_demographics
from core.integrations.market.bls import fetch_unemployment_rate
from core.models import MarketSnapshot

CACHE_TTL_DAYS = 30


class Command(BaseCommand):
    help = "Fetch Census and BLS market indicators for given ZIP codes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--zip",
            action="append",
            dest="zip_codes",
            help="ZIP code to fetch data for (repeat for multiple)",
        )
        parser.add_argument(
            "--state",
            type=str,
            default="",
            help="State code for BLS unemployment data (e.g. VA)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Force re-fetch even if cached data is fresh (< 30 days)",
        )

    def handle(self, *args, **options):
        zip_codes = options.get("zip_codes") or []
        state_code = options.get("state", "").strip().upper()
        force = options.get("force", False)

        if not zip_codes:
            raise CommandError("At least one --zip code is required")

        census_api_key = os.getenv("CENSUS_API_KEY", "")
        bls_api_key = os.getenv("BLS_API_KEY", "")

        if not census_api_key:
            self.stdout.write(
                self.style.WARNING(
                    "CENSUS_API_KEY not set. Census demographic data will be skipped."
                )
            )
        if not bls_api_key:
            self.stdout.write(
                self.style.WARNING(
                    "BLS_API_KEY not set. BLS unemployment data will be skipped."
                )
            )

        refreshed = 0
        skipped = 0
        errors = 0

        for zip_code in zip_codes:
            zip_code = zip_code.strip()
            if not zip_code:
                continue

            self.stdout.write(f"Processing ZIP {zip_code}...")

            # Check cache freshness
            if not force:
                existing = MarketSnapshot.objects.filter(zip_code=zip_code).first()
                if existing and existing.fetched_at:
                    age = timezone.now() - existing.fetched_at
                    if age < timedelta(days=CACHE_TTL_DAYS):
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Cached data for {zip_code} is {age.days} days old "
                                f"(< {CACHE_TTL_DAYS}). Use --force to refresh."
                            )
                        )
                        skipped += 1
                        continue

            # Fetch Census demographics
            census_data = None
            if census_api_key:
                census_data = fetch_zip_demographics(zip_code, census_api_key)

            # Fetch BLS unemployment (if state provided and key available)
            unemployment_rate = None
            if state_code and bls_api_key:
                unemployment_rate = fetch_unemployment_rate(state_code, bls_api_key)

            # Upsert MarketSnapshot
            snapshot, created = MarketSnapshot.objects.update_or_create(
                zip_code=zip_code,
                defaults={
                    "area_type": "zip",
                    "population": (
                        census_data.get("population") if census_data else None
                    ),
                    "population_growth_pct_5yr": (
                        census_data.get("population_growth_pct_5yr")
                        if census_data
                        else None
                    ),
                    "median_household_income": (
                        census_data.get("median_household_income")
                        if census_data
                        else None
                    ),
                    "unemployment_rate": unemployment_rate,
                    "state": state_code,
                    "fetched_at": timezone.now(),
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {action} MarketSnapshot for {zip_code}"
                    f" (pop={snapshot.population}, "
                    f"income={snapshot.median_household_income}, "
                    f"unemployment={snapshot.unemployment_rate})"
                )
            )
            refreshed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Refreshed={refreshed}, Skipped={skipped}, Errors={errors}"
            )
        )
