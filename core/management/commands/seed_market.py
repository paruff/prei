"""Seed one market end to end: growth area (with GACS), properties, rent inputs.

Usage:
    python manage.py seed_market                      # Dallas, TX
    python manage.py seed_market --city Austin --state TX
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import GrowthArea, VrmProperty

# Fallback when Census/FRED/HUD are unreachable or keys are missing (plan.md risk).
# PLACEHOLDER values, not sourced data: for demo/CI only, never for decisions.
FIXTURE_GROWTH_AREAS = {
    ("TX", "Dallas"): dict(
        metro_area="Dallas-Fort Worth-Arlington, TX",
        population_growth_rate=Decimal("0.01"),
        employment_growth_rate=Decimal("0.02"),
        median_income_growth=Decimal("0.03"),
        housing_demand_index=72,
        supply_constraint_index=45,
        rent_growth_rate=Decimal("0.04"),
        fmr_2br=Decimal("1650.00"),
        county_fips="48113",
    ),
}

# Discoverable listings for the seeded market (VRM rows; discovery reads the DB,
# never the network). PLACEHOLDER values: one passes default screening, one fails.
FIXTURE_VRM_LISTINGS: tuple[dict[str, Any], ...] = (
    dict(
        vrm_property_id=900001,
        address="1200 Seed Pass Ln",
        zip_code="75201",
        list_price=Decimal("180000.00"),
        projected_monthly_rent=Decimal("1800.00"),
        bedrooms=3,
    ),
    dict(
        vrm_property_id=900002,
        address="3400 Seed Fail Ct",
        zip_code="75204",
        list_price=Decimal("450000.00"),
        projected_monthly_rent=Decimal("2200.00"),
        bedrooms=3,
    ),
)


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
        now = timezone.now()
        for listing in FIXTURE_VRM_LISTINGS:
            VrmProperty.objects.update_or_create(
                vrm_property_id=listing["vrm_property_id"],
                defaults={
                    **listing,
                    "vrm_listing_url": f"https://example.com/vrm/{listing['vrm_property_id']}",
                    "city": city,
                    "state": state,
                    "property_type": "single-family",
                    "status": VrmProperty.Status.FOR_SALE,
                    "scraped_at": now,
                    "last_seen_at": now,
                },
            )
        area = GrowthArea.objects.get(state=state, city_name=city)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {city}, {state}: GACS={area.composite_score_display()}"
            )
        )
