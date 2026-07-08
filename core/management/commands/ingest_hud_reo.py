"""Management command to ingest HUD REO properties from data.gov feed."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import HudProperty

logger = logging.getLogger("prei.ingestion.hud")

# Human gate DISC-HG-1: confirm this URL before production use.
# The data.gov HUD REO JSON endpoint may change; verify before deploying.
DEFAULT_ENDPOINT = "https://hudhomestore.data.gov/api/reo-properties"

HUD_FIXTURE_DATA: dict[str, list[dict[str, Any]]] = {
    "results": [
        {
            "case_number": "HUD-2026-001",
            "asking_price": 150000.00,
            "street_address": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
            "county": "Travis",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "square_feet": 1500,
            "property_type": "Single Family",
            "status": "Active",
            "insured_status": "FHA Insured",
            "listing_url": "https://hudhomestore.gov/property/HUD-2026-001",
            "image_url": "https://hudhomestore.gov/images/HUD-2026-001.jpg",
            "description": "Well-maintained 3BR home in Austin.",
        },
        {
            "case_number": "HUD-2026-002",
            "asking_price": 200000.00,
            "street_address": "456 Oak Ave",
            "city": "Dallas",
            "state": "TX",
            "zip": "75201",
            "county": "Dallas",
            "bedrooms": 4,
            "bathrooms": 3.0,
            "square_feet": 2200,
            "property_type": "Single Family",
            "status": "Sold",
            "insured_status": "Conventional",
            "listing_url": "https://hudhomestore.gov/property/HUD-2026-002",
            "image_url": "",
            "description": "Recently sold 4BR home in Dallas.",
        },
        {
            "case_number": "HUD-2026-003",
            "asking_price": 125000.00,
            "street_address": "789 Pine St",
            "city": "Houston",
            "state": "TX",
            "zip": "77001",
            "county": "Harris",
            "bedrooms": 2,
            "bathrooms": 1.0,
            "square_feet": 950,
            "property_type": "Condo",
            "status": "Active",
            "insured_status": "Uninsured",
            "listing_url": "https://hudhomestore.gov/property/HUD-2026-003",
            "image_url": "",
            "description": "Cozy 2BR condo in Houston.",
        },
    ]
}


def _map_status(raw_status: str) -> str:
    """Map data.gov status string to HudProperty.Status value."""
    mapping: dict[str, str] = {
        "active": "active",
        "pending": "pending",
        "sold": "sold",
        "contingent": "contingent",
    }
    return mapping.get(raw_status.lower(), "active")


def _map_insured_status(raw: str) -> str:
    """Map data.gov insured_status string to HudProperty.InsuredStatus value."""
    mapping: dict[str, str] = {
        "fha insured": "fha_insured",
        "conventional": "conventional",
        "uninsured": "uninsured",
        "va": "va",
    }
    return mapping.get(raw.lower(), "")


class Command(BaseCommand):
    """Fetch HUD REO properties from data.gov feed and upsert into HudProperty."""

    help = (
        "Fetch HUD REO properties from data.gov feed, "
        "upsert into HudProperty, and mark stale records as removed"
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Use embedded fixture data instead of HTTP endpoint "
            "(still writes to DB; safe for testing)",
        )
        parser.add_argument(
            "--endpoint",
            type=str,
            default=None,
            help="Override the data.gov HUD REO JSON endpoint URL",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: C901
        dry_run = options["dry_run"]
        endpoint = options.get("endpoint") or DEFAULT_ENDPOINT

        # ---- 1. Fetch data ----
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — using embedded fixture data")
            )
            raw_data = HUD_FIXTURE_DATA
        else:
            self.stdout.write(f"Fetching HUD REO data from {endpoint} ...")
            try:
                response = requests.get(endpoint, timeout=30)
                response.raise_for_status()
                raw_data = response.json()
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"HTTP request failed: {exc}"))
                raise

        results = raw_data.get("results", [])
        if not results:
            self.stdout.write(self.style.WARNING("No results found in feed."))
            return

        seen_case_numbers: set[str] = set()
        added = 0
        updated = 0
        now = timezone.now()

        # ---- 2. Upsert each record ----
        for item in results:
            case_number = item.get("case_number", "")
            if not case_number:
                continue

            seen_case_numbers.add(case_number)

            raw_asking = item.get("asking_price")
            asking_price: Decimal | None = (
                Decimal(str(raw_asking)) if raw_asking is not None else None
            )
            raw_baths = item.get("bathrooms")
            bathrooms: Decimal | None = (
                Decimal(str(raw_baths)) if raw_baths is not None else None
            )

            defaults: dict[str, Any] = {
                "address": item.get("street_address", ""),
                "city": item.get("city", ""),
                "state": item.get("state", ""),
                "zip_code": item.get("zip", ""),
                "county": item.get("county", ""),
                "asking_price": asking_price,
                "bedrooms": item.get("bedrooms"),
                "bathrooms": bathrooms,
                "square_feet": item.get("square_feet"),
                "property_type": item.get("property_type", ""),
                "status": _map_status(item.get("status", "Active")),
                "insured_status": _map_insured_status(item.get("insured_status", "")),
                "listing_url": item.get("listing_url", ""),
                "image_url": item.get("image_url", ""),
                "description": item.get("description", ""),
                "scraped_at": now,
                "last_seen_at": now,
            }

            obj, created = HudProperty.objects.update_or_create(
                hud_case_number=case_number,
                defaults=defaults,
            )

            if created:
                added += 1
            else:
                updated += 1

        # ---- 3. Mark stale records as REMOVED ----
        removed = (
            HudProperty.objects.filter(
                status__in=[
                    HudProperty.Status.ACTIVE,
                    HudProperty.Status.PENDING,
                    HudProperty.Status.CONTINGENT,
                ],
            )
            .exclude(hud_case_number__in=seen_case_numbers)
            .update(
                status=HudProperty.Status.REMOVED,
                last_seen_at=now,
            )
        )

        # ---- 4. Log summary ----
        self.stdout.write(
            self.style.SUCCESS(
                f"Added: {added}, Updated: {updated}, Removed: {removed}"
            )
        )
