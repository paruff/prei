"""Screening service for pipeline property evaluation.

Provides the ScreeningResult dataclass and screen_property() function
that evaluates a PipelineProperty against a user's ScreeningCriteria.
Handles both hard-kill (immediate reject) and soft (score-based) criteria,
with special handling for VrmProperty (has rent data) vs other source types
(no rent data: ForeclosureProperty, HudProperty, UsdaProperty).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Pure screening evaluator (ported from prei.pipeline.handlers.screening) ──


@dataclass
class ScreeningThresholds:
    """Threshold configuration for the SCREENING pipeline stage.

    All fields are required unless marked optional. Float-based because this
    evaluator is transient ratio math (no persistence); the ORM persistence
    path (screen_property/PipelineProperty) is Decimal-based.
    """

    min_gross_yield: float
    max_price_to_rent_ratio: float
    excluded_hoas: list[str] = field(default_factory=list)
    min_beds: int = 0
    min_baths: int = 0


def gross_yield(monthly_rent: float, purchase_price: float) -> float:
    """Compute gross yield as a fraction: (monthly_rent × 12) / purchase_price.

    Returns 0.0 for non-positive price or rent.
    """
    if purchase_price <= 0 or monthly_rent <= 0:
        return 0.0
    return (monthly_rent * 12.0) / purchase_price


def price_to_rent_ratio(monthly_rent: float, purchase_price: float) -> float:
    """Compute price-to-rent ratio: purchase_price / (monthly_rent × 12).

    Returns float('inf') when annual rent is zero.
    """
    annual_rent = monthly_rent * 12.0
    if annual_rent <= 0:
        return float("inf")
    return purchase_price / annual_rent


def compute_screening_metrics(asset_data: dict[str, Any]) -> dict[str, float]:
    """Compute gross_yield and price_to_rent_ratio from raw asset data."""
    rent = float(asset_data.get("estimated_monthly_rent", 0))
    price = float(asset_data.get("purchase_price", 0))
    return {
        "gross_yield": gross_yield(rent, price),
        "price_to_rent_ratio": price_to_rent_ratio(rent, price),
    }


def evaluate_screening_stage(
    asset_data: dict[str, Any],
    thresholds: ScreeningThresholds,
) -> Tuple[bool, Optional[str]]:
    """Evaluate a property against all screening thresholds.

    Checks run in order of lowest computational cost first; the first
    violation short-circuits and returns the kill reason.

    Returns:
        Tuple of (pass: bool, kill_reason: str | None).
    """
    # 1. Beds check
    beds = asset_data.get("beds")
    if beds is not None and int(beds) < thresholds.min_beds:
        return False, f"Insufficient bedrooms: {beds} < {thresholds.min_beds}"

    # 2. Baths check
    baths = asset_data.get("baths")
    if baths is not None and float(baths) < thresholds.min_baths:
        return False, f"Insufficient bathrooms: {baths} < {thresholds.min_baths}"

    # 3. HOA exclusion check
    hoa = asset_data.get("hoa_name")
    if hoa and thresholds.excluded_hoas:
        hoa_lower = hoa.strip().lower()
        for excluded in thresholds.excluded_hoas:
            if excluded.strip().lower() == hoa_lower:
                return False, f"Excluded HOA: {hoa}"

    # 4. Gross yield check
    rent = asset_data.get("estimated_monthly_rent")
    price = asset_data.get("purchase_price")
    if rent is not None and price is not None and price > 0 and float(rent) > 0:
        gy = gross_yield(float(rent), float(price))
        if gy < thresholds.min_gross_yield:
            return (
                False,
                f"Gross yield too low: {gy:.4f} < {thresholds.min_gross_yield}",
            )

    # 5. Price-to-rent ratio check
    if rent is not None and price is not None and price > 0 and float(rent) > 0:
        ptr = price_to_rent_ratio(float(rent), float(price))
        if ptr > thresholds.max_price_to_rent_ratio:
            return (
                False,
                f"Price-to-rent ratio too high: {ptr:.2f} > "
                f"{thresholds.max_price_to_rent_ratio}",
            )

    return True, None


def screen_batch(
    property_dicts: list[dict[str, Any]],
    thresholds: ScreeningThresholds,
) -> dict[str, Any]:
    """Evaluate a batch of property payloads through SCREENING (stats only).

    Pure batch equivalent of the former prei BatchScreeningProcessor: returns
    the same operational summary dict (processed/advanced/killed/execution_time_ms)
    without engine state or persistence.

    Args:
        property_dicts: List of property payload dicts with at minimum
            asset_id, address, estimated_monthly_rent, purchase_price,
            beds, baths keys.
        thresholds: ScreeningThresholds for the evaluator.

    Returns:
        Dict with processed (int), advanced (int), killed (int),
        execution_time_ms (float).
    """
    import time

    start = time.perf_counter()
    advanced = 0
    killed = 0

    for payload in property_dicts:
        asset_data = {
            "estimated_monthly_rent": payload.get("estimated_monthly_rent"),
            "purchase_price": payload.get("purchase_price"),
            "beds": payload.get("beds"),
            "baths": payload.get("baths"),
            "hoa_name": payload.get("hoa_name"),
        }
        passed, _ = evaluate_screening_stage(asset_data, thresholds)
        if passed:
            advanced += 1
        else:
            killed += 1

    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "processed": len(property_dicts),
        "advanced": advanced,
        "killed": killed,
        "execution_time_ms": round(elapsed_ms, 2),
    }


if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from core.models import (
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

    @property
    def kill_reason(self) -> str | None:
        """Return the first hard-failure reason, or None if not killed."""
        return self.hard_failures[0] if self.hard_failures else None

    @property
    def yield_evaluated(self) -> bool:
        """True if gross yield was actually evaluated (not skipped)."""
        for msg in self.passes:
            if "gross yield" in msg.lower():
                if "skipped" in msg.lower():
                    return False
                return True
        for msg in self.soft_failures:
            if "gross yield" in msg.lower():
                return True
        return False

    @property
    def yield_note(self) -> str:
        """Machine-readable note about yield screening outcome."""
        for msg in self.passes:
            if "gross yield" in msg.lower():
                if "skipped" in msg.lower():
                    return "no_rent_estimate"
                return "evaluated"
        for msg in self.soft_failures:
            if "gross yield" in msg.lower():
                return "evaluated"
        return ""


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
    growth_area: Any = None,
) -> tuple[Decimal, Optional[str], Optional[str]]:
    """Evaluate GACS score soft criterion.

    Uses the passed growth_area if available (avoids a DB lookup).
    Falls back to looking up GrowthArea by (state, city) if not provided.

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

    if growth_area is None:
        try:
            from core.models import GrowthArea

            growth_area = GrowthArea.objects.filter(
                state=state, city_name__iexact=city
            ).first()
        except Exception:
            # Broad catch: DB connection failure, import error, etc.
            # Non-critical — screening continues without GACS deduction
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
    cache_rent: bool = True,
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
    monthly_rent = _get_monthly_rent(pipeline_property, source_record, cache_rent)

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
    cache_rent: bool = True,
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

    monthly_rent = _get_monthly_rent(pipeline_property, source_record, cache_rent)

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


