"""Leasing pipeline service — stage advancement and lifecycle operations.

Mirrors core/services/pipeline.py for the acquisition pipeline but operates
on LeasingPipelineProperty records through the leasing stage sequence.
"""

from __future__ import annotations

from typing import Any


LEASING_STAGE_ORDER: list[str] = [
    "LISTING",
    "SHOWING",
    "APPLICATION",
    "SCREENING",
    "APPROVED",
    "LEASE_SIGNED",
    "MOVE_IN",
    "STABILIZED",
]


def advance_stage(entry: Any) -> Any:
    """Advance a LeasingPipelineProperty to the next sequential stage.

    Raises ValueError if already at STABILIZED or status is not ACTIVE.
    """
    from core.models import LeasingPipelineProperty

    if entry.status != LeasingPipelineProperty.Status.ACTIVE:
        raise ValueError(f"Cannot advance property with status '{entry.status}'")

    current_stage = entry.stage
    try:
        current_idx = LEASING_STAGE_ORDER.index(current_stage)
    except ValueError:
        raise ValueError(f"Unknown stage: {current_stage}")

    if current_stage == "STABILIZED":
        raise ValueError("Cannot advance — already at final stage STABILIZED")

    next_stage = LEASING_STAGE_ORDER[current_idx + 1]
    entry.stage = next_stage
    entry.save(update_fields=["stage", "updated_at"])

    return entry


def mark_filled(entry: Any) -> Any:
    """Mark a leasing property as filled (tenant found)."""
    entry.status = "FILLED"
    entry.save(update_fields=["status", "updated_at"])
    return entry


def put_on_hold(entry: Any) -> Any:
    """Place a leasing property on hold."""
    entry.status = "ON_HOLD"
    entry.save(update_fields=["status", "updated_at"])
    return entry
