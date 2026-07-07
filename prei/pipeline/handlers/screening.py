"""Hyper-fast screening-stage metric evaluator for property pipeline.

Evaluates incoming properties against structural yield bounds using pure
arithmetic functions. Designed for sub-10ms execution per property —
no pandas, no ORM, no external I/O.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ── Configuration model ───────────────────────────────────────────────────────


class ScreeningThresholds(BaseModel):
    """Threshold configuration for the SCREENING pipeline stage.

    All fields are required unless marked optional.
    """

    min_gross_yield: float = Field(
        ..., gt=0, description="Minimum acceptable gross yield (e.g. 0.07 = 7%)"
    )
    max_price_to_rent_ratio: float = Field(
        ..., gt=0, description="Maximum acceptable price-to-rent ratio (e.g. 15.0)"
    )
    excluded_hoas: List[str] = Field(
        default_factory=list, description="HOA names that automatically disqualify"
    )
    min_beds: int = Field(..., ge=0, description="Minimum number of bedrooms")
    min_baths: int = Field(..., ge=0, description="Minimum number of bathrooms")


# ── Pure arithmetic helpers ────────────────────────────────────────────────────


def gross_yield(monthly_rent: float, purchase_price: float) -> float:
    """Compute gross yield as a fraction.

    Formula:
        Gross Yield = (monthly_rent × 12) / purchase_price

    Args:
        monthly_rent: Estimated monthly rent in dollars.
        purchase_price: Total purchase price in dollars.

    Returns:
        Gross yield as a float (e.g. 0.072 for 7.2%).
    """
    if purchase_price <= 0 or monthly_rent <= 0:
        return 0.0
    return (monthly_rent * 12.0) / purchase_price


def price_to_rent_ratio(monthly_rent: float, purchase_price: float) -> float:
    """Compute price-to-rent ratio.

    Formula:
        Price-to-Rent Ratio = purchase_price / (monthly_rent × 12)

    Args:
        monthly_rent: Estimated monthly rent in dollars.
        purchase_price: Total purchase price in dollars.

    Returns:
        Price-to-rent ratio (e.g. 13.8 means 13.8× annual rent).
    """
    annual_rent = monthly_rent * 12.0
    if annual_rent <= 0:
        return float("inf")
    return purchase_price / annual_rent


# ── Composition helper ─────────────────────────────────────────────────────────


def compute_screening_metrics(asset_data: Dict[str, Any]) -> Dict[str, float]:
    """Compute all screening-relevant metrics from raw asset data.

    Args:
        asset_data: Dict containing at least 'estimated_monthly_rent'
                    and 'purchase_price' keys.

    Returns:
        Dict with computed metric names mapped to float values.
    """
    rent = float(asset_data.get("estimated_monthly_rent", 0))
    price = float(asset_data.get("purchase_price", 0))

    return {
        "gross_yield": gross_yield(rent, price),
        "price_to_rent_ratio": price_to_rent_ratio(rent, price),
    }


# ── Top-level evaluator ────────────────────────────────────────────────────────


def evaluate_screening_stage(
    asset_data: Dict[str, Any],
    thresholds: ScreeningThresholds,
) -> Tuple[bool, Optional[str]]:
    """Evaluate a property against all screening thresholds.

    Each check is evaluated in order of lowest computational cost first.
    The first violation short-circuits and returns the kill reason.

    Args:
        asset_data: Property data with keys:
            - estimated_monthly_rent (float)
            - purchase_price (float)
            - beds (int)
            - baths (int)
            - hoa_name (str, optional)
        thresholds: ScreeningThresholds instance with bounds.

    Returns:
        Tuple of (pass: bool, kill_reason: str | None).
        pass=True, kill_reason=None means all checks passed.
        pass=False, kill_reason=<msg> means the property was rejected.
    """
    # ── 1. Beds check (cheapest: dict lookup + int compare) ──────────────
    beds = asset_data.get("beds")
    if beds is not None and int(beds) < thresholds.min_beds:
        return False, (f"Insufficient bedrooms: {beds} < {thresholds.min_beds}")

    # ── 2. Baths check ───────────────────────────────────────────────────
    baths = asset_data.get("baths")
    if baths is not None and float(baths) < thresholds.min_baths:
        return False, (f"Insufficient bathrooms: {baths} < {thresholds.min_baths}")

    # ── 3. HOA exclusion check ───────────────────────────────────────────
    hoa = asset_data.get("hoa_name")
    if hoa and thresholds.excluded_hoas:
        hoa_lower = hoa.strip().lower()
        for excluded in thresholds.excluded_hoas:
            if excluded.strip().lower() == hoa_lower:
                return False, (f"Excluded HOA: {hoa}")

    # ── 4. Gross yield check (two arithmetic ops) ────────────────────────
    rent = asset_data.get("estimated_monthly_rent")
    price = asset_data.get("purchase_price")
    if rent is not None and price is not None and price > 0:
        gy = gross_yield(float(rent), float(price))
        if gy < thresholds.min_gross_yield:
            return False, (
                f"Gross yield too low: {gy:.4f} < {thresholds.min_gross_yield}"
            )

    # ── 5. Price-to-rent ratio check ──────────────────────────────────────
    if rent is not None and price is not None and price > 0 and float(rent) > 0:
        ptr = price_to_rent_ratio(float(rent), float(price))
        if ptr > thresholds.max_price_to_rent_ratio:
            return False, (
                f"Price-to-rent ratio too high: {ptr:.2f} > "
                f"{thresholds.max_price_to_rent_ratio}"
            )

    # ── All checks passed ─────────────────────────────────────────────────
    return True, None