def _cache_rent(pipeline_property: Any, rent: Decimal, cache_rent: bool) -> Decimal:
    """Set estimated_rent on pipeline_property and persist it if possible.

    The DB write is skipped when cache_rent is False (e.g. screening_preview's
    documented "without saving" contract) or when pipeline_property has no
    `pk` (e.g. a _PipelineView adapted from a HUD/USDA source, which is never
    a persisted PipelineProperty).
    """
    pipeline_property.estimated_rent = rent
    pk = getattr(pipeline_property, "pk", None)
    if cache_rent and pk:
        PipelineProperty.objects.filter(pk=pk).update(estimated_rent=rent)
    return rent


def _get_monthly_rent(
    pipeline_property: PipelineProperty,
    source_record: Any | None,
    cache_rent: bool = True,
) -> Decimal | None:
    """Get monthly rent from source_record, PipelineProperty, or market APIs.

    Priority: source_record (VRM) > PipelineProperty.estimated_rent >
              Rentometer (real comps) > HUD FMR > None.

    The fallback chain tries real rent data first (Rentometer), then falls
    back to HUD FMR when Rentometer is unavailable.

    Args:
        cache_rent: When False, a fetched rent is still returned but not
            persisted to the DB — used by screening_preview(), which promises
            not to save anything.
    """
    # 1. Prefer source_record (VRM has actual rent data)
    if (
        source_record is not None
        and _is_vrm_source(source_record)
        and hasattr(source_record, "projected_monthly_rent")
    ):
        rent = source_record.projected_monthly_rent  # type: ignore[union-attr]
        if rent is not None and rent > 0:
            return Decimal(str(rent))

    # 2. PipelineProperty.estimated_rent (user-entered or previously cached)
    if (
        pipeline_property.estimated_rent is not None
        and pipeline_property.estimated_rent > 0
    ):
        return Decimal(str(pipeline_property.estimated_rent))

    # 3. Try Rentometer (real rent comps) — best data source
    zip_code = _extract_zip(source_record, pipeline_property)
    bedrooms = pipeline_property.beds
    # Use getattr for safety — some callers pass _PipelineView proxies
    address = getattr(pipeline_property, "address", None)
    city = getattr(pipeline_property, "city", None)
    state = getattr(pipeline_property, "state", None)

    if zip_code and address and city and state:
        try:
            from core.integrations.market.rentometer import get_rent_estimate

            rent = get_rent_estimate(
                zip_code=zip_code,
                address=address,
                city=city,
                state=state,
                bedrooms=int(bedrooms) if bedrooms else 2,
            )
            if rent is not None and rent > 0:
                return _cache_rent(pipeline_property, rent, cache_rent)
        except Exception:
            logger.warning(
                "Rentometer lookup failed for zip=%s", zip_code, exc_info=True
            )

    # 4. Fallback: HUD Fair Market Rent
    if zip_code:
        try:
            from core.integrations.market.hud_fmr import (  # type: ignore[assignment]
                get_rent_estimate,
            )

            rent = get_rent_estimate(
                zip_code=zip_code, bedrooms=int(bedrooms) if bedrooms else 2
            )
            if rent is not None and rent > 0:
                return _cache_rent(pipeline_property, rent, cache_rent)
        except Exception:
            logger.warning("HUD FMR lookup failed for zip=%s", zip_code, exc_info=True)

    return None


