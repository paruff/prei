"""Pipeline lifecycle service for property acquisition workflow.

Provides the authoritative operations for advancing, killing, holding,
and reactivating PipelineProperty records. Also handles creation from
source models (VRM, Foreclosure) and conversion to Property records.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Tuple

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    pass


# ── Stage order ────────────────────────────────────────────────────────────────

STAGE_ORDER: list[str] = [
    "DISCOVERED",
    "SCREENING",
    "UNDERWRITING",
    "OFFER",
    "DUE_DILIGENCE",
    "CLOSING",
    "ACQUIRED",
    "RENOVATION",
    "STABILIZED",
]

# Map stage value → timestamp field name on PipelineProperty
STAGE_TIMESTAMP_FIELD: dict[str, str] = {
    "DISCOVERED": "discovered_at",
    "SCREENING": "screening_at",
    "UNDERWRITING": "underwriting_at",
    "OFFER": "offer_at",
    "DUE_DILIGENCE": "due_diligence_at",
    "CLOSING": "closing_at",
    "ACQUIRED": "acquired_at",
    "RENOVATION": "renovation_at",
    "STABILIZED": "stabilized_at",
}


# ── Stage helpers ──────────────────────────────────────────────────────────────


def _get_stage_index(stage: str) -> int:
    """Get the index of a stage in STAGE_ORDER."""
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        raise ValueError(f"Unknown stage: {stage}")


# ── Core lifecycle operations ──────────────────────────────────────────────────


def advance_stage(pipeline_property: Any) -> Any:
    """Advance a PipelineProperty to the next sequential stage.

    Sets the corresponding stage timestamp and saves with update_fields.
    Raises ValueError if the property is KILLED, ON_HOLD, or at STABILIZED.

    Args:
        pipeline_property: PipelineProperty instance to advance.

    Returns:
        The same PipelineProperty instance (updated in place, caller
        should refresh from DB if needed).

    Raises:
        ValueError: If status is KILLED or ON_HOLD, or if already at STABILIZED.
    """
    from core.models import PipelineProperty

    if pipeline_property.status in (
        PipelineProperty.Status.KILLED,
        PipelineProperty.Status.ON_HOLD,
    ):
        raise ValueError(
            f"Cannot advance property with status '{pipeline_property.status}'"
        )

    current_stage = pipeline_property.stage
    current_idx = _get_stage_index(current_stage)

    if current_stage == "STABILIZED":
        raise ValueError("Cannot advance — already at final stage STABILIZED")

    next_stage = STAGE_ORDER[current_idx + 1]
    next_timestamp_field = STAGE_TIMESTAMP_FIELD[next_stage]

    setattr(pipeline_property, next_timestamp_field, timezone.now())
    pipeline_property.stage = next_stage

    update_fields = ["stage", next_timestamp_field, "updated_at"]
    pipeline_property.save(update_fields=update_fields)

    return pipeline_property


def kill_property(
    pipeline_property: Any,
    reason: str,
) -> Any:
    """Kill a PipelineProperty — sets status=KILLED and records the reason.

    Args:
        pipeline_property: PipelineProperty instance to kill.
        reason: Human-readable reason for the kill.

    Returns:
        The same PipelineProperty instance.
    """
    pipeline_property.status = "KILLED"
    pipeline_property.kill_reason = reason
    pipeline_property.save(update_fields=["status", "kill_reason", "updated_at"])

    return pipeline_property


def hold_property(
    pipeline_property: Any,
    reason: str = "",
) -> Any:
    """Place a PipelineProperty on hold.

    Sets status=ON_HOLD. The property stays at its current stage.

    Args:
        pipeline_property: PipelineProperty instance to hold.
        reason: Optional reason for the hold.

    Returns:
        The same PipelineProperty instance.
    """
    pipeline_property.status = "ON_HOLD"
    if reason:
        pipeline_property.kill_reason = reason
    pipeline_property.save(update_fields=["status", "kill_reason", "updated_at"])

    return pipeline_property


def reactivate_property(pipeline_property: Any) -> Any:
    """Reactivate a KILLED or ON_HOLD property.

    Sets status=ACTIVE at its current stage. Does NOT advance the stage.

    Args:
        pipeline_property: PipelineProperty instance to reactivate.

    Returns:
        The same PipelineProperty instance.
    """
    pipeline_property.status = "ACTIVE"
    pipeline_property.save(update_fields=["status", "updated_at"])

    return pipeline_property


# ── Source record resolution ───────────────────────────────────────────────────


def get_source_record(pipeline_property: Any) -> Any | None:
    """Resolve the source model instance for a PipelineProperty.

    Maps source_type to the corresponding model and looks up by source_id.

    Supported source types:
        - vrm        → VrmProperty (by vrm_property_id)
        - foreclosure → ForeclosureProperty (by property_id)
        - listing    → Listing (by id / pk)

    Returns:
        Model instance, or None if source_type is 'manual' or unrecognised.
    """
    from core.models import ForeclosureProperty, VrmProperty

    source_type = pipeline_property.source_type
    source_id = pipeline_property.source_id

    if source_type == "vrm":
        try:
            return VrmProperty.objects.get(vrm_property_id=int(source_id))
        except VrmProperty.DoesNotExist, ValueError:
            return None

    if source_type == "foreclosure":
        try:
            return ForeclosureProperty.objects.get(property_id=source_id)
        except ForeclosureProperty.DoesNotExist:
            return None

    if source_type == "listing":
        from core.models import Listing

        try:
            return Listing.objects.get(pk=int(source_id))
        except Listing.DoesNotExist, ValueError:
            return None

    return None


# ── Creation from source models ────────────────────────────────────────────────


def create_from_vrm(
    vrm_property: Any,
    user: Any,
    growth_area: Any | None = None,
) -> Tuple[Any, bool]:
    """Create a PipelineProperty from a VrmProperty and run screening.

    Denormalizes key fields from the VrmProperty, runs screen_property()
    immediately, and sets stage=SCREENING (screening already executed).

    Args:
        vrm_property: VrmProperty instance.
        user: Django User who owns this pipeline entry.
        growth_area: Optional GrowthArea this property was discovered under.

    Returns:
        Tuple of (PipelineProperty, created). created=False if a PP
        already exists for this (user, vrm) combination.
    """
    from core.models import PipelineProperty, ScreeningCriteria
    from core.services.screening import screen_property

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)

    pp, created = PipelineProperty.objects.get_or_create(
        user=user,
        source_type=PipelineProperty.SourceType.VRM,
        source_id=str(vrm_property.vrm_property_id),
        defaults={
            "address": vrm_property.address or "",
            "address_hash": "",
            "city": vrm_property.city or "",
            "state": vrm_property.state or "",
            "zip_code": vrm_property.zip_code or "",
            "county": vrm_property.county or "",
            "growth_area": growth_area,
            "stage": PipelineProperty.Stage.DISCOVERED,
            "status": PipelineProperty.Status.ACTIVE,
            "price": vrm_property.list_price,
            "estimated_rent": vrm_property.projected_monthly_rent,
            "beds": vrm_property.bedrooms,
            "year_built": vrm_property.year_built,
            "discovered_at": timezone.now(),
        },
    )

    if not created:
        return pp, False

    # Run screening immediately
    result = screen_property(pp, criteria, source_record=vrm_property)

    pp.screening_passed = result.passed
    pp.screening_at = timezone.now()
    pp.stage = PipelineProperty.Stage.SCREENING
    pp.save(
        update_fields=[
            "screening_passed",
            "screening_at",
            "stage",
            "updated_at",
        ]
    )

    # Notify user if the property passed screening
    if pp.screening_passed:
        _notify_if_growth_area_match(pp, user, None)

    return pp, True


def create_from_foreclosure(
    foreclosure_property: Any,
    user: Any,
    growth_area: Any | None = None,
) -> Tuple[Any, bool]:
    """Create a PipelineProperty from a ForeclosureProperty and run screening.

    Same pattern as create_from_vrm. ForeclosureProperty has no rent data,
    so yield/PTR screening criteria will be skipped (see screen_property).

    Args:
        foreclosure_property: ForeclosureProperty instance.
        user: Django User who owns this pipeline entry.
        growth_area: Optional GrowthArea this property was discovered under.

    Returns:
        Tuple of (PipelineProperty, created).
    """
    from core.models import PipelineProperty, ScreeningCriteria
    from core.services.screening import screen_property

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)

    pp, created = PipelineProperty.objects.get_or_create(
        user=user,
        source_type=PipelineProperty.SourceType.FORECLOSURE,
        source_id=foreclosure_property.property_id,
        defaults={
            "address": foreclosure_property.street or "",
            "address_hash": "",
            "city": foreclosure_property.city or "",
            "state": foreclosure_property.state or "",
            "zip_code": foreclosure_property.zip_code or "",
            "county": foreclosure_property.county or "",
            "growth_area": growth_area,
            "stage": PipelineProperty.Stage.DISCOVERED,
            "status": PipelineProperty.Status.ACTIVE,
            "price": foreclosure_property.opening_bid,
            "beds": foreclosure_property.bedrooms,
            "year_built": foreclosure_property.year_built,
            "discovered_at": timezone.now(),
        },
    )

    if not created:
        return pp, False

    # Run screening immediately
    result = screen_property(pp, criteria, source_record=foreclosure_property)

    pp.screening_passed = result.passed
    pp.screening_at = timezone.now()
    pp.stage = PipelineProperty.Stage.SCREENING
    pp.save(
        update_fields=[
            "screening_passed",
            "screening_at",
            "stage",
            "updated_at",
        ]
    )

    # Notify user if the property passed screening
    if pp.screening_passed:
        _notify_if_growth_area_match(pp, user, None)

    return pp, True


def create_from_hud(
    hud_property: Any,
    user: Any,
    growth_area: Any | None = None,
) -> Tuple[Any, bool]:
    """Create a PipelineProperty from a HudProperty and run screening.

    Same pattern as create_from_vrm. HudProperty has no rent data,
    so yield/PTR criteria are skipped during screening.

    Args:
        hud_property: HudProperty instance.
        user: Django User who owns this pipeline entry.
        growth_area: Optional GrowthArea this property was discovered under.

    Returns:
        Tuple of (PipelineProperty, created).
    """
    from core.models import HudProperty, PipelineProperty, ScreeningCriteria
    from core.services.screening import screen_property

    if not isinstance(hud_property, HudProperty):
        raise TypeError("Expected HudProperty instance")

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)

    price = hud_property.asking_price or hud_property.list_price

    pp, created = PipelineProperty.objects.get_or_create(
        user=user,
        source_type=PipelineProperty.SourceType.HUD,
        source_id=str(hud_property.hud_case_number),
        defaults={
            "address": hud_property.address or "",
            "address_hash": "",
            "city": hud_property.city or "",
            "state": hud_property.state or "",
            "zip_code": hud_property.zip_code or "",
            "county": hud_property.county or "",
            "growth_area": growth_area,
            "stage": PipelineProperty.Stage.DISCOVERED,
            "status": PipelineProperty.Status.ACTIVE,
            "price": price,
            "estimated_rent": None,
            "beds": hud_property.bedrooms,
            "year_built": None,
            "discovered_at": timezone.now(),
        },
    )

    if not created:
        return pp, False

    # Run screening immediately
    result = screen_property(pp, criteria, source_record=hud_property)

    pp.screening_passed = result.passed
    pp.screening_at = timezone.now()
    pp.stage = PipelineProperty.Stage.SCREENING
    pp.save(
        update_fields=[
            "screening_passed",
            "screening_at",
            "stage",
            "updated_at",
        ]
    )

    # Notify user if the property passed screening
    if pp.screening_passed:
        _notify_if_growth_area_match(pp, user, None)

    return pp, True


def create_from_usda(
    usda_property: Any,
    user: Any,
    growth_area: Any | None = None,
) -> Tuple[Any, bool]:
    """Create a PipelineProperty from a UsdaProperty and run screening.

    Same pattern as create_from_hud. UsdaProperty has no rent data,
    so yield/PTR criteria are skipped during screening.

    Args:
        usda_property: UsdaProperty instance.
        user: Django User who owns this pipeline entry.
        growth_area: Optional GrowthArea this property was discovered under.

    Returns:
        Tuple of (PipelineProperty, created).
    """
    from core.models import PipelineProperty, ScreeningCriteria, UsdaProperty
    from core.services.screening import screen_property

    if not isinstance(usda_property, UsdaProperty):
        raise TypeError("Expected UsdaProperty instance")

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)

    pp, created = PipelineProperty.objects.get_or_create(
        user=user,
        source_type=PipelineProperty.SourceType.USDA,
        source_id=str(usda_property.usda_case_number),
        defaults={
            "address": usda_property.address or "",
            "address_hash": "",
            "city": usda_property.city or "",
            "state": usda_property.state or "",
            "zip_code": usda_property.zip_code or "",
            "county": usda_property.county or "",
            "growth_area": growth_area,
            "stage": PipelineProperty.Stage.DISCOVERED,
            "status": PipelineProperty.Status.ACTIVE,
            "price": usda_property.list_price,
            "estimated_rent": None,
            "beds": usda_property.bedrooms,
            "year_built": None,
            "discovered_at": timezone.now(),
        },
    )

    if not created:
        return pp, False

    # Run screening immediately
    result = screen_property(pp, criteria, source_record=usda_property)

    pp.screening_passed = result.passed
    pp.screening_at = timezone.now()
    pp.stage = PipelineProperty.Stage.SCREENING
    pp.save(
        update_fields=[
            "screening_passed",
            "screening_at",
            "stage",
            "updated_at",
        ]
    )

    # Notify user if the property passed screening
    if pp.screening_passed:
        _notify_if_growth_area_match(pp, user, None)

    return pp, True


def create_from_county_notice(
    county_notice: Any,
    user: Any,
    growth_area: Any | None = None,
) -> Tuple[Any, bool]:
    """Create a PipelineProperty from a CountyForeclosureNotice and run screening.

    Handles both ATTOM preforeclosure data (stored as CountyForeclosureNotice)
    and county-scraped notices. No rent data available for these sources,
    so yield/PTR criteria are skipped during screening.

    Args:
        county_notice: CountyForeclosureNotice instance.
        user: Django User who owns this pipeline entry.
        growth_area: Optional GrowthArea this property was discovered under.

    Returns:
        Tuple of (PipelineProperty, created).
    """
    from core.models import CountyForeclosureNotice, PipelineProperty, ScreeningCriteria
    from core.services.screening import screen_property

    if not isinstance(county_notice, CountyForeclosureNotice):
        raise TypeError("Expected CountyForeclosureNotice instance")

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)

    pp, created = PipelineProperty.objects.get_or_create(
        user=user,
        source_type=PipelineProperty.SourceType.COUNTY,
        source_id=str(county_notice.case_number),
        defaults={
            "address": county_notice.address or "",
            "address_hash": "",
            "city": county_notice.city or "",
            "state": county_notice.state or "",
            "zip_code": county_notice.zip_code or "",
            "county": county_notice.county or "",
            "growth_area": growth_area,
            "stage": PipelineProperty.Stage.DISCOVERED,
            "status": PipelineProperty.Status.ACTIVE,
            "price": county_notice.unpaid_balance,
            "estimated_rent": None,
            "beds": None,
            "year_built": None,
            "discovered_at": timezone.now(),
        },
    )

    if not created:
        return pp, False

    # Run screening immediately
    result = screen_property(pp, criteria, source_record=county_notice)

    pp.screening_passed = result.passed
    pp.screening_at = timezone.now()
    pp.stage = PipelineProperty.Stage.SCREENING
    pp.save(
        update_fields=[
            "screening_passed",
            "screening_at",
            "stage",
            "updated_at",
        ]
    )

    # Notify user if the property passed screening
    if pp.screening_passed:
        _notify_if_growth_area_match(pp, user, None)

    return pp, True


# ── Conversion to Property record ──────────────────────────────────────────────


def convert_to_property_record(
    pipeline_property: Any,
    closing_date: Any = None,
) -> Any:
    """Convert a PipelineProperty to a Property record (post-acquisition).

    Creates a Property model instance from pipeline data, sets the FK
    back-reference, and marks the pipeline property as ACQUIRED.

    Runs within a transaction.atomic() block.

    Args:
        pipeline_property: PipelineProperty at CLOSING or ACQUIRED stage.
        closing_date: Optional date of closing (defaults to now).

    Returns:
        The newly created Property instance.

    Raises:
        ValueError: If the pipeline property already has a property_record.
    """
    from core.models import Property as PropertyModel

    if pipeline_property.property_record_id is not None:
        raise ValueError(
            "PipelineProperty already converted — "
            f"Property record #{pipeline_property.property_record_id} exists"
        )

    now = timezone.now()
    closing = closing_date or now

    source_record = get_source_record(pipeline_property)

    with transaction.atomic():
        prop = PropertyModel.objects.create(
            user=pipeline_property.user,
            address=pipeline_property.address,
            city=getattr(source_record, "city", "") or "",
            state=getattr(source_record, "state", "") or "",
            zip_code=getattr(source_record, "zip_code", "") or "",
            purchase_price=pipeline_property.price or Decimal("0"),
            purchase_date=closing if hasattr(closing, "strftime") else now,
            bedrooms=pipeline_property.beds or 0,
            sqft=int(pipeline_property.sqft) if pipeline_property.sqft else 0,
            property_type="SFR",
            monthly_rent_gross=pipeline_property.estimated_rent or Decimal("0"),
        )

        pipeline_property.property_record = prop
        pipeline_property.status = "ACQUIRED"
        pipeline_property.stage = "ACQUIRED"
        pipeline_property.acquired_at = now
        pipeline_property.save(
            update_fields=[
                "property_record",
                "status",
                "stage",
                "acquired_at",
                "updated_at",
            ]
        )

    return prop


def _notify_if_growth_area_match(
    pipeline_property: Any,
    user: Any,
    source_record: Any | None = None,
) -> None:
    """Create a notification if the property matches a user's growth area.

    Called after a new PipelineProperty passes screening.  Silently
    handles missing notification service or preferences.
    """
    try:
        from core.services.notifications import notify_pipeline_match

        notify_pipeline_match(user, pipeline_property, source_record)
    except Exception as exc:
        import logging

        logging.getLogger("prei.pipeline").warning(
            "Failed to send pipeline notification: %s", exc
        )
