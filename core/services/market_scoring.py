"""Market scoring: Price-to-Rent ratio and overall market score.

Computes market-level metrics from Property entries and cached MarketSnapshot
data. Does NOT make live API calls — uses only data already in the system.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone


def _q2(val: Decimal) -> Decimal:
    """Quantize to 2 decimal places."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Default weights for score_market(snapshot) composite scoring
# ---------------------------------------------------------------------------

_DEFAULT_MARKET_SCORE_WEIGHTS: dict[str, Decimal] = {
    "price_to_rent": Decimal("0.25"),
    "landlord_friendliness": Decimal("0.25"),
    "employment_diversity": Decimal("0.20"),
    "population_growth": Decimal("0.15"),
    "rent_growth": Decimal("0.15"),
}


def _get_market_score_weights() -> dict[str, Decimal]:
    """Return market score weights, falling back to defaults for invalid entries."""
    from django.conf import settings

    configured = getattr(settings, "MARKET_SCORE_WEIGHTS", None)
    if not isinstance(configured, dict):
        return dict(_DEFAULT_MARKET_SCORE_WEIGHTS)

    result = dict(_DEFAULT_MARKET_SCORE_WEIGHTS)
    for key in _DEFAULT_MARKET_SCORE_WEIGHTS:
        if key in configured:
            try:
                result[key] = Decimal(str(configured[key]))
            except Exception:
                pass  # fall back to default
    return result


# ---------------------------------------------------------------------------
# score_market — snapshot-based composite scoring (tests expect this API)
# ---------------------------------------------------------------------------


def score_market(snapshot_or_zip):
    """Compute a market score — polymorphic API.

    Accepts either:
        - A MarketSnapshot instance → returns a Decimal score in [0, 100].
        - A zip code string         → returns a dict with market data and score.

    When a string is provided, the function queries the database for the
    latest MarketSnapshot and Property entries for that ZIP and returns
    a detailed dict.  When a MarketSnapshot instance is provided, it
    computes a weighted composite score directly from the snapshot's fields.

    Raises:
        ValueError: If snapshot_or_zip is None.
    """
    # --- String (zip code) path → dict ----------------------------------------
    if isinstance(snapshot_or_zip, str):
        return score_market_by_zip(snapshot_or_zip)

    # --- None guard -----------------------------------------------------------
    if snapshot_or_zip is None:
        raise ValueError("snapshot cannot be None")

    # --- MarketSnapshot path → Decimal ----------------------------------------
    return _score_market_from_snapshot(snapshot_or_zip)


