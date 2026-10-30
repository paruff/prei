"""Parse and upsert VRM property records from the JSON export format."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from core.models import VrmProperty

logger = logging.getLogger(__name__)

_ACRES_TO_SF = Decimal("43560")

_STATUS_MAP = {
    "for sale": VrmProperty.Status.FOR_SALE,
    "coming soon": VrmProperty.Status.COMING_SOON,
    "pending": VrmProperty.Status.PENDING,
    "sold": VrmProperty.Status.SOLD,
}


def _normalize_status(raw: str) -> str:
    return _STATUS_MAP.get(raw.strip().lower(), VrmProperty.Status.FOR_SALE)


def _normalize_lot_size_sf(lot_size: Any, lot_size_source: str) -> int | None:
    """Convert lot_size + lot_size_source to integer square feet."""
    if lot_size is None:
        return None
    try:
        value = Decimal(str(lot_size))
    except InvalidOperation:
        return None

    source = (lot_size_source or "").strip().lower()
    if source in {"ac", "acre", "acres"}:
        return int(value * _ACRES_TO_SF)
    # "SF", "sf", or anything else: treat as square feet already
    try:
        return int(value)
    except ValueError, ArithmeticError:
        return None


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None


def _to_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except TypeError, ValueError:
        return None


def parse_vrm_json_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map one VRM JSON record to a dict of VrmProperty field values.

    Returns a dict suitable for VrmProperty.objects.update_or_create().
    Raises ValueError if required fields (asset_id, url) are missing.
    """
    asset_id = record.get("asset_id")
    if asset_id is None:
        raise ValueError("Record missing required field: asset_id")
    url = record.get("url") or ""
    if not url:
        raise ValueError("Record missing required field: url")

    is_auction = bool(record.get("is_auction", False))
    listing_type = (
        VrmProperty.ListingType.ONLINE_AUCTION
        if is_auction
        else VrmProperty.ListingType.TRADITIONAL
    )

    return {
        "vrm_property_id": int(asset_id),
        "vrm_listing_url": url,
        "address": (record.get("address") or "").strip().title(),
        "city": (record.get("city") or "").strip().title(),
        "state": (record.get("state") or "").strip().upper(),
        "zip_code": str(record.get("zip") or "").strip(),
        "county": (record.get("county") or None),
        "list_price": _to_decimal(record.get("list_price")),
        "square_feet": _to_int(record.get("sqft")),
        "bedrooms": _to_int(record.get("bedrooms")),
        "bathrooms": _to_decimal(record.get("bathrooms")),
        "lot_size_sf": _normalize_lot_size_sf(
            record.get("lot_size"), record.get("lot_size_source", "SF")
        ),
        "property_type": record.get("property_type") or None,
        "status": _normalize_status(record.get("status") or ""),
        "listing_type": listing_type,
        "vendee_eligible": bool(record.get("is_vendee_financing", False)),
    }


def upsert_vrm_records(
    records: list[dict[str, Any]],
) -> tuple[int, int, list[str]]:
    """Parse and upsert a list of VRM JSON records.

    Returns (created_count, updated_count, errors) where errors is a list of
    human-readable strings describing any records that could not be imported.
    """
    now = timezone.now()
    created = 0
    updated = 0
    errors: list[str] = []

    for idx, record in enumerate(records):
        try:
            fields = parse_vrm_json_record(record)
        except ValueError as exc:
            logger.warning("VRM import: record %d failed validation: %s", idx, exc)
            # Derive a safe user-facing message from the record, not from the exception
            missing_fields = [f for f in ("asset_id", "url") if not record.get(f)]
            user_msg = (
                "missing required field: " + missing_fields[0]
                if missing_fields
                else "validation error"
            )
            errors.append(f"Record {idx}: {user_msg}")
            continue

        vrm_id = fields.pop("vrm_property_id")
        existing_scraped_at = (
            VrmProperty.objects.filter(vrm_property_id=vrm_id)
            .values_list("scraped_at", flat=True)
            .first()
        )
        fields["scraped_at"] = existing_scraped_at or now
        fields["last_seen_at"] = now

        _, was_created = VrmProperty.objects.update_or_create(
            vrm_property_id=vrm_id,
            defaults=fields,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated, errors
