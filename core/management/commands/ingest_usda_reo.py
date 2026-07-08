"""Management command to ingest USDA REO properties from data.gov feed."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import UsdaProperty

logger = logging.getLogger("prei.ingestion.usda")

# Human gate DISC-HG-2: confirm this URL before production use.
# The data.gov USDA TXT file is a fixed-width format last updated 2018-09-10.
# Source: https://catalog.data.gov/dataset/usda-rural-development-resale-properties-foreclosure
DEFAULT_ENDPOINT = (
    "https://www.sc.egov.usda.gov/data/files/Property/FSASFHFOREData9-7-18.txt"
)

USDA_FIXTURE_DATA: list[dict[str, Any]] = [
    {
        "usda_case_number": "USDA-2026-001",
        "address": "501 S 1st St",
        "city": "San Jose",
        "state": "IL",
        "zip_code": "62682",
        "county": "Mason",
        "list_price": Decimal("14048.00"),
        "bedrooms": 3,
        "bathrooms": Decimal("1.0"),
        "square_feet": 1400,
        "lot_size_acres": Decimal("0.25"),
        "property_type": "Single Family",
        "status": "active",
    },
    {
        "usda_case_number": "USDA-2026-002",
        "address": "456 Oak Ave",
        "city": "Bremen",
        "state": "IN",
        "zip_code": "46506",
        "county": "Marshall",
        "list_price": Decimal("15075.00"),
        "bedrooms": 4,
        "bathrooms": Decimal("2.0"),
        "square_feet": 1800,
        "lot_size_acres": Decimal("0.50"),
        "property_type": "Single Family",
        "status": "sold",
    },
    {
        "usda_case_number": "USDA-2026-003",
        "address": "789 Pine St",
        "city": "Monroeville",
        "state": "AL",
        "zip_code": "36460",
        "county": "Monroe",
        "list_price": Decimal("1002.00"),
        "bedrooms": 2,
        "bathrooms": Decimal("1.0"),
        "square_feet": 950,
        "lot_size_acres": Decimal("0.33"),
        "property_type": "Single Family",
        "status": "active",
    },
]


def _parse_usda_txt(raw_text: str) -> list[dict[str, Any]]:
    """Parse USDA fixed-width TXT data into structured property records.

    The USDA data.gov feed uses an irregular fixed-width format with
    multiple line types. This parser uses regex patterns to extract
    key fields from the primary data lines.

    Args:
        raw_text: Raw text content of the USDA TXT file.

    Returns:
        List of dicts with fields mapped to UsdaProperty model.
    """
    records: list[dict[str, Any]] = []
    continuation_bids: dict[str, Decimal] = {}

    # First pass: extract opening bid amounts from continuation lines
    bid_pattern = re.compile(r"Opening\s+bid\s+\$?([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
    for bid_match in bid_pattern.finditer(raw_text):
        bid_str = bid_match.group(1).replace(",", "")
        try:
            continuation_bids["_next"] = Decimal(bid_str)
        except Exception:
            pass

    # Second pass: extract property lines
    lines = raw_text.splitlines()
    current_bid: Decimal | None = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check for bid continuation lines
        bid_line_match = re.match(
            r"^(?:Opening\s+(?:bid|Bid)\s+(?:is\s+)?\$?([\d,]+(?:\.\d{2})?))",
            line_stripped,
        )
        if bid_line_match:
            bid_str = bid_line_match.group(1).replace(",", "")
            try:
                current_bid = Decimal(bid_str)
            except Exception:
                current_bid = None
            continue

        # Check for state/county continuation lines
        if re.match(r"^\s{2,}[A-Z]{2}\s+", line_stripped) and len(line_stripped) > 150:
            # Has state abbreviation early in line; likely a continuation
            continue

        # Skip known non-data patterns
        if line_stripped.startswith(
            ("All sales", "******", "N/A", "Property", "At the")
        ):
            continue
        if "sold AS IS" in line_stripped.lower():
            continue
        if "subject to" in line_stripped.lower():
            continue

        # Data lines start with "N" and contain a case number
        if not line_stripped.startswith("N"):
            continue
        if len(line_stripped) < 100:
            continue

        # Extract case number: 6-9 digit number.
        # Case numbers may be concatenated with preceding text
        # (e.g. "at33127221") so avoid leading \b.
        case_match = re.search(r"(\d{6,9})\b", line_stripped)
        if not case_match:
            continue
        case_number = case_match.group(1)

        # Extract bedrooms: single digit after case number area
        bed_match = re.search(re.escape(case_number) + r"\s*(\d)", line_stripped)
        bedrooms = int(bed_match.group(1)) if bed_match else None

        # Extract city: between foundation type and style/state
        # Foundation types: Block, Slab, Poured, Wood, etc.
        city_match = re.search(
            r"(?:Block|Slab|Poured|Wood|Manufact)\s+([A-Z][a-zA-Z\s.-]+?)\s{2,}",
            line_stripped,
        )
        city = city_match.group(1).strip() if city_match else ""

        # Extract state: 2-letter code
        state_match = re.search(r"\b([A-Z]{2})\b", line_stripped[50:])
        state = state_match.group(1) if state_match else ""

        # Extract square footage: 3-5 digit number near end of line
        sqft_match = re.search(r"\b(\d{3,5})\b", line_stripped[80:])
        square_feet = int(sqft_match.group(1)) if sqft_match else None

        # Extract street address: between city area and state
        addr_match = re.search(
            r"\s{4,}([\d]+[\sA-Za-z0-9#./-]+?)\s{2,}",
            line_stripped[60:100],
        )
        address = addr_match.group(1).strip() if addr_match else ""

        # Determine status (default active)
        status = "active"
        if "sold" in line_stripped.lower() or "forced" in line_stripped.lower():
            status = "active"

        property_type = "Single Family"
        if "Ranch" in line_stripped:
            property_type = "Ranch"
        elif "Story" in line_stripped or "Stor" in line_stripped:
            property_type = "Multi-Story"
        elif "Manufact" in line_stripped:
            property_type = "Manufactured"
        elif "Split" in line_stripped:
            property_type = "Split Level"

        record: dict[str, Any] = {
            "usda_case_number": f"USDA-{case_number}",
            "address": address or "Unknown",
            "city": city or "Unknown",
            "state": state or "US",
            "zip_code": "",
            "county": "",
            "list_price": current_bid,
            "bedrooms": bedrooms,
            "bathrooms": None,
            "square_feet": square_feet,
            "lot_size_acres": None,
            "property_type": property_type,
            "status": status,
        }
        records.append(record)
        current_bid = None

    return records


class Command(BaseCommand):
    """Fetch USDA REO properties from data.gov feed and upsert into UsdaProperty."""

    help = (
        "Fetch USDA Rural Development REO properties from data.gov feed, "
        "upsert into UsdaProperty, and mark stale records as removed"
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
            help="Override the data.gov USDA TXT endpoint URL",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: C901
        dry_run = options["dry_run"]
        endpoint = options.get("endpoint") or DEFAULT_ENDPOINT

        # ---- 1. Fetch data ----
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — using embedded fixture data")
            )
            records_data = USDA_FIXTURE_DATA
        else:
            self.stdout.write(f"Fetching USDA data from {endpoint} ...")
            try:
                response = requests.get(endpoint, timeout=30)
                response.raise_for_status()
                records_data = _parse_usda_txt(response.text)
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"HTTP request failed: {exc}"))
                raise

        if not records_data:
            self.stdout.write(self.style.WARNING("No records found in feed."))
            return

        seen_case_numbers: set[str] = set()
        added = 0
        updated = 0
        now = timezone.now()

        # ---- 2. Upsert each record ----
        for item in records_data:
            case_number = item.get("usda_case_number", "")
            if not case_number:
                continue

            seen_case_numbers.add(case_number)

            defaults: dict[str, Any] = {
                "address": item.get("address", ""),
                "city": item.get("city", ""),
                "state": item.get("state", ""),
                "zip_code": item.get("zip_code", ""),
                "county": item.get("county", ""),
                "list_price": item.get("list_price"),
                "bedrooms": item.get("bedrooms"),
                "bathrooms": item.get("bathrooms"),
                "square_feet": item.get("square_feet"),
                "lot_size_acres": item.get("lot_size_acres"),
                "property_type": item.get("property_type", ""),
                "status": item.get("status", "active"),
                "listing_url": item.get("listing_url", ""),
                "description": item.get("description", ""),
                "scraped_at": now,
                "last_seen_at": now,
            }

            obj, created = UsdaProperty.objects.update_or_create(
                usda_case_number=case_number,
                defaults=defaults,
            )

            if created:
                added += 1
            else:
                updated += 1

        # ---- 3. Mark stale records as REMOVED ----
        removed = (
            UsdaProperty.objects.filter(
                status__in=[
                    UsdaProperty.Status.ACTIVE,
                    UsdaProperty.Status.PENDING,
                ],
            )
            .exclude(usda_case_number__in=seen_case_numbers)
            .update(
                status=UsdaProperty.Status.REMOVED,
                last_seen_at=now,
            )
        )

        # ---- 4. Log summary ----
        self.stdout.write(
            self.style.SUCCESS(
                f"Added: {added}, Updated: {updated}, Removed: {removed}"
            )
        )