def _extract_zip(source_record: Any | None, pipeline_property: Any) -> str | None:
    """Extract ZIP code from source_record or pipeline_property."""
    if source_record is not None and hasattr(source_record, "zip_code"):
        zip_code = str(source_record.zip_code) if source_record.zip_code else None  # type: ignore[union-attr]
        if zip_code:
            return zip_code

    # Check PipelineProperty.zip_code directly
    if hasattr(pipeline_property, "zip_code") and pipeline_property.zip_code:
        return str(pipeline_property.zip_code)

    if pipeline_property.address:
        import re

        # Anchor to the end (optionally with a ZIP+4 suffix) so a 5-digit
        # street number earlier in the address isn't mistaken for the ZIP,
        # e.g. "12345 Main St, Austin, TX 78701" must match 78701, not 12345.
        m = re.search(r"(\d{5})(?:-\d{4})?\s*$", pipeline_property.address.strip())
        if m:
            return m.group(1)

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


def _is_source_model(obj: Any) -> bool:
    """Check if *obj* is a HUD/USDA source model (not a PipelineProperty).

    Detects by checking for source-specific unique field names.
    """
    class_name = obj.__class__.__name__ if obj is not None else ""
    return (
        class_name in ("HudProperty", "UsdaProperty")
        or hasattr(obj, "hud_case_number")
        or hasattr(obj, "usda_case_number")
    )


