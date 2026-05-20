"""Management command to enrich VRM properties from detail-page fields."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests
from django.core.management.base import BaseCommand, CommandError

from core.integrations.sources.vrm_scraper import VrmScraper
from core.models import VrmProperty

logger = logging.getLogger("prei.scraper.vrm")


class Command(BaseCommand):
    """Enrich existing VRM properties by scraping each detail page."""

    help = "Fetch VRM detail pages to enrich stored VrmProperty records"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--state",
            required=True,
            type=str,
            help="2-letter uppercase state code, e.g. VA",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-enrich properties even if year_built is already populated",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        state = options["state"]
        force = options["force"]
        if not re.fullmatch(r"[A-Z]{2}", state):
            raise CommandError("state must be a 2-letter uppercase code")

        scraper = VrmScraper()
        properties = VrmProperty.objects.filter(
            state=state,
            status=VrmProperty.Status.FOR_SALE,
        ).order_by("id")

        enriched_count = 0
        requested_count = 0
        for property_record in properties:
            if property_record.year_built is not None and not force:
                logger.debug(
                    "Skipping %s, already enriched", property_record.vrm_property_id
                )
                continue

            if requested_count > 0 and scraper.delay_seconds > 0:
                time.sleep(scraper.delay_seconds)

            try:
                html = scraper.fetch_property_detail(property_record.vrm_listing_url)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    logger.warning(
                        "Detail page not found for %s", property_record.vrm_property_id
                    )
                else:
                    logger.warning(
                        "Failed to fetch detail page for %s: %s",
                        property_record.vrm_property_id,
                        exc,
                    )
                requested_count += 1
                continue
            except requests.RequestException as exc:
                logger.warning(
                    "Failed to fetch detail page for %s: %s",
                    property_record.vrm_property_id,
                    exc,
                )
                requested_count += 1
                continue

            detail_data = scraper.extract_property_details_from_html(html)
            update_fields: list[str] = []
            for field_name, field_value in detail_data.items():
                if field_value is None:
                    continue
                setattr(property_record, field_name, field_value)
                update_fields.append(field_name)

            if update_fields:
                property_record.save(update_fields=update_fields)
                enriched_count += 1
            requested_count += 1

        logger.info("Enriched %s properties for state %s", enriched_count, state)
        self.stdout.write(
            self.style.SUCCESS(
                f"Enriched {enriched_count} properties for state {state}"
            )
        )
