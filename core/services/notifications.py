"""Notification service — creates in-app notifications for pipeline events.

When a property passes screening and matches a user's growth areas,
a notification is created. Email/SMS delivery requires additional
infrastructure (Celery, email backend, SMS provider).
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def notify_pipeline_match(
    user: Any,
    pipeline_property: Any,
    source_record: Any | None = None,
) -> bool:
    """Create an in-app notification when a property matches screening.

    Checks the user's ``NotificationPreference`` before creating. Only
    creates in-app notifications for now (email/SMS requires external
    integration).

    Args:
        user: Django User who owns the pipeline property.
        pipeline_property: PipelineProperty instance that passed screening.
        source_record: The source model (VrmProperty, HudProperty, etc.)

    Returns:
        True if a notification was created, False otherwise.
    """
    from core.models import Notification, NotificationPreference

    prefs, _ = NotificationPreference.objects.get_or_create(user=user)

    if not prefs.notify_in_app:
        return False

    growth_areas = _find_matching_growth_areas(pipeline_property, source_record)

    if not growth_areas:
        return False

    address = pipeline_property.address or "Unknown address"
    score = pipeline_property.gacs_score
    score_str = f" (GACS: {score})" if score else ""

    Notification.objects.create(
        user=user,
        notification_type="pipeline_match",
        priority="medium",
        title=f"New property matching growth area: {address[:60]}",
        body=(
            f"A property at {address} passed screening{score_str} and "
            f"matches your growth area: {growth_areas[0].city_name}, "
            f"{growth_areas[0].state}. Review it in your pipeline."
        ),
        url="/pipeline/review/",
        data={
            "pipeline_property_id": pipeline_property.pk,
            "growth_area": growth_areas[0].city_name,
            "state": growth_areas[0].state,
            "gacs_score": str(score) if score else None,
        },
    )
    logger.info(
        "Created pipeline_match notification for user=%s, property=%s",
        user,
        pipeline_property.pk,
    )
    return True


def _find_matching_growth_areas(
    pipeline_property: Any,
    source_record: Any | None = None,
) -> list[Any]:
    """Find growth areas matching the property's location.

    Uses the source_record's state and city if available, otherwise
    falls back to PipelineProperty address parsing.
    """
    from core.models import GrowthArea

    state = None
    city = None

    if source_record is not None:
        state = getattr(source_record, "state", None)
        city = getattr(source_record, "city", None)

    if not state and pipeline_property.address:
        # Try to extract state from address
        import re

        m = re.search(r"\b([A-Z]{2})\b", pipeline_property.address)
        if m:
            state = m.group(1)

    if not state:
        return []

    qs = GrowthArea.objects.filter(state=state)
    if city:
        qs = qs.filter(city_name__iexact=city)

    return list(qs[:5])
