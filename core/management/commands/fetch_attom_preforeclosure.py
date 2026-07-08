"""Management command to fetch ATTOM preforeclosure notices for a ZIP code."""

from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.integrations.sources.attom_preforeclosure import fetch_attom_preforeclosure
from core.models import CountyForeclosureNotice

logger = logging.getLogger("prei.attom.preforeclosure")


class Command(BaseCommand):
    """Fetch ATTOM preforeclosure notices and upsert into CountyForeclosureNotice."""

    help = (
        "Fetch pre-foreclosure notices (NOD, NTS, Lis Pendens) from ATTOM "
        "for a target ZIP code and upsert into CountyForeclosureNotice"
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--zip-code",
            type=str,
            required=True,
            help="5-digit US ZIP code to search",
        )
        parser.add_argument(
            "--radius",
            type=int,
            default=25,
            help="Search radius in miles (default: 25)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and display results without saving to database",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        zip_code = str(options["zip_code"]).strip()
        radius = int(options["radius"])
        dry_run = options.get("dry_run", False)

        self.stdout.write(
            f"ATTOM: fetching preforeclosure notices for ZIP={zip_code} ..."
        )

        notices = fetch_attom_preforeclosure(zip_code=zip_code, radius=radius)

        if not notices:
            self.stdout.write(
                self.style.WARNING(
                    "No notices returned.  Check that ATTOM_API_KEY is set and "
                    "the subscription covers the /preforeclosure/detail endpoint "
                    "(see DISC-HG-4)."
                )
            )
            return None

        if dry_run:
            self._report_dry_run(notices, zip_code)
            return None

        new_count = 0
        updated_count = 0
        errors = 0
        now = timezone.now()

        with transaction.atomic():
            for notice in notices:
                try:
                    upsert_defaults = {
                        k: v for k, v in notice.items() if k != "case_number"
                    }
                    upsert_defaults["last_seen_at"] = now

                    _, created = CountyForeclosureNotice.objects.update_or_create(
                        case_number=notice["case_number"],
                        county=notice.get("county", ""),
                        state=notice.get("state", ""),
                        defaults=upsert_defaults,
                    )

                    if created:
                        new_count += 1
                    else:
                        updated_count += 1

                except Exception as exc:
                    errors += 1
                    logger.error(
                        "Failed to upsert notice %s: %s",
                        notice.get("case_number", "?"),
                        exc,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"ZIP={zip_code}: {new_count} new, {updated_count} updated, "
                f"{errors} errors"
            )
        )
        return None

    def _report_dry_run(self, notices: list[dict[str, Any]], zip_code: str) -> None:
        """Print parsed notices without saving."""
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"DRY RUN — ZIP={zip_code}: {len(notices)} notice(s)")
        self.stdout.write(f"{'=' * 60}\n")

        for i, notice in enumerate(notices, start=1):
            self.stdout.write(f"--- Notice #{i} ---")
            self.stdout.write(f"  Case #:     {notice.get('case_number', 'N/A')}")
            self.stdout.write(f"  Type:       {notice.get('document_type', 'N/A')}")
            self.stdout.write(f"  Address:    {notice.get('address', 'N/A')}")
            self.stdout.write(f"  City:       {notice.get('city', 'N/A')}")
            self.stdout.write(f"  State:      {notice.get('state', 'N/A')}")
            self.stdout.write(f"  County:     {notice.get('county', 'N/A')}")
            self.stdout.write(f"  Lender:     {notice.get('lender_name', 'N/A')}")
            self.stdout.write(f"  Filing:     {notice.get('filing_date', 'N/A')}")
            self.stdout.write(f"  Sale:       {notice.get('sale_date', 'N/A')}")
            self.stdout.write(f"  Balance:    {notice.get('unpaid_balance', 'N/A')}")
            self.stdout.write("")
