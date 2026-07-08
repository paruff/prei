"""Management command to scrape Dallas County TX NTS foreclosure notices."""

from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.integrations.county.dallas_tx import scrape_dallas_county_nts
from core.models import CountyForeclosureNotice

logger = logging.getLogger("prei.scraper.dallas_county")


class Command(BaseCommand):
    """Scrape Dallas County TX NTS notices and upsert into CountyForeclosureNotice."""

    help = (
        "Fetch NTS foreclosure notices from Dallas County public records "
        "and upsert into CountyForeclosureNotice"
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and display results without saving to database",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        dry_run = options.get("dry_run", False)

        self.stdout.write("Dallas County: scraping NTS notices ...")
        notices = scrape_dallas_county_nts()

        if not notices:
            self.stdout.write(
                self.style.WARNING(
                    "No notices returned. The site may be unreachable or the "
                    "structure may have changed (see DISC-HG-3)."
                )
            )
            return None

        if dry_run:
            self._report_dry_run(notices)
            return None

        new_count = 0
        updated_count = 0
        errors = 0
        now = timezone.now()

        with transaction.atomic():
            for notice in notices:
                try:
                    sale_date = notice.get("sale_date")
                    if sale_date is not None:
                        from datetime import date as date_type

                        if isinstance(sale_date, str):
                            sale_date = date_type.fromisoformat(sale_date)

                    opening_bid = notice.get("opening_bid")

                    _, created = CountyForeclosureNotice.objects.update_or_create(
                        case_number=notice["case_number"],
                        county=notice["county"],
                        state=notice["state"],
                        defaults={
                            "document_type": notice["document_type"],
                            "address": notice["address"],
                            "city": notice["city"],
                            "zip_code": notice.get("zip_code", ""),
                            "trustee_name": notice.get("trustee_name", ""),
                            "lender_name": notice.get("lender_name", ""),
                            "borrower_name": notice.get("borrower_name", ""),
                            "sale_date": sale_date,
                            "opening_bid": opening_bid,
                            "source_url": notice.get("source_url", ""),
                            "raw_data": notice.get("raw_data", {}),
                            "scraped_at": now,
                            "last_seen_at": now,
                        },
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
                f"Dallas County: {new_count} new, {updated_count} updated, "
                f"{errors} errors"
            )
        )
        return None

    def _report_dry_run(self, notices: list[dict[str, Any]]) -> None:
        """Print parsed notices without saving."""
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"DRY RUN — {len(notices)} notice(s) parsed")
        self.stdout.write(f"{'=' * 60}\n")

        for i, notice in enumerate(notices, start=1):
            self.stdout.write(f"--- Notice #{i} ---")
            self.stdout.write(f"  Case #:     {notice.get('case_number', 'N/A')}")
            self.stdout.write(f"  Address:    {notice.get('address', 'N/A')}")
            self.stdout.write(f"  City:       {notice.get('city', 'N/A')}")
            self.stdout.write(f"  State:      {notice.get('state', 'N/A')}")
            self.stdout.write(f"  ZIP:        {notice.get('zip_code', 'N/A')}")
            self.stdout.write(f"  Trustee:    {notice.get('trustee_name', 'N/A')}")
            self.stdout.write(f"  Lender:     {notice.get('lender_name', 'N/A')}")
            self.stdout.write(f"  Sale Date:  {notice.get('sale_date', 'N/A')}")
            self.stdout.write(f"  Bid:        {notice.get('opening_bid', 'N/A')}")
            self.stdout.write("")
