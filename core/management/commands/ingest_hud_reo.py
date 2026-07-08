"""Management command to ingest HUD REO properties from ArcGIS GeoJSON feed.

Confirmed endpoint (DISC-HG-1, 2026-07-08)
--------------------------------------------
The authoritative HUD REO data source is an ArcGIS Hub Feature Service
published by HUD's eGIS team:

  https://hudgis-hud.opendata.arcgis.com/datasets/a54aff75cc0a42de8456cc36a7335663_3

The data is available as GeoJSON at:
  https://opendata.arcgis.com/api/v3/datasets/a54aff75cc0a42de8456cc36a7335663_3/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1

Fields available in the source:
  CASE_NUM       — FHA case number (→ hud_case_number)
  ADDRESS        — full street address (→ address)
  CITY           — city (→ city)
  STATE_CODE     — 2-letter state code (→ state)
  DISPLAY_ZIP_CODE — ZIP code (→ zip_code)
  DATE_ACQUIRED  — date HUD acquired the property
  DATE_CLOSED    — date property was sold (null = still available)
  MAP_LATITUDE   — latitude (stored in raw_data)
  MAP_LONGITUDE  — longitude (stored in raw_data)

⚠️  The ArcGIS data does NOT include: asking_price, bedrooms, bathrooms,
square_feet, property_type, insured_status, listing_url, or image_url.
These HudProperty fields are left as defaults when not available.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import HudProperty

logger = logging.getLogger("prei.ingestion.hud")

# ═══════════════════════════════════════════════════════════════════════
# Confirmed endpoint (DISC-HG-1, 2026-07-08)
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_ENDPOINT = (
    "https://opendata.arcgis.com/api/v3/datasets/"
    "a54aff75cc0a42de8456cc36a7335663_3/downloads/data"
    "?format=geojson&spatialRefId=4326&where=1%3D1"
)

# ── Fixture data for --dry-run mode ──────────────────────────────────
# Mirrors the ArcGIS GeoJSON FeatureCollection schema.

HUD_FIXTURE_DATA: dict[str, Any] = {
    "type": "FeatureCollection",
    "name": "FHA_Single_Family_REO_Properties_For_Sale",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 1,
                "CASE_NUM": "011-625906",
                "CASE_STEP_NUMBER": 6,
                "STREET_NUM": "12712 ",
                "DIRECTION_PREFIX": None,
                "STREET_NAME": "PLANT RD                      ",
                "CITY": "ALPINE",
                "STATE_CODE": "AL",
                "DISPLAY_ZIP_CODE": 35014,
                "MAP_LATITUDE": 33.370882,
                "MAP_LONGITUDE": -86.323935,
                "DATE_ACQUIRED": "2022-07-29T00:00:00Z",
                "DATE_CLOSED": None,
                "ADDRESS": "12712 PLANT RD                      ",
                "REVITE_NAME": None,
                "REVITE_HOC": None,
            },
            "geometry": {"type": "Point", "coordinates": [-86.323935, 33.370882]},
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 2,
                "CASE_NUM": "011-640353",
                "CASE_STEP_NUMBER": 6,
                "STREET_NUM": "205 ",
                "DIRECTION_PREFIX": None,
                "STREET_NAME": "W CORNELIA ST                 ",
                "CITY": "MARION",
                "STATE_CODE": "AL",
                "DISPLAY_ZIP_CODE": 36756,
                "MAP_LATITUDE": 32.64209,
                "MAP_LONGITUDE": -87.325266,
                "DATE_ACQUIRED": "2022-11-01T00:00:00Z",
                "DATE_CLOSED": None,
                "ADDRESS": "205 W CORNELIA ST                 ",
                "REVITE_NAME": None,
                "REVITE_HOC": None,
            },
            "geometry": {"type": "Point", "coordinates": [-87.325266, 32.64209]},
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 3,
                "CASE_NUM": "011-662347",
                "CASE_STEP_NUMBER": 6,
                "STREET_NUM": "2220 ",
                "DIRECTION_PREFIX": None,
                "STREET_NAME": "E TUSCALOOSA A                ",
                "CITY": "GADSDEN",
                "STATE_CODE": "AL",
                "DISPLAY_ZIP_CODE": 35904,
                "MAP_LATITUDE": 34.028436,
                "MAP_LONGITUDE": -86.03811,
                "DATE_ACQUIRED": "2024-04-16T00:00:00Z",
                "DATE_CLOSED": "2024-10-15T00:00:00Z",
                "ADDRESS": "2220 E TUSCALOOSA A                ",
                "REVITE_NAME": None,
                "REVITE_HOC": None,
            },
            "geometry": {"type": "Point", "coordinates": [-86.03811, 34.028436]},
        },
    ],
}


def _infer_status(properties: dict[str, Any]) -> str:
    """Infer HudProperty.Status from ArcGIS property data.

    - DATE_CLOSED set → property has been sold → SOLD
    - Otherwise → ACTIVE
    """
    date_closed = properties.get("DATE_CLOSED")
    if date_closed is not None:
        return HudProperty.Status.SOLD
    return HudProperty.Status.ACTIVE


def _feature_to_hud_property(
    feature: dict[str, Any],
    scraped_at: datetime,
) -> dict[str, Any]:
    """Convert one GeoJSON feature to HudProperty field defaults dict.

    Maps only fields that exist in the ArcGIS source.  Fields without
    a source counterpart (asking_price, bedrooms, etc.) are left at
    their model defaults (None or "").
    """
    props = feature.get("properties", {})

    # --- Identity ---
    case_number = str(props.get("CASE_NUM", "")).strip()
    address = str(props.get("ADDRESS", "")).strip()
    city = str(props.get("CITY", "")).strip()

    # --- Location ---
    state = str(props.get("STATE_CODE", "")).strip()
    raw_zip = props.get("DISPLAY_ZIP_CODE")
    zip_code = str(raw_zip).strip() if raw_zip is not None else ""

    return {
        "hud_case_number": case_number,
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "asking_price": None,
        "list_price": None,
        "bedrooms": None,
        "bathrooms": None,
        "square_feet": None,
        "property_type": "",
        "status": _infer_status(props),
        "insured_status": "",
        "listing_url": "",
        "image_url": "",
        "description": "",
        "scraped_at": scraped_at,
        "last_seen_at": scraped_at,
    }


class Command(BaseCommand):
    """Fetch HUD REO properties from ArcGIS GeoJSON feed."""

    help = (
        "Fetch HUD REO properties from ArcGIS Hub GeoJSON feed, "
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
            help="Override the ArcGIS GeoJSON endpoint URL",
        )

    def handle(  # noqa: C901
        self,
        *args: Any,
        **options: Any,
    ) -> None:
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
                response = requests.get(endpoint, timeout=60)
                response.raise_for_status()
                raw_data = response.json()
            except requests.RequestException as exc:
                self.stderr.write(self.style.ERROR(f"HTTP request failed: {exc}"))
                raise

        features = raw_data.get("features", []) if isinstance(raw_data, dict) else []
        if not features:
            self.stdout.write(self.style.WARNING("No features found in GeoJSON feed."))
            return

        seen_case_numbers: set[str] = set()
        added = 0
        updated = 0
        now = timezone.now()

        # ---- 2. Upsert each feature ----
        for feature in features:
            props = feature.get("properties", {})
            case_number = str(props.get("CASE_NUM", "")).strip()
            if not case_number:
                continue

            seen_case_numbers.add(case_number)

            defaults = _feature_to_hud_property(feature, now)

            _obj, created = HudProperty.objects.update_or_create(
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
