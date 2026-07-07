"""Tests for the screening-stage metric evaluator."""

import pytest

from prei.pipeline.handlers.screening import (
    ScreeningThresholds,
    compute_screening_metrics,
    evaluate_screening_stage,
    gross_yield,
    price_to_rent_ratio,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

BASE_ASSET = {
    "estimated_monthly_rent": 2500.0,
    "purchase_price": 300_000.0,
    "beds": 3,
    "baths": 2,
    "hoa_name": None,
}

BASE_THRESHOLDS = ScreeningThresholds(
    min_gross_yield=0.07,
    max_price_to_rent_ratio=15.0,
    min_beds=2,
    min_baths=1,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Pure arithmetic helpers
# ═══════════════════════════════════════════════════════════════════════════════


class TestGrossYield:
    """Tests for the pure gross_yield() function."""

    def test_basic_gross_yield(self):
        """$2,500/mo rent on $300,000 price = 10% gross yield."""
        gy = gross_yield(monthly_rent=2500, purchase_price=300000)
        assert gy == pytest.approx(0.10, rel=1e-6)

    def test_gross_yield_low_rent(self):
        """Low rent produces low yield."""
        gy = gross_yield(monthly_rent=800, purchase_price=300000)
        assert gy == pytest.approx(0.032, rel=1e-3)

    def test_gross_yield_zero_price(self):
        """Zero purchase price returns 0.0 to avoid division by zero."""
        assert gross_yield(monthly_rent=2000, purchase_price=0) == 0.0

    def test_gross_yield_zero_rent(self):
        """Zero monthly rent returns 0.0."""
        assert gross_yield(monthly_rent=0, purchase_price=100000) == 0.0

    def test_gross_yield_negative(self):
        """Negative values return 0.0 (defensive)."""
        assert gross_yield(monthly_rent=-1000, purchase_price=100000) == 0.0


class TestPriceToRentRatio:
    """Tests for the pure price_to_rent_ratio() function."""

    def test_basic_ratio(self):
        """$300k price / $2.5k/mo rent = 10.0× annual."""
        ptr = price_to_rent_ratio(monthly_rent=2500, purchase_price=300000)
        assert ptr == pytest.approx(10.0, rel=1e-6)

    def test_expensive_market(self):
        """High price-to-rent ratio = expensive market."""
        ptr = price_to_rent_ratio(monthly_rent=2000, purchase_price=500000)
        assert ptr == pytest.approx(20.833, rel=1e-3)

    def test_zero_rent_returns_inf(self):
        """Zero monthly rent returns infinity."""
        assert price_to_rent_ratio(monthly_rent=0, purchase_price=100000) == float(
            "inf"
        )

    def test_zero_price(self):
        """Zero purchase price returns 0."""
        ptr = price_to_rent_ratio(monthly_rent=2000, purchase_price=0)
        assert ptr == 0.0


class TestComputeScreeningMetrics:
    """Tests for the composition helper."""

    def test_compute_metrics(self):
        """Returns both gross_yield and price_to_rent_ratio."""
        metrics = compute_screening_metrics(BASE_ASSET)
        assert "gross_yield" in metrics
        assert "price_to_rent_ratio" in metrics
        assert metrics["gross_yield"] == pytest.approx(0.10, rel=1e-6)
        assert metrics["price_to_rent_ratio"] == pytest.approx(10.0, rel=1e-6)

    def test_missing_rent_defaults_to_zero(self):
        """Missing rent key defaults to 0 → 0 yield."""
        data = {"purchase_price": 300000}
        metrics = compute_screening_metrics(data)
        assert metrics["gross_yield"] == 0.0
        assert metrics["price_to_rent_ratio"] == float("inf")


# ═══════════════════════════════════════════════════════════════════════════════
#  evaluate_screening_stage
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvaluateScreeningStage:
    """Tests for the top-level screening evaluator."""

    # ── PASS ──────────────────────────────────────────────────────────────────

    def test_all_checks_pass(self):
        """A property meeting all thresholds passes."""
        passed, reason = evaluate_screening_stage(BASE_ASSET, BASE_THRESHOLDS)
        assert passed is True
        assert reason is None

    def test_above_minimums_still_passes(self):
        """Above-minimum beds/baths/yield still passes."""
        data = {**BASE_ASSET, "beds": 5, "baths": 4}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    # ── BEDS ──────────────────────────────────────────────────────────────────

    def test_fails_on_below_min_beds(self):
        """Fewer beds than min_beds → fail."""
        data = {**BASE_ASSET, "beds": 1}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is False
        assert "bedroom" in (reason or "").lower()

    def test_passes_on_exact_min_beds(self):
        """Exact minimum beds still passes."""
        data = {**BASE_ASSET, "beds": 2}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    # ── BATHS ─────────────────────────────────────────────────────────────────

    def test_fails_on_below_min_baths(self):
        """Fewer baths than min_baths → fail."""
        data = {**BASE_ASSET, "baths": 0.5}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is False
        assert "bath" in (reason or "").lower()

    def test_passes_on_exact_min_baths(self):
        """Exact minimum baths still passes."""
        data = {**BASE_ASSET, "baths": 1}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    # ── HOA EXCLUSION ─────────────────────────────────────────────────────────

    def test_excluded_hoa_fails(self):
        """Property in an excluded HOA → fail."""
        thresholds = BASE_THRESHOLDS.model_copy(
            update={"excluded_hoas": ["Sunset Homes", "Lake View"]}
        )
        data = {**BASE_ASSET, "hoa_name": "Sunset Homes"}
        passed, reason = evaluate_screening_stage(data, thresholds)
        assert passed is False
        assert "HOA" in (reason or "")

    def test_non_excluded_hoa_passes(self):
        """Property in a non-excluded HOA → pass."""
        thresholds = BASE_THRESHOLDS.model_copy(
            update={"excluded_hoas": ["Sunset Homes"]}
        )
        data = {**BASE_ASSET, "hoa_name": "Lake View"}
        passed, reason = evaluate_screening_stage(data, thresholds)
        assert passed is True

    def test_hoa_exclusion_case_insensitive(self):
        """HOA name matching is case-insensitive."""
        thresholds = BASE_THRESHOLDS.model_copy(
            update={"excluded_hoas": ["SUNSET HOMES"]}
        )
        data = {**BASE_ASSET, "hoa_name": "sunset homes"}
        passed, reason = evaluate_screening_stage(data, thresholds)
        assert passed is False

    # ── GROSS YIELD ───────────────────────────────────────────────────────────

    def test_fails_on_low_gross_yield(self):
        """Below-minimum gross yield → fail."""
        data = {**BASE_ASSET, "estimated_monthly_rent": 1500}  # 6% yield
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is False
        assert "yield" in (reason or "").lower()

    def test_passes_on_exact_min_gross_yield(self):
        """Exact minimum gross yield → pass."""
        data = {**BASE_ASSET, "estimated_monthly_rent": 1750}  # 7% exactly
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    # ── PRICE-TO-RENT RATIO ──────────────────────────────────────────────────

    def test_fails_on_high_price_to_rent(self):
        """Above-maximum price-to-rent ratio → fail."""
        # Need data where yield passes but ratio fails:
        # min_yield=0.05, pass when (rent*12)/price >= 0.05
        # max_ratio=12, fail when price/(rent*12) > 12
        # rent=3000, price=520000 → yield=0.069 (pass), ratio=14.44 (fail)
        data = {
            "estimated_monthly_rent": 3000,
            "purchase_price": 520_000,
            "beds": 3,
            "baths": 2,
        }
        thresholds = BASE_THRESHOLDS.model_copy(
            update={"min_gross_yield": 0.05, "max_price_to_rent_ratio": 12.0}
        )
        passed, reason = evaluate_screening_stage(data, thresholds)
        assert passed is False
        assert "price-to-rent" in (reason or "").lower()

    def test_passes_on_exact_max_price_to_rent(self):
        """Exact maximum price-to-rent ratio → pass."""
        # Target: passes yield (>=5%) and exactly hits ratio (12.0)
        # ratio = price/(rent*12) = 12 → price = 12*rent*12 = 144*rent
        # yield = (rent*12)/price = (rent*12)/(144*rent) = 0.0833 = 8.33%
        # With rent=2500: price=360000, yield=8.33%, ratio=12.0
        data = {
            "estimated_monthly_rent": 2500,
            "purchase_price": 360_000,
            "beds": 3,
            "baths": 2,
        }
        thresholds = BASE_THRESHOLDS.model_copy(
            update={"min_gross_yield": 0.05, "max_price_to_rent_ratio": 12.0}
        )
        passed, reason = evaluate_screening_stage(data, thresholds)
        assert passed is True, f"Expected pass, got: {reason}"

    # ── MISSING DATA EDGE CASES ───────────────────────────────────────────────

    def test_missing_beds_skips_bed_check(self):
        """If beds key is missing, beds check is skipped (not failed)."""
        data = {k: v for k, v in BASE_ASSET.items() if k != "beds"}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    def test_missing_rent_skips_yield_and_ratio(self):
        """If rent is missing, yield and ratio checks are skipped."""
        data = {k: v for k, v in BASE_ASSET.items() if k != "estimated_monthly_rent"}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    def test_missing_price_skips_yield_and_ratio(self):
        """If price is missing, yield and ratio checks are skipped."""
        data = {k: v for k, v in BASE_ASSET.items() if k != "purchase_price"}
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is True

    # ── FIRST FAILURE SHORT-CIRCUIT ──────────────────────────────────────────

    def test_beds_checked_before_yield(self):
        """Beds check (cheapest) runs first; failing beds short-circuits."""
        data = {
            **BASE_ASSET,
            "beds": 1,  # fails
            "estimated_monthly_rent": 100,  # would also fail yield
            "purchase_price": 500000,  # would also fail ratio
        }
        passed, reason = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert passed is False
        # Should fail on beds before getting to yield
        assert "bedroom" in (reason or "").lower()

    # ── PERFORMANCE VERIFICATION ──────────────────────────────────────────────

    def test_evaluation_under_10ms(self):
        """Single evaluation completes in under 10ms (trivially)."""
        import time

        start = time.perf_counter()
        for _ in range(1000):
            evaluate_screening_stage(BASE_ASSET, BASE_THRESHOLDS)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 1000
        assert elapsed_ms < 10, (
            f"Average evaluation took {elapsed_ms:.4f}ms (expected <10ms)"
        )

    # ── PROTOCOL: returns (bool, str | None) ─────────────────────────────────

    def test_return_type_on_pass(self):
        """Pass returns (True, None)."""
        result = evaluate_screening_stage(BASE_ASSET, BASE_THRESHOLDS)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is True
        assert result[1] is None

    def test_return_type_on_fail(self):
        """Fail returns (False, str)."""
        data = {**BASE_ASSET, "beds": 0}
        result = evaluate_screening_stage(data, BASE_THRESHOLDS)
        assert isinstance(result, tuple)
        assert result[0] is False
        assert isinstance(result[1], str)
