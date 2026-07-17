"""On-demand data ingestion for HUD, USDA, and County sources.

Provides functions that can be called from management commands or from
web views (for hosted deployments without CLI access).
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.utils import timezone

logger = logging.getLogger("prei.ingestion")

HUD_GEOJSON_URL = (
    "https://opendata.arcgis.com/api/v3/datasets/"
    "a54aff75cc0a42de8456cc36a7335663_3/downloads/data"
    "?format=geojson&spatialRefId=4326&where=1%3D1"
)

USDA_TXT_URL = "https://www.rd.usda.gov/sites/default/files"
USDA_BASE_URL = "https://www.rd.usda.gov/sites/default/files/reo-listings"

# Cache — ingestion is heavyweight, only needed once
_ingestion_run: set[str] = set()


def ingest_hud_reo() -> dict[str, int]:
    """Download and ingest HUD REO properties from ArcGIS GeoJSON.

    Returns:
        dict with 'created', 'updated', 'skipped' counts.
    """
    from core.models import HudProperty

    if "hud" in _ingestion_run:
        return {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "note": "already ran this session",
        }

    logger.info("Ingesting HUD REO from ArcGIS GeoJSON...")
    resp = requests.get(HUD_GEOJSON_URL, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    now = timezone.now()
    created = updated = skipped = 0
    features = data.get("features", data if isinstance(data, list) else [])

    for feature in features:
        props = feature.get("properties", feature) if isinstance(feature, dict) else {}
        case_num = str(props.get("CASE_NUM") or "").strip()
        if not case_num:
            skipped += 1
            continue

        defaults = {
            "address": str(props.get("ADDRESS") or "").strip(),
            "city": str(props.get("CITY") or "").strip(),
            "state": str(props.get("STATE_CODE") or "").strip()[:2],
            "zip_code": str(props.get("DISPLAY_ZIP_CODE") or "").strip(),
            "county": str(props.get("COUNTY_NAME") or "").strip(),
            "status": "active",
            "scraped_at": now,
            "last_seen_at": now,
        }
        _, was_created = HudProperty.objects.update_or_create(
            hud_case_number=case_num,
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    _ingestion_run.add("hud")
    logger.info(
        "HUD ingestion complete: %d created, %d updated, %d skipped",
        created,
        updated,
        skipped,
    )
    return {"created": created, "updated": updated, "skipped": skipped}


USDA_TXT_URL = (
    "https://www.sc.egov.usda.gov/data/files/Property/FSASFHFOREData9-7-18.txt"
)


def ingest_usda_reo() -> dict[str, int]:
    """Download and ingest USDA REO properties from fixed-width TXT file."""
    from core.models import UsdaProperty

    if "usda" in _ingestion_run:
        return {"created": 0, "updated": 0, "skipped": 0, "note": "already ran"}

    try:
        from core.management.commands.ingest_usda_reo import _parse_usda_txt

        logger.info("Downloading USDA REO data from %s", USDA_TXT_URL)
        resp = requests.get(USDA_TXT_URL, timeout=60)
        resp.raise_for_status()
        records = _parse_usda_txt(resp.text)

        now = timezone.now()
        created = updated = 0
        for rec in records:
            rec["scraped_at"] = now
            rec["last_seen_at"] = now
            _, was_created = UsdaProperty.objects.update_or_create(
                usda_case_number=rec["usda_case_number"],
                defaults=rec,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        _ingestion_run.add("usda")
        logger.info("USDA ingestion: %d created, %d updated", created, updated)
        return {"created": created, "updated": updated, "skipped": 0}
    except Exception as e:
        _ingestion_run.add("usda")
        logger.error("USDA ingestion failed: %s", e)
        return {"created": 0, "updated": 0, "skipped": 0, "error": str(e)}
