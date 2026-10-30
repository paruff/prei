"""Seed one market end to end: growth area (with GACS), properties, rent inputs.

Usage:
    python manage.py seed_market                      # Dallas, TX
    python manage.py seed_market --city Austin --state TX
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import GrowthArea

# Used when Census/FRED/HUD are unreachable or keys are missing (plan.md risk).
FIXTURE_GROWTH_AREAS = {
    ("TX", "Dallas"): dict(
        metro_area="Dallas-Fort Worth-Arlington, TX",
        population_growth_rate=Decimal("1.20"),
        employment_growth_rate=Decimal("2.10"),
        median_income_growth=Decimal("3.40"),
        housing_demand_index=72,
        supply_constraint_index=45,
        rent_growth_rate=Decimal("4.00"),
        fmr_2br=Decimal("1650.00"),
        county_fips="48113",
    ),
}


class Command(BaseCommand):
    help = "Seed one market: growth area with GACS, properties and rent inputs."

    def add_arguments(self, parser):
        parser.add_argument("--state", default="TX")
        parser.add_argument("--city", default="Dallas")

    def handle(self, *args, **options):
        state = options["state"].strip().upper()
        city = options["city"].strip().title()

        try:
            call_command("populate_growth_areas", state=[state], city=[city])
        except CommandError as exc:
            self.stderr.write(f"populate_growth_areas failed: {exc}")
        if not GrowthArea.objects.filter(state=state, city_name=city).exists():
            fixture = FIXTURE_GROWTH_AREAS.get((state, city))
            if fixture is None:
                raise CommandError(f"No live data and no fixture for {city}, {state}")
            GrowthArea.objects.update_or_create(
                state=state,
                city_name=city,
                defaults={**fixture, "data_timestamp": timezone.now()},
            )
            self.stdout.write(
                self.style.WARNING(f"Used fixture data for {city}, {state}")
            )

        call_command("seed_markets")
        call_command("seed_data")
        area = GrowthArea.objects.get(state=state, city_name=city)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {city}, {state}: GACS={area.composite_score_display}"
            )
        )
