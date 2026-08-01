"""Comprehensive unit test suite for the property pipeline.

Covers:
  - Screening engine math edge cases (division by zero, missing data)
  - Batch processor with a 10-mock-asset dataset (3 valid, 7 failing distinct rules)

The prei state-machine tests (stage-machine classes transitions) were
removed in the pydantic→Django consolidation — stage transitions are now
covered by core/tests/test_pipeline_service.py against PipelineProperty.
"""

from dataclasses import replace

from core.services.screening import (
    ScreeningThresholds,
    evaluate_screening_stage,
    gross_yield,
    price_to_rent_ratio,
    screen_batch,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. SCREENING ENGINE MATH EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestScreeningMathEdgeCases:
    """Division by zero, missing data, and boundary conditions."""

    THRESHOLDS = ScreeningThresholds(
        min_gross_yield=0.07,
        max_price_to_rent_ratio=15.0,
        min_beds=2,
        min_baths=1,
    )

    # ── Division by zero: gross_yield ────────────────────────────────────────

    def test_gross_yield_zero_purchase_price(self):
        """Purchase price of 0 → gross_yield returns 0.0 (no crash)."""
        assert gross_yield(monthly_rent=2000, purchase_price=0) == 0.0

    def test_gross_yield_zero_rent(self):
        """Rent of 0 → gross_yield returns 0.0 (no crash)."""
        assert gross_yield(monthly_rent=0, purchase_price=100000) == 0.0

    def test_gross_yield_both_zero(self):
        """Both zero → gross_yield returns 0.0."""
        assert gross_yield(monthly_rent=0, purchase_price=0) == 0.0

    # ── Division by zero: price_to_rent_ratio ────────────────────────────────

    def test_price_to_rent_zero_rent(self):
        """Rent of 0 → price_to_rent returns inf (no crash)."""
        result = price_to_rent_ratio(monthly_rent=0, purchase_price=100000)
        assert result == float("inf")

    def test_price_to_rent_zero_price(self):
        """Price of 0 → price_to_rent returns 0.0."""
        assert price_to_rent_ratio(monthly_rent=2000, purchase_price=0) == 0.0

    def test_price_to_rent_both_zero(self):
        """Both zero → price_to_rent returns inf (rent=0 dominates)."""
        result = price_to_rent_ratio(monthly_rent=0, purchase_price=0)
        assert result == float("inf")

    # ── Division by zero: evaluate_screening_stage ───────────────────────────

    def test_evaluate_zero_purchase_price_skips_yield_and_ratio(self):
        """Purchase price of 0 → yield and ratio checks are skipped gracefully."""
        data = {
            "estimated_monthly_rent": 2000,
            "purchase_price": 0,
            "beds": 3,
            "baths": 2,
        }
        passed, reason = evaluate_screening_stage(data, self.THRESHOLDS)
        # Should pass because yield/ratio checks are skipped when price <= 0
        assert passed is True

    def test_evaluate_zero_rent_skips_yield_and_ratio(self):
        """Rent of 0 → yield and ratio checks are skipped."""
        data = {
            "estimated_monthly_rent": 0,
            "purchase_price": 300000,
            "beds": 3,
            "baths": 2,
        }
        passed, reason = evaluate_screening_stage(data, self.THRESHOLDS)
        assert passed is True

    # ── Missing data ─────────────────────────────────────────────────────────

    def test_missing_beds_skips_bed_check(self):
        """Missing beds key → beds check skipped (not failed)."""
        data = {
            "estimated_monthly_rent": 2500,
            "purchase_price": 300000,
            "baths": 2,
        }
        passed, reason = evaluate_screening_stage(data, self.THRESHOLDS)
        assert passed is True

    def test_missing_baths_skips_bath_check(self):
        """Missing baths key → baths check skipped."""
        data = {
            "estimated_monthly_rent": 2500,
            "purchase_price": 300000,
            "beds": 3,
        }
        passed, reason = evaluate_screening_stage(data, self.THRESHOLDS)
        assert passed is True

    def test_str_beds_coerced_correctly(self):
        """String beds value '3' is parsed as int."""
        data = {
            "estimated_monthly_rent": 2500,
            "purchase_price": 300000,
            "beds": "3",
            "baths": 2,
        }
        passed, reason = evaluate_screening_stage(data, self.THRESHOLDS)
        assert passed is True

    def test_str_beds_fails_when_below_minimum(self):
        """String beds '1' fails the check."""
        data = {
            "estimated_monthly_rent": 2500,
            "purchase_price": 300000,
            "beds": "1",
            "baths": 2,
        }
        passed, reason = evaluate_screening_stage(data, self.THRESHOLDS)
        assert passed is False
        assert "bedroom" in (reason or "").lower()

    # ── Empty HOA list ───────────────────────────────────────────────────────

    def test_empty_excluded_hoas_list(self):
        """Empty excluded_hoas list never blocks any HOA."""
        thresholds = replace(self.THRESHOLDS, excluded_hoas=[])
        data = {
            "estimated_monthly_rent": 2500,
            "purchase_price": 300000,
            "beds": 3,
            "baths": 2,
            "hoa_name": "Sunset Homes",
        }
        passed, reason = evaluate_screening_stage(data, thresholds)
        assert passed is True


# ═══════════════════════════════════════════════════════════════════════════════
#  2. BATCH PROCESSOR — 10 MOCK ASSETS (3 PASS, 7 FAIL DISTINCT RULES)
# ═══════════════════════════════════════════════════════════════════════════════


# Shared thresholds for the batch test
BATCH_THRESHOLDS = ScreeningThresholds(
    min_gross_yield=0.07,
    max_price_to_rent_ratio=15.0,
    min_beds=2,
    min_baths=1,
    excluded_hoas=["Sunset Homes", "Lake View Condos"],
)

# Dataset of 10 mock assets: 3 valid + 7 failing distinct rules
MOCK_DATASET = [
    # ── PASSING (3) ─────────────────────────────────────────────────────────
    {
        "asset_id": "PASS-01",
        "address": "101 Good St",
        "estimated_monthly_rent": 2500.0,
        "purchase_price": 300_000.0,
        "beds": 3,
        "baths": 2,
    },
    {
        "asset_id": "PASS-02",
        "address": "202 Great Ave",
        "estimated_monthly_rent": 3000.0,
        "purchase_price": 350_000.0,
        "beds": 4,
        "baths": 2,
    },
    {
        "asset_id": "PASS-03",
        "address": "303 Prime Blvd",
        "estimated_monthly_rent": 4000.0,
        "purchase_price": 480_000.0,
        "beds": 5,
        "baths": 3,
    },
    # ── FAILING (7) — each fails a different rule ───────────────────────────
    {
        "asset_id": "FAIL-BEDS-01",
        "address": "404 Small Ln",
        "estimated_monthly_rent": 2500.0,
        "purchase_price": 300_000.0,
        "beds": 1,  # < min_beds (2)
        "baths": 2,
    },
    {
        "asset_id": "FAIL-BATHS-01",
        "address": "505 Tight Pl",
        "estimated_monthly_rent": 2500.0,
        "purchase_price": 300_000.0,
        "beds": 3,
        "baths": 0.5,  # < min_baths (1)
    },
    {
        "asset_id": "FAIL-HOA-01",
        "address": "606 Lake View Dr",
        "estimated_monthly_rent": 2500.0,
        "purchase_price": 300_000.0,
        "beds": 3,
        "baths": 2,
        "hoa_name": "Lake View Condos",  # excluded HOA
    },
    {
        "asset_id": "FAIL-YIELD-01",
        "address": "707 LowYield Ct",
        "estimated_monthly_rent": 1500.0,  # (1500*12)/300000 = 6%
        "purchase_price": 300_000.0,
        "beds": 3,
        "baths": 2,
    },
    {
        "asset_id": "FAIL-RATIO-01",
        "address": "808 Expensive Way",
        "estimated_monthly_rent": 2000.0,
        "purchase_price": 500_000.0,  # 500000/(2000*12) = 20.8 > 15
        "beds": 3,
        "baths": 2,
    },
    {
        "asset_id": "FAIL-MULTI-01",
        "address": "909 Multi Fail Rd",
        "estimated_monthly_rent": 800.0,  # yield: 3.2% < 7%
        "purchase_price": 300_000.0,
        "beds": 1,  # < min_beds — caught first
        "baths": 0.5,  # < min_baths
    },
    {
        "asset_id": "FAIL-RENT-MISSING",
        "address": "NaN Data Cir",
        # estimated_monthly_rent deliberately missing
        "purchase_price": 300_000.0,
        "beds": 3,
        "baths": 2,
    },
]


class TestBatchProcessorTenAssets:
    """Verify the batch processor against a 10-asset mock dataset."""

    # ── Individual expected outcomes ──────────────────────────────────────────

    def test_individual_asset_outcomes(self):
        """Each asset's screening result matches the expected pass/fail."""
        expected = {
            "PASS-01": True,
            "PASS-02": True,
            "PASS-03": True,
            "FAIL-BEDS-01": False,
            "FAIL-BATHS-01": False,
            "FAIL-HOA-01": False,
            "FAIL-YIELD-01": False,
            "FAIL-RATIO-01": False,
            "FAIL-MULTI-01": False,
            "FAIL-RENT-MISSING": True,  # missing rent → checks skipped → passes
        }
        for asset_data in MOCK_DATASET:
            passed, _ = evaluate_screening_stage(asset_data, BATCH_THRESHOLDS)
            aid = asset_data["asset_id"]
            assert passed == expected[aid], (
                f"{aid}: expected pass={expected[aid]}, got pass={passed}"
            )

    # ── Batch summary numbers ────────────────────────────────────────────────

    def test_batch_summary_counts(self):
        """Batch processor returns correct processed/advanced/killed counts."""
        summary = screen_batch(MOCK_DATASET, BATCH_THRESHOLDS)

        assert summary["processed"] == 10
        assert summary["advanced"] == 4  # 3 passing + 1 missing-rent (falls through)
        assert summary["killed"] == 6  # 7 failing - 1 missing-rent (not killed)
        assert summary["execution_time_ms"] >= 0

    # ── First-failure short-circuit within single asset ───────────────────────

    def test_multi_fail_asset_reports_first_violation(self):
        """FAIL-MULTI-01 fails on beds (first check) before yield."""
        passed, reason = evaluate_screening_stage(
            next(a for a in MOCK_DATASET if a["asset_id"] == "FAIL-MULTI-01"),
            BATCH_THRESHOLDS,
        )
        assert passed is False
        # Should fail on beds before yield
        assert "bedroom" in (reason or "").lower()

    # ── Deterministic: running twice yields same results ─────────────────────

    def test_deterministic_output(self):
        """Processing the same dataset twice produces identical counts."""
        s1 = screen_batch(MOCK_DATASET, BATCH_THRESHOLDS)
        s2 = screen_batch(MOCK_DATASET, BATCH_THRESHOLDS)

        for key in ("processed", "advanced", "killed"):
            assert s1[key] == s2[key], f"Mismatch on {key}: {s1[key]} != {s2[key]}"