def _score_market_from_snapshot(snapshot) -> Decimal:
    """Compute composite score from a MarketSnapshot instance.

    Returns a Decimal in [0, 100] computed as a weighted average of
    normalised sub-scores for each available signal.
    """
    from investor_app.finance.utils import (
        clamp_market_score,
        normalize_market_growth_rate_score,
        normalize_market_price_to_rent_score,
    )

    weights = _get_market_score_weights()

    # Build list of (sub_score, weight) for available signals
    scored_components: list[tuple[Decimal, Decimal]] = []

    # Price-to-rent ratio
    if snapshot.price_to_rent_ratio is not None:
        sub = normalize_market_price_to_rent_score(snapshot.price_to_rent_ratio)
        scored_components.append((sub, weights["price_to_rent"]))

    # Landlord friendliness (already 0-100)
    if snapshot.landlord_friendliness_score is not None:
        scored_components.append(
            (
                snapshot.landlord_friendliness_score,
                weights["landlord_friendliness"],
            )
        )

    # Employment diversity (already 0-100)
    if snapshot.employment_diversity_score is not None:
        scored_components.append(
            (
                snapshot.employment_diversity_score,
                weights["employment_diversity"],
            )
        )

    # Population growth
    if snapshot.population_growth_rate is not None:
        sub = normalize_market_growth_rate_score(snapshot.population_growth_rate)
        scored_components.append((sub, weights["population_growth"]))

    # Rent growth
    if snapshot.rent_growth_rate is not None:
        sub = normalize_market_growth_rate_score(snapshot.rent_growth_rate)
        scored_components.append((sub, weights["rent_growth"]))

    if not scored_components:
        return Decimal("0")

    total_weight = sum(w for _, w in scored_components)
    if total_weight == 0:
        return Decimal("0")

    weighted_sum = sum(s * w for s, w in scored_components)
    raw = weighted_sum / total_weight
    return clamp_market_score(raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# update_market_scores — batch update MarketSnapshot.market_score
# ---------------------------------------------------------------------------


def update_market_scores(zip_codes: list[str]) -> int:
    """Recompute and persist market_score for each ZIP code.

    Args:
        zip_codes: List of ZIP code strings to update.

    Returns:
        Number of MarketSnapshot records updated.
    """
    from core.models import MarketSnapshot

    updated = 0
    for zip_code in zip_codes:
        snapshots = MarketSnapshot.objects.filter(zip_code=zip_code, area_type="zip")
        for snapshot in snapshots:
            snapshot.market_score = _score_market_from_snapshot(snapshot)
            snapshot.save(update_fields=["market_score"])
            updated += 1
    return updated


# ---------------------------------------------------------------------------
# Legacy helpers (used by views, scoring service, etc.)
# ---------------------------------------------------------------------------


def calculate_price_to_rent_ratio(
    median_home_price: Decimal,
    median_monthly_rent: Decimal,
) -> Decimal:
    """Calculate the Price-to-Rent ratio for a market.

    P/R = median_home_price / (median_monthly_rent * 12)

    Lower is better for cashflow investors. Rule of thumb:
        < 12: strong cashflow market
        12–16: moderate
        16–20: borderline
        > 20: appreciation market, not cashflow

    Args:
        median_home_price: Median home price in the market (must be > 0).
        median_monthly_rent: Median monthly rent in the market (must be > 0).

    Returns:
        Price-to-rent ratio as a Decimal.

    Raises:
        ValueError: If either input is <= 0.
    """
    hp = median_home_price
    mr = median_monthly_rent

    if hp <= 0:
        raise ValueError(f"median_home_price must be > 0 (received {hp})")
    if mr <= 0:
        raise ValueError(f"median_monthly_rent must be > 0 (received {mr})")

    annual_rent = mr * Decimal(12)
    return _q2(hp / annual_rent)


def _pr_verdict(pr_ratio: Decimal) -> str:
    """Return a human-readable verdict for a Price-to-Rent ratio.

    Bands:
        < 12  : "Strong"   — strong cashflow market
        12–16 : "Moderate" — moderate cashflow potential
        16–20 : "Borderline" — borderline, needs careful analysis
        > 20  : "Weak"     — appreciation market, not cashflow
    """
    if pr_ratio < 12:
        return "Strong"
    elif pr_ratio < 16:
        return "Moderate"
    elif pr_ratio <= 20:
        return "Borderline"
    else:
        return "Weak"


def score_market_by_zip(zip_code: str) -> dict:
    """Compute an overall market score for a ZIP code.

    Uses cached MarketSnapshot data and Property entries already in the
    database. Does NOT make live API calls.

    The overall_score (0–100) is a weighted composite of:
        - Price-to-Rent ratio     : 40%  (lower is better)
        - Unemployment rate       : 20%  (lower is better)
        - Population growth (5yr) : 20%  (higher is better)
        - Data freshness          : 20%  (fresher is better)

    Args:
        zip_code: 5-digit ZIP code to evaluate.

    Returns:
        dict with keys:
            zip_code (str)
            price_to_rent_ratio (Decimal or None)
            price_to_rent_verdict (str): "Strong" / "Moderate" / "Borderline" / "Weak" / "Unknown"
            unemployment_rate (Decimal or None)
            population_growth_pct_5yr (Decimal or None)
            overall_score (int): 0–100
            data_freshness_days (int or None): days since MarketSnapshot.fetched_at
    """
    from core.models import MarketSnapshot, Property

    result = {
        "zip_code": zip_code,
        "price_to_rent_ratio": None,
        "price_to_rent_verdict": "Unknown",
        "unemployment_rate": None,
        "population_growth_pct_5yr": None,
        "overall_score": 0,
        "data_freshness_days": None,
    }

    # ── Get MarketSnapshot for this ZIP ───────────────────────────────────────
    try:
        snapshot = (
            MarketSnapshot.objects.filter(zip_code=zip_code, area_type="zip")
            .order_by("-fetched_at")
            .first()
        )
    except MarketSnapshot.DoesNotExist:
        snapshot = None

    if snapshot is None:
        return result

    # ── Data freshness ────────────────────────────────────────────────────────
    if snapshot.fetched_at:
        days_old = (timezone.now() - snapshot.fetched_at).days
        result["data_freshness_days"] = days_old

    # ── Price-to-Rent ratio ───────────────────────────────────────────────────
    # Try to compute from Property data for this ZIP
    properties = Property.objects.filter(
        zip_code=zip_code,
        purchase_price__gt=0,
        monthly_rent_gross__gt=0,
    )

    if properties.exists():
        from django.db.models import Avg

        agg = properties.aggregate(
            avg_price=Avg("purchase_price"),
            avg_rent=Avg("monthly_rent_gross"),
        )
        avg_price = agg["avg_price"]
        avg_rent = agg["avg_rent"]

        if avg_price and avg_rent and avg_rent > 0:
            pr = calculate_price_to_rent_ratio(avg_price, avg_rent)
            result["price_to_rent_ratio"] = pr
            result["price_to_rent_verdict"] = _pr_verdict(pr)
    elif snapshot.price_to_rent_ratio is not None:
        # Fall back to stored value on MarketSnapshot
        result["price_to_rent_ratio"] = snapshot.price_to_rent_ratio
        result["price_to_rent_verdict"] = _pr_verdict(snapshot.price_to_rent_ratio)

    # ── Unemployment rate ─────────────────────────────────────────────────────
    if snapshot.unemployment_rate is not None:
        result["unemployment_rate"] = snapshot.unemployment_rate

    # ── Population growth ─────────────────────────────────────────────────────
    if snapshot.population_growth_pct_5yr is not None:
        result["population_growth_pct_5yr"] = snapshot.population_growth_pct_5yr

    # ── Overall score (0–100) ─────────────────────────────────────────────────
    scores: list[int] = []

    # 1. Price-to-Rent (40%)
    pr = result["price_to_rent_ratio"]
    if pr is not None:
        if pr < 12:
            pr_score = 100
        elif pr < 16:
            # Linear scale: 12→100, 16→60
            pr_score = int(100 - ((pr - 12) / 4) * 40)
        elif pr <= 20:
            # Linear scale: 16→60, 20→20
            pr_score = int(60 - ((pr - 16) / 4) * 40)
        else:
            # Linear scale: 20→20, 30→0
            pr_score = max(0, int(20 - ((pr - 20) / 10) * 20))
        scores.append(("pr", pr_score, 40))

    # 2. Unemployment rate (20%)
    ur = result["unemployment_rate"]
    if ur is not None:
        ur_pct = ur * 100  # convert fraction to percentage
        if ur_pct <= 3:
            ur_score = 100
        elif ur_pct <= 6:
            ur_score = int(100 - ((ur_pct - 3) / 3) * 50)
        elif ur_pct <= 10:
            ur_score = int(50 - ((ur_pct - 6) / 4) * 50)
        else:
            ur_score = 0
        scores.append(("ur", ur_score, 20))

    # 3. Population growth (20%)
    pg = result["population_growth_pct_5yr"]
    if pg is not None:
        pg_pct = pg * 100  # convert fraction to percentage
        if pg_pct >= 2:
            pg_score = 100
        elif pg_pct >= 0:
            pg_score = int(50 + (pg_pct / 2) * 50)
        elif pg_pct >= -2:
            pg_score = int((2 + pg_pct) / 2 * 50)
        else:
            pg_score = 0
        scores.append(("pg", pg_score, 20))

    # 4. Data freshness (20%)
    days = result["data_freshness_days"]
    if days is not None:
        if days <= 7:
            fresh_score = 100
        elif days <= 30:
            fresh_score = int(100 - ((days - 7) / 23) * 30)
        elif days <= 90:
            fresh_score = int(70 - ((days - 30) / 60) * 70)
        else:
            fresh_score = 0
        scores.append(("fresh", fresh_score, 20))

    # Compute weighted average
    if scores:
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(s * w for _, s, w in scores)
        result["overall_score"] = (
            int(weighted_sum / total_weight) if total_weight > 0 else 0
        )
    else:
        result["overall_score"] = 0

    return result


# Keep backward-compatible alias for views that import score_market by name
# and expect the zip-based dict API.
def score_market_compat(zip_code: str) -> dict:  # noqa: D401
    """Alias for score_market_by_zip used by views."""
    return score_market_by_zip(zip_code)
