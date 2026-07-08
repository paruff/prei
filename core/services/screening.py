"""Screening service for pipeline property evaluation.

Provides the ScreeningResult dataclass and screen_property() function
that evaluates a PipelineProperty against a user's ScreeningCriteria.
Handles both hard-kill (immediate reject) and soft (score-based) criteria,
with special handling for VrmProperty (has rent data) vs ForeclosureProperty
(no rent data) source types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from core.models import (
        GrowthArea,
        PipelineProperty,
        ScreeningCriteria,
    )


# ── Constants ──────────────────────────────────────────────────────────────────

# Score deduction weights for soft criteria failures.
# Each is the maximum points deducted when the criterion is fully violated.
# Proportional deduction is applied — e.g. 10% below threshold = 10% of max.
GACS_DEDUCTION_MAX = Decimal("20")  # Up to 20 pts for GACS shortfall
YIELD_DEDUCTION_MAX = Decimal("15")  # Up to 15 pts for yield below min
PTR_DEDUCTION_MAX = Decimal("10")  # Up to 10 pts for PTR above max
YEAR_BUILT_DEDUCTION = Decimal("5")  # Fixed 5 pts for property too old
BEDS_DEDUCTION_PER_UNIT = Decimal("5")  # 5 pts per bed outside range, max 10


# ── Public dataclass ───────────────────────────────────────────────────────────


@dataclass
class ScreeningResult:
    """Result of evaluating a PipelineProperty against ScreeningCriteria.

    Attributes:
        passed:       True if no hard failures AND final score >= 50.
        score:       Final score 0-100 (Decimal). Starts at 100, soft failures
                     deduct proportionally.
        hard_failures:  List of reasons that caused an immediate kill
                        (empty if no hard failures).
        soft_failures:  List of reasons for score deductions
                        (non-fatal, but reduce score).
        passes:      List of criteria that were checked and passed, or were
                     skipped due to missing data.
        notes:       Free-text notes about any exceptional conditions
                     (e.g. "Yield screening skipped — no rent data").
    """

    passed: bool = True
    score: Decimal = Decimal("100")
    hard_failures: list[str] = field(default_factory=list)
    soft_failures: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    notes: str = ""


def _kill_result(reason: str) -> ScreeningResult:
    """Helper to construct a killed ScreeningResult."""
    return ScreeningResult(
        passed=False,
        score=Decimal("0"),
        hard_failures=[reason],
    )


def _fail_result(reason: str, score: Decimal, passes: list[str]) -> ScreeningResult:
    """Helper for a failed result with soft failures (score < 50)."""
    return ScreeningResult(
        passed=False,
        score=max(Decimal("0"), score),
        soft_failures=[reason],
        passes=passes,
    )


# ── Data extraction helpers ───────────────────────────────────────────────────


def _extract_state(
    pipeline_property: PipelineProperty,
    source_record: Any | None,
) -> str | None:
    """Extract state from source_record, or None."""
    if source_record is not None:
        return getattr(source_record, "state", None)
    return None


def _extract_city(
    pipeline_property: PipelineProperty,
    source_record: Any | None,
) -> str | None:
    """Extract city from source_record, or None."""
    if source_record is not None:
        return getattr(source_record, "city", None)
    return None


def _extract_foreclosure_status(
    source_record: Any | None,
) -> str | None:
    """Extract foreclosure_status from source_record if it has one."""
    if source_record is not None:
        return getattr(source_record, "foreclosure_status", None)
    return None


def _extract_property_type(
    source_record: Any | None,
) -> str | None:
    """Extract property_type from source_record if it has one."""
    if source_record is not None:
        return getattr(source_record, "property_type", None) or None
    return None


def _is_vrm_source(source_record: Any | None) -> bool:
    """Check if source_record is a VrmProperty (has rent data)."""
    if source_record is None:
        return False
    return source_record.__class__.__name__ == "VrmProperty" or hasattr(
        source_record, "projected_monthly_rent"
    )


# ── Soft criterion evaluators ─────────────────────────────────────────────────


def _eval_gacs_score(
    pipeline_property: PipelineProperty,
    criteria: ScreeningCriteria,
    state: str | None,
    city: str | None,
) -> tuple[Decimal, Optional[str], Optional[str]]:
    """Evaluate GACS score soft criterion.

    Looks up GrowthArea by (state, city). If found and the property's
    market score is below the user's minimum, deducts proportionally.

    Returns:
        Tuple of (deduction, pass_msg, fail_msg).
        pass_msg is set if the criterion was skipped or passed.
        fail_msg is set if there was a deduction.
    """
    if criteria.min_gacs_score is None:
        return Decimal("0"), "GACS score screening skipped — no minimum set", None

    if not state or not city:
        return (
            Decimal("0"),
            "GACS score screening skipped — no state/city data available",
            None,
        )

    try:
        from core.models import GrowthArea

        growth_area: GrowthArea | None = GrowthArea.objects.filter(
            state=state, city_name__iexact=city
        ).first()
    except Exception:
        growth_area = None

    if growth_area is None or growth_area.composite_score is None:
        return (
            Decimal("0"),
            f"GACS score screening skipped — no GrowthArea found for {city}, {state}",
            None,
        )

    actual = growth_area.composite_score
    minimum = criteria.min_gacs_score

    if actual >= minimum:
        return (
            Decimal("0"),
            f"GACS score {actual} >= {minimum} (min)",
            None,
        )

    # Proportional deduction: shortfall relative to minimum
    if minimum > 0:
        shortfall_pct = (minimum - actual) / minimum
    else:
        shortfall_pct = Decimal("1")
    deduction = (GACS_DEDUCTION_MAX * shortfall_pct).quantize(Decimal("0.01"))
    deduction = min(deduction, GACS_DEDUCTION_MAX)

    return (
        deduction,
        None,
        f"GACS score {actual} below minimum {minimum} — deduct {deduction} pts",
    )


def _eval_gross_yield(
    pipeline_property: PipelineProperty,
    criteria: ScreeningCriteria,
    source_record: Any | None,
) -> tuple[Decimal, Optional[str], Optional[str]]:
    """Evaluate gross yield soft criterion.

    Formula: gross_yield_pct = (annual_rent / price) * 100
    Uses projected_monthly_rent from VrmProperty or estimated_rent from
    PipelineProperty.

    Returns:
        Tuple of (deduction, pass_msg, fail_msg).
    """
    if criteria.min_gross_yield_pct is None:
        return Decimal("0"), "Gross yield screening skipped — no minimum set", None

    # Determine if we have rent data
    monthly_rent = _get_monthly_rent(pipeline_property, source_record)

    if monthly_rent is None or monthly_rent <= 0:
        return (
            Decimal("0"),
            "Gross yield screening skipped — no rent estimate available",
            None,
        )

    price = pipeline_property.price
    if price is None or price <= 0:
        return Decimal("0"), "Gross yield screening skipped — no price available", None

    annual_rent = monthly_rent * Decimal("12")
    gross_yield_pct = (annual_rent / price) * Decimal("100")
    minimum_pct = criteria.min_gross_yield_pct

    if gross_yield_pct >= minimum_pct:
        return (
            Decimal("0"),
            f"Gross yield {gross_yield_pct:.2f}% >= {minimum_pct}% (min)",
            None,
        )

    # Proportional deduction
    if minimum_pct > 0:
        shortfall_pct = (minimum_pct - gross_yield_pct) / minimum_pct
    else:
        shortfall_pct = Decimal("1")
    deduction = (YIELD_DEDUCTION_MAX * shortfall_pct).quantize(Decimal("0.01"))
    deduction = min(deduction, YIELD_DEDUCTION_MAX)

    return (
        deduction,
        None,
        f"Gross yield {gross_yield_pct:.2f}% below minimum {minimum_pct}%"
        f" — deduct {deduction} pts",
    )


def _eval_price_to_rent_ratio(
    pipeline_property: PipelineProperty,
    criteria: ScreeningCriteria,
    source_record: Any | None,
) -> tuple[Decimal, Optional[str], Optional[str]]:
    """Evaluate price-to-rent ratio soft criterion.

    Formula: ptr = price / monthly_rent

    Returns:
        Tuple of (deduction, pass_msg, fail_msg).
    """
    if criteria.max_price_to_rent_ratio is None:
        return (
            Decimal("0"),
            "Price-to-rent ratio screening skipped — no max set",
            None,
        )

    monthly_rent = _get_monthly_rent(pipeline_property, source_record)

    if monthly_rent is None or monthly_rent <= 0:
        return (
            Decimal("0"),
            "Price-to-rent ratio screening skipped — no rent estimate available",
            None,
        )

    price = pipeline_property.price
    if price is None or price <= 0:
        return (
            Decimal("0"),
            "Price-to-rent ratio screening skipped — no price available",
            None,
        )

    ptr = price / monthly_rent
    max_ratio = criteria.max_price_to_rent_ratio

    if ptr <= max_ratio:
        return (
            Decimal("0"),
            f"Price-to-rent ratio {ptr:.2f} <= {max_ratio} (max)",
            None,
        )

    # Proportional deduction: how much we exceed the max ratio
    if max_ratio > 0:
        excess_pct = (ptr - max_ratio) / max_ratio
    else:
        excess_pct = Decimal("1")
    deduction = (PTR_DEDUCTION_MAX * excess_pct).quantize(Decimal("0.01"))
    deduction = min(deduction, PTR_DEDUCTION_MAX)

    return (
        deduction,
        None,
        f"Price-to-rent ratio {ptr:.2f} above maximum {max_ratio}"
        f" — deduct {deduction} pts",
    )


def _get_monthly_rent(
    pipeline_property: PipelineProperty,
    source_record: Any | None,
) -> Decimal | None:
    """Get monthly rent from source_record or PipelineProperty.

    Prefers source_record (VrmProperty.projected_monthly_rent) over
    PipelineProperty.estimated_rent. Returns None if neither available.
    """
    if (
        source_record is not None
        and _is_vrm_source(source_record)
        and hasattr(source_record, "projected_monthly_rent")
    ):
        rent = source_record.projected_monthly_rent  # type: ignore[union-attr]
        if rent is not None and rent > 0:
            return Decimal(str(rent))

    if (
        pipeline_property.estimated_rent is not None
        and pipeline_property.estimated_rent > 0
    ):
        return Decimal(str(pipeline_property.estimated_rent))

    return None


def _eval_year_built(
    pipeline_property: PipelineProperty,
    criteria: ScreeningCriteria,
) -> tuple[Decimal, Optional[str], Optional[str]]:
    """Evaluate year-built soft criterion.

    If the property was built before max_year_built, deducts fixed points.

    Returns:
        Tuple of (deduction, pass_msg, fail_msg).
    """
    if criteria.max_year_built is None:
        return Decimal("0"), "Year-built screening skipped — no max set", None

    year_built = pipeline_property.year_built
    if year_built is None:
        return (
            Decimal("0"),
            "Year-built screening skipped — no year_built data available",
            None,
        )

    if year_built >= criteria.max_year_built:
        return (
            Decimal("0"),
            f"Year built {year_built} >= {criteria.max_year_built} (max cutoff)",
            None,
        )

    return (
        YEAR_BUILT_DEDUCTION,
        None,
        f"Year built {year_built} older than cutoff {criteria.max_year_built}"
        f" — deduct {YEAR_BUILT_DEDUCTION} pts",
    )


def _eval_beds(
    pipeline_property: PipelineProperty,
    criteria: ScreeningCriteria,
) -> tuple[Decimal, Optional[str], Optional[str]]:
    """Evaluate beds soft criterion.

    Checks min_beds and max_beds. Each bed outside range deducts
    BEDS_DEDUCTION_PER_UNIT, capped at 10 points.

    Returns:
        Tuple of (deduction, pass_msg, fail_msg).
    """
    beds = pipeline_property.beds
    if beds is None:
        return Decimal("0"), "Beds screening skipped — no beds data available", None

    deduction = Decimal("0")

    if criteria.min_beds is not None and beds < criteria.min_beds:
        shortfall = criteria.min_beds - beds
        bed_deduction = min(
            BEDS_DEDUCTION_PER_UNIT * Decimal(str(shortfall)),
            Decimal("10"),
        )
        deduction += bed_deduction
        fail = (
            f"Beds {beds} below minimum {criteria.min_beds}"
            f" — deduct {bed_deduction} pts"
        )
        return deduction, None, fail

    if criteria.max_beds is not None and beds > criteria.max_beds:
        excess = beds - criteria.max_beds
        bed_deduction = min(
            BEDS_DEDUCTION_PER_UNIT * Decimal(str(excess)),
            Decimal("10"),
        )
        deduction += bed_deduction
        fail = (
            f"Beds {beds} above maximum {criteria.max_beds}"
            f" — deduct {bed_deduction} pts"
        )
        return deduction, None, fail

    bounds = f"in [{criteria.min_beds}"
    bounds += f", {criteria.max_beds}]" if criteria.max_beds is not None else ", ∞]"
    return Decimal("0"), f"Beds {beds} {bounds} (within range)", None


# ── Public API ─────────────────────────────────────────────────────────────────


def get_or_create_criteria(user: User) -> Any:
    """Get or create ScreeningCriteria for a user.

    Args:
        user: Django User model instance.

    Returns:
        ScreeningCriteria instance for the given user.
    """
    from core.models import ScreeningCriteria as ScreeningCriteriaModel

    criteria, _ = ScreeningCriteriaModel.objects.get_or_create(user=user)
    return criteria


def screen_property(
    pipeline_property: PipelineProperty,
    criteria: ScreeningCriteria,
    source_record: Any | None = None,
) -> ScreeningResult:
    """Evaluate a PipelineProperty against ScreeningCriteria.

    Hard criteria (evaluated first, immediate kill on any failure):
      1. State filter
      2. Property type filter
      3. Price range
      4. Foreclosure status filter

    Soft criteria (reduce score from 100, do not kill individually):
      5. GACS score (GrowthArea lookup by state+city)
      6. Gross yield (needs rent data — VrmProperty only)
      7. Price-to-rent ratio (needs rent data — VrmProperty only)
      8. Year built
      9. Beds

    Special handling:
      - If source_record is a ForeclosureProperty or None, criteria 6 and 7
        are skipped because no rent estimate is available.
      - Missing fields on PP or source_record → skip criterion,
        add 'SKIPPED: {criterion} — no data' to passes list.

    Args:
        pipeline_property: PipelineProperty instance being evaluated.
        criteria:          ScreeningCriteria with user's thresholds.
        source_record:     Optional source model instance (VrmProperty,
                          ForeclosureProperty, etc.) for additional data.

    Returns:
        ScreeningResult with pass/fail, final score, and diagnostic lists.
    """
    passes: list[str] = []
    notes: list[str] = []

    # ── Extract data ──────────────────────────────────────────────────────
    state = _extract_state(pipeline_property, source_record)
    city = _extract_city(pipeline_property, source_record)
    foreclosure_status = _extract_foreclosure_status(source_record)
    property_type = _extract_property_type(source_record)
    has_rent_data = _is_vrm_source(source_record) or (
        pipeline_property.estimated_rent is not None
        and pipeline_property.estimated_rent > 0
    )

    if not has_rent_data and source_record is not None:
        notes.append(
            "Yield and PTR screening skipped — no rent estimate available "
            "for this source type (confirmed: no Rentcast integration)"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # HARD KILL CRITERIA — evaluated in order, return immediately on failure
    # ═══════════════════════════════════════════════════════════════════════

    # 1. State filter
    if criteria.allowed_states:
        if not state:
            return _kill_result(
                "State filter enabled but property has no state data — KILLED"
            )
        if state not in criteria.allowed_states:
            return _kill_result(
                f"State '{state}' not in allowed states: "
                f"{', '.join(criteria.allowed_states)}"
            )
    passes.append(f"State '{state}' is allowed")

    # 2. Property type filter
    if criteria.allowed_property_types:
        pt = property_type
        if pt and pt not in criteria.allowed_property_types:
            return _kill_result(
                f"Property type '{pt}' not in allowed types: "
                f"{', '.join(criteria.allowed_property_types)}"
            )
        if not pt:
            passes.append(
                "SKIPPED: Property type check — no property_type data available"
            )
        else:
            passes.append(f"Property type '{pt}' is allowed")

    # 3. Price range
    price = pipeline_property.price
    if price is not None:
        if criteria.max_price is not None and price > criteria.max_price:
            return _kill_result(
                f"Price ${price:,.2f} exceeds max ${criteria.max_price:,.2f}"
            )
        if criteria.min_price is not None and price < criteria.min_price:
            return _kill_result(
                f"Price ${price:,.2f} below min ${criteria.min_price:,.2f}"
            )
        passes.append(
            f"Price ${price:,.2f} within range"
            f" [{criteria.min_price or 0}, {criteria.max_price or '∞'}]"
        )
    else:
        passes.append("SKIPPED: Price range check — no price data available")

    # 4. Foreclosure status filter
    if criteria.allowed_foreclosure_statuses:
        if not foreclosure_status:
            passes.append(
                "SKIPPED: Foreclosure status check — "
                "no foreclosure_status data available"
            )
        elif foreclosure_status not in criteria.allowed_foreclosure_statuses:
            return _kill_result(
                f"Foreclosure status '{foreclosure_status}' not in allowed: "
                f"{', '.join(criteria.allowed_foreclosure_statuses)}"
            )
        else:
            passes.append(f"Foreclosure status '{foreclosure_status}' is allowed")

    # ═══════════════════════════════════════════════════════════════════════
    # SOFT CRITERIA — each deducts from score, none kills individually
    # ═══════════════════════════════════════════════════════════════════════

    score = Decimal("100")
    soft_failures: list[str] = []

    # 5. GACS score
    ded, pass_msg, fail_msg = _eval_gacs_score(pipeline_property, criteria, state, city)
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # 6. Gross yield
    ded, pass_msg, fail_msg = _eval_gross_yield(
        pipeline_property, criteria, source_record
    )
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # 7. Price-to-rent ratio
    ded, pass_msg, fail_msg = _eval_price_to_rent_ratio(
        pipeline_property, criteria, source_record
    )
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # 8. Year built
    ded, pass_msg, fail_msg = _eval_year_built(pipeline_property, criteria)
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # 9. Beds
    ded, pass_msg, fail_msg = _eval_beds(pipeline_property, criteria)
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # ── Finalize ──────────────────────────────────────────────────────────
    score = max(Decimal("0"), score.quantize(Decimal("0.01")))

    passed = len(soft_failures) == 0 or score >= Decimal("50")

    return ScreeningResult(
        passed=passed,
        score=score,
        hard_failures=[],
        soft_failures=soft_failures,
        passes=passes,
        notes="; ".join(notes) if notes else "",
    )
