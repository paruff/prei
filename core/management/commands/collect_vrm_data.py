"""Management command to collect VA REO listings from VRM Properties."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.integrations.sources.vrm_scraper import VrmScraper
from core.models import VrmProperty

logger = logging.getLogger("prei.scraper.vrm")


class Command(BaseCommand):
    """Run VRM listing collection for one state and upsert into VrmProperty."""

    help = "Collect VRM VA REO listings for a required 2-letter state code"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--state",
            required=True,
            type=str,
            help="2-letter uppercase state code, e.g. VA",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        state = options["state"]
        if not re.fullmatch(r"[A-Z]{2}", state):
            raise CommandError("state must be a 2-letter uppercase code")

        scraper = VrmScraper()
        properties = scraper.collect_state_listings(state)

        if not properties:
            logger.info("No properties found for state %s", state)
            self.stdout.write(
                self.style.SUCCESS(f"Collected 0 properties for state {state}")
            )
            return

        now = timezone.now()

        with transaction.atomic():
            for property_data in properties:
                normalized_property_data = dict(property_data)
                normalized_property_data["state"] = (
                    normalized_property_data.get("state") or state
                )
                self._upsert_property(normalized_property_data, now)

        logger.info("Collected %s properties for state %s", len(properties), state)
        self.stdout.write(
            self.style.SUCCESS(
                f"Collected {len(properties)} properties for state {state}"
            )
        )

    def _upsert_property(self, property_data: dict[str, Any], now: datetime) -> None:
        existing_scraped_at = (
            VrmProperty.objects.filter(vrm_property_id=property_data["vrm_property_id"])
            .values_list("scraped_at", flat=True)
            .first()
        )

        defaults = {
            "vrm_listing_url": property_data["vrm_listing_url"],
            "address": property_data.get("address", ""),
            "city": property_data.get("city", ""),
            "state": property_data.get("state", ""),
            "zip_code": property_data.get("zip_code", ""),
            "list_price": property_data.get("list_price"),
            "bedrooms": property_data.get("bedrooms"),
            "bathrooms": property_data.get("bathrooms"),
            "square_feet": property_data.get("square_feet"),
            "status": property_data.get("status", VrmProperty.Status.FOR_SALE),
            "listing_type": property_data.get(
                "listing_type", VrmProperty.ListingType.TRADITIONAL
            ),
            "vendee_eligible": property_data.get("vendee_eligible", False),
            "scraped_at": existing_scraped_at or now,
            "last_seen_at": now,
        }

        VrmProperty.objects.update_or_create(
            vrm_property_id=property_data["vrm_property_id"],
            defaults=defaults,
        )
