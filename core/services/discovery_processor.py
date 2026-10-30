"""Dedup-aware discovery ingestion for the DISCOVERY stage.

Ported from prei.pipeline.handlers.discovery_processor (pydantic removed).
Provides two layers:

- ``process_discovery_batch`` — pure stats/dedup pass over raw listings,
  returns the same analytics contract the prei DiscoveryProcessor exposed
  (total_received/new_assets_discovered/duplicates_skipped/failed_records/
  payloads). No persistence — used by stats-only view bridges.
- ``process_discovery`` — persists one canonical payload as a
  PipelineProperty at DISCOVERED stage, deduplicated by address_hash
  (per user, source_type). This is the Django-state write path.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from core.services.discovery import CanonicalPropertyPayload, DiscoverySanitizer

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from core.models import PipelineProperty


# ── Stats-only batch pass (preserves prei DiscoveryProcessor contract) ────────


def process_discovery_batch(
    raw_listings: list[dict[str, Any]],
    source_name: str,
    existing_hashes: set[str] | None = None,
) -> dict[str, Any]:
    """Process a batch of raw listings through dedup (no persistence).

    Each listing is:
      1. Normalised via DiscoverySanitizer.transform_input()
      2. Checked for address_hash collision against existing_hashes
      3. If duplicate → counted and skipped
      4. If new → canonical payload collected, hash added

    Args:
        raw_listings: List of raw property data dicts from an external
                      source (MLS, county records, wholesale JSON, etc.).
        source_name: Human-readable source label (e.g. "mls_feed").
        existing_hashes: Set of SHA-256 address hashes already known.
                         A fresh set is used if not provided.

    Returns:
        Analytics dict:
            total_received        (int): Raw count of input records.
            new_assets_discovered (int): New (non-duplicate) records.
            duplicates_skipped    (int): Records rejected by hash match.
            failed_records        (int): Records that raised during parsing.
            payloads              (list): CanonicalPropertyPayload list.
    """
    # Mutate the caller's set in place when provided (prei DiscoveryProcessor
    # contract: existing_hashes is updated after each batch so callers can
    # share one set across sources).
    hashes = existing_hashes if existing_hashes is not None else set()
    new_payloads: list[CanonicalPropertyPayload] = []
    duplicates_count = 0
    errors_count = 0

    for raw in raw_listings:
        try:
            canonical = DiscoverySanitizer.transform_input(raw, source_name)
            if canonical.address_hash in hashes:
                duplicates_count += 1
                continue
            new_payloads.append(canonical)
            hashes.add(canonical.address_hash)
        except Exception:
            errors_count += 1
            continue

    return {
        "total_received": len(raw_listings),
        "new_assets_discovered": len(new_payloads),
        "duplicates_skipped": duplicates_count,
        "failed_records": errors_count,
        "payloads": new_payloads,
    }


# ── Django persistence path ───────────────────────────────────────────────────


def process_discovery(
    payload: CanonicalPropertyPayload,
    user: User,
    source_type: str,
) -> PipelineProperty:
    """Persist a canonical payload as a PipelineProperty at DISCOVERED stage.

    Deduplicates by address_hash across the user's existing pipeline
    properties of the same source_type. If a property with the same
    address_hash already exists, it is returned unchanged (created=False
    semantics — caller checks ``created`` on the returned object via the
    PipelineProperty.created flag if needed).

    Args:
        payload: CanonicalPropertyPayload from DiscoverySanitizer.
        user: Django User who owns this pipeline entry.
        source_type: PipelineProperty.SourceType value.

    Returns:
        PipelineProperty instance (created or existing).
    """
    from core.models import PipelineProperty

    existing = (
        PipelineProperty.objects.filter(
            user=user,
            source_type=source_type,
            address_hash=payload.address_hash,
        )
        .order_by("-updated_at")
        .first()
    )
    if existing is not None:
        return existing

    return PipelineProperty.objects.create(
        user=user,
        source_type=source_type,
        source_id=payload.source_id,
        address=payload.raw_address,
        address_hash=payload.address_hash,
        stage=PipelineProperty.Stage.DISCOVERED,
        status=PipelineProperty.Status.ACTIVE,
        price=Decimal(str(payload.price)) if payload.price is not None else None,
        estimated_rent=Decimal(str(payload.estimated_rent))
        if payload.estimated_rent is not None
        else None,
        beds=payload.beds or None,
        baths=payload.baths or None,
        sqft=payload.sqft,
        year_built=payload.year_built,
        discovered_at=timezone.now(),
    )