def _adapt_source_to_pipeline(
    source: Any,
) -> Any:
    """Create a namespace object with PipelineProperty-like fields from a HUD/USDA source.

    Maps source-model fields to the attribute names that ``screen_property``
    expects on ``pipeline_property``.
    """

    class _PipelineView:
        # No `pk` — this is never a persisted PipelineProperty, so callers
        # must not assume `.pk` exists (see cache_rent guard in
        # _get_monthly_rent).
        price: Decimal | None = None
        estimated_rent: Decimal | None = None
        beds: int | None = None
        year_built: int | None = None
        address: str | None = None
        city: str | None = None
        state: str | None = None

    view = _PipelineView()

    if hasattr(source, "asking_price") and source.asking_price is not None:
        view.price = Decimal(str(source.asking_price))
    elif hasattr(source, "list_price") and source.list_price is not None:
        view.price = Decimal(str(source.list_price))

    if hasattr(source, "bedrooms") and source.bedrooms is not None:
        view.beds = int(source.bedrooms)

    # Address/city/state so Rentometer's address-based lookup (step 3 of
    # _get_monthly_rent) also runs for HUD/USDA sources, not just VRM.
    view.address = getattr(source, "address", None)
    view.city = getattr(source, "city", None)
    view.state = getattr(source, "state", None)

    return view


def screen_property(
    pipeline_property: Any,
    criteria: ScreeningCriteria,
    source_record: Any | None = None,
    growth_area: Any | None = None,
    cache_rent: bool = True,
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
      - If source_record is a ForeclosureProperty, HudProperty, UsdaProperty,
        or None, criteria 6 and 7 are skipped because no rent estimate is
        available.
      - If *pipeline_property* is a HUD or USDA source model (not a
        PipelineProperty), it is treated as the source_record and relevant
        fields (price, beds) are extracted from it.
      - Missing fields on PP or source_record → skip criterion,
        add 'SKIPPED: {criterion} — no data' to passes list.

    Args:
        pipeline_property: PipelineProperty or source model (HudProperty,
                           UsdaProperty) being evaluated.
        criteria:          ScreeningCriteria with user's thresholds.
        source_record:     Optional source model instance for additional data.
        cache_rent:        When False, a Rentometer/HUD FMR rent lookup is
                           still used for scoring but not persisted to the
                           DB — pass False from preview/dry-run callers.

    Returns:
        ScreeningResult with pass/fail, final score, and diagnostic lists.
    """
    passes: list[str] = []
    notes: list[str] = []

    # ── Detect source model passed as first argument ───────────────────────
    if _is_source_model(pipeline_property):
        source_record = pipeline_property
        pipeline_property = _adapt_source_to_pipeline(source_record)

    # ── Extract data ──────────────────────────────────────────────────────
    state = _extract_state(pipeline_property, source_record)
    city = _extract_city(pipeline_property, source_record)
    foreclosure_status = _extract_foreclosure_status(source_record)
    property_type = _extract_property_type(source_record)
    has_rent_data = _is_vrm_source(source_record) or (
        getattr(pipeline_property, "estimated_rent", None) is not None
        and getattr(pipeline_property, "estimated_rent", Decimal("0")) > 0
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
    ded, pass_msg, fail_msg = _eval_gacs_score(
        pipeline_property, criteria, state, city, growth_area
    )
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # 6. Gross yield
    ded, pass_msg, fail_msg = _eval_gross_yield(
        pipeline_property, criteria, source_record, cache_rent
    )
    score -= ded
    if pass_msg:
        passes.append(pass_msg)
    if fail_msg:
        soft_failures.append(fail_msg)

    # 7. Price-to-rent ratio
    ded, pass_msg, fail_msg = _eval_price_to_rent_ratio(
        pipeline_property, criteria, source_record, cache_rent
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
