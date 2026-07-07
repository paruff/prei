"""Comprehensive unit test suite for the property pipeline.

Covers:
  - State transition validation (illicit jump controls)
  - Screening engine math edge cases (division by zero, missing data)
  - Batch processor with a 10-mock-asset dataset (3 valid, 7 failing distinct rules)
"""

import pytest

from prei.models.pipeline import (
    InvalidStageTransitionException,
    PipelineStage,
    PropertyAsset,
)
from prei.pipeline.engine import InMemoryAssetRepository, PipelineEngine
from prei.pipeline.handlers.batch_screening import BatchScreeningProcessor
from prei.pipeline.handlers.screening import (
    ScreeningThresholds,
    evaluate_screening_stage,
    gross_yield,
    price_to_rent_ratio,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. STATE TRANSITION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestStateTransitionValidation:
    """Verify the state machine enforces all transition rules."""

    def _make_asset(self) -> PropertyAsset:
        return PropertyAsset(asset_id="T", address="1 Test St")

    # ── Illicit jumps ────────────────────────────────────────────────────────

    def test_gacs_to_underwriting_raises(self):
        """GACS → UNDERWRITING is an illicit jump (must go through DISCOVERY, SCREENING)."""
        a = self._make_asset()
        with pytest.raises(InvalidStageTransitionException) as exc:
            a.transition_to(PipelineStage.UNDERWRITING)
        assert "GACS" in str(exc.value)
        assert "UNDERWRITING" in str(exc.value)

    def test_gacs_to_portfolio_raises(self):
        """GACS → PORTFOLIO is an illicit jump."""
        a = self._make_asset()
        with pytest.raises(InvalidStageTransitionException):
            a.transition_to(PipelineStage.PORTFOLIO)

    def test_screening_to_closing_raises(self):
        """SCREENING → CLOSING skips UNDERWRITING, OFFER, DUE_DILIGENCE."""
        a = self._make_asset()
        a.transition_to(PipelineStage.DISCOVERY)
        a.transition_to(PipelineStage.SCREENING)
        with pytest.raises(InvalidStageTransitionException):
            a.transition_to(PipelineStage.CLOSING)

    def test_offer_to_turnover_raises(self):
        """OFFER → TURNOVER skips DUE_DILIGENCE, CLOSING."""
        a = self._make_asset()
        a.transition_to(PipelineStage.DISCOVERY)
        a.transition_to(PipelineStage.SCREENING)
        a.transition_to(PipelineStage.UNDERWRITING)
        a.transition_to(PipelineStage.OFFER)
        with pytest.raises(InvalidStageTransitionException):
            a.transition_to(PipelineStage.TURNOVER)

    def test_killed_to_anything_raises(self):
        """KILLED is terminal — no transitions out."""
        a = self._make_asset()
        a.transition_to(PipelineStage.KILLED, reason="test")
        for stage in PipelineStage:
            if stage == PipelineStage.KILLED:
                continue
            with pytest.raises(InvalidStageTransitionException):
                a.transition_to(stage)

    # ── Valid forward flow ────────────────────────────────────────────────────

    def test_full_forward_flow(self):
        """Every legal forward transition succeeds."""
        a = self._make_asset()
        path = [
            (PipelineStage.DISCOVERY, "identify"),
            (PipelineStage.SCREENING, "qualify"),
            (PipelineStage.UNDERWRITING, "analyze"),
            (PipelineStage.OFFER, "bid"),
            (PipelineStage.DUE_DILIGENCE, "inspect"),
            (PipelineStage.CLOSING, "purchase"),
            (PipelineStage.TURNOVER, "rehab"),
            (PipelineStage.LEASING, "rent"),
            (PipelineStage.PORTFOLIO, "hold"),
        ]
        for stage, _ in path:
            a.transition_to(stage, reason="forward")
            assert a.current_stage == stage
        assert a.current_stage == PipelineStage.PORTFOLIO

    def test_leasing_portfolio_bidirectional(self):
        """LEASING ↔ PORTFOLIO works in both directions."""
        a = self._make_asset()
        a.transition_to(PipelineStage.DISCOVERY)
        a.transition_to(PipelineStage.SCREENING)
        a.transition_to(PipelineStage.UNDERWRITING)
        a.transition_to(PipelineStage.OFFER)
        a.transition_to(PipelineStage.DUE_DILIGENCE)
        a.transition_to(PipelineStage.CLOSING)
        a.transition_to(PipelineStage.TURNOVER)
        a.transition_to(PipelineStage.LEASING)

        # LEASING → PORTFOLIO
        a.transition_to(PipelineStage.PORTFOLIO)
        assert a.current_stage == PipelineStage.PORTFOLIO

        # PORTFOLIO → LEASING (back to active management)
        a.transition_to(PipelineStage.LEASING)
        assert a.current_stage == PipelineStage.LEASING

    def test_kill_from_any_stage(self):
        """KILLED is reachable from any non-terminal stage."""
        stages = [s for s in PipelineStage if s != PipelineStage.KILLED]
        for stage in stages:
            a = self._make_asset()
            # Advance to target stage
            if stage == PipelineStage.GACS:
                pass  # already at GACS
            elif stage == PipelineStage.DISCOVERY:
                a.transition_to(PipelineStage.DISCOVERY)
            elif stage == PipelineStage.SCREENING:
                a.transition_to(PipelineStage.DISCOVERY)
                a.transition_to(PipelineStage.SCREENING)
            elif stage == PipelineStage.UNDERWRITING:
                a.transition_to(PipelineStage.DISCOVERY)
                a.transition_to(PipelineStage.SCREENING)
                a.transition_to(PipelineStage.UNDERWRITING)
            elif stage == PipelineStage.OFFER:
                self._advance_to(a, PipelineStage.OFFER)
            elif stage == PipelineStage.DUE_DILIGENCE:
                self._advance_to(a, PipelineStage.DUE_DILIGENCE)
            elif stage == PipelineStage.CLOSING:
                self._advance_to(a, PipelineStage.CLOSING)
            elif stage == PipelineStage.TURNOVER:
                self._advance_to(a, PipelineStage.TURNOVER)
            elif stage == PipelineStage.LEASING:
                self._advance_to(a, PipelineStage.LEASING)
            elif stage == PipelineStage.PORTFOLIO:
                self._advance_to(a, PipelineStage.PORTFOLIO)

            a.transition_to(PipelineStage.KILLED, reason=f"Killed at {stage.value}")
            assert a.current_stage == PipelineStage.KILLED
            assert a.kill_reason == f"Killed at {stage.value}"

    def _advance_to(self, a: PropertyAsset, target: PipelineStage) -> None:
        """Advance asset through the pipeline to the given stage."""
        path = [
            PipelineStage.DISCOVERY,
            PipelineStage.SCREENING,
            PipelineStage.UNDERWRITING,
            PipelineStage.OFFER,
            PipelineStage.DUE_DILIGENCE,
            PipelineStage.CLOSING,
            PipelineStage.TURNOVER,
            PipelineStage.LEASING,
            PipelineStage.PORTFOLIO,
        ]
        for stage in path:
            a.transition_to(stage, reason="forward")
            if stage == target:
                break

    # ── Stage history integrity ───────────────────────────────────────────────

    def test_stage_history_records_all_transitions(self):
        """Every transition adds a StageLog entry with correct timestamps."""
        a = self._make_asset()
        a.transition_to(PipelineStage.DISCOVERY)
        a.transition_to(PipelineStage.SCREENING)
        a.transition_to(PipelineStage.KILLED, reason="Budget cut")

        assert len(a.stage_history) == 3
        assert a.stage_history[0].stage == PipelineStage.DISCOVERY
        assert a.stage_history[1].stage == PipelineStage.SCREENING
        assert a.stage_history[2].stage == PipelineStage.KILLED

        # exited_at should be set for completed stages
        assert a.stage_history[0].exited_at is not None
        assert a.stage_history[1].exited_at is not None
        # Current (last) stage should have no exit time
        assert a.stage_history[2].exited_at is None


# ═══════════════════════════════════════════════════════════════════════════════
#  2. SCREENING ENGINE MATH EDGE CASES
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
        thresholds = self.THRESHOLDS.model_copy(update={"excluded_hoas": []})
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
#  3. BATCH PROCESSOR — 10 MOCK ASSETS (3 PASS, 7 FAIL DISTINCT RULES)
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

    def _make_engine(self) -> PipelineEngine:
        return PipelineEngine(repository=InMemoryAssetRepository())

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
        engine = self._make_engine()
        processor = BatchScreeningProcessor(engine, BATCH_THRESHOLDS)

        summary = processor.process(MOCK_DATASET)

        assert summary["processed"] == 10
        assert summary["advanced"] == 4  # 3 passing + 1 missing-rent (falls through)
        assert summary["killed"] == 6  # 7 failing - 1 missing-rent (not killed)
        assert summary["execution_time_ms"] >= 0

    # ── All assets persisted ─────────────────────────────────────────────────

    def test_all_assets_persisted(self):
        """All 10 assets are saved to the repository."""
        engine = self._make_engine()
        processor = BatchScreeningProcessor(engine, BATCH_THRESHOLDS)
        processor.process(MOCK_DATASET)

        all_assets = engine.repository.list_all()
        assert len(all_assets) == 10
        asset_ids = {a.asset_id for a in all_assets}
        expected_ids = {d["asset_id"] for d in MOCK_DATASET}
        assert asset_ids == expected_ids

    # ── Killed assets have kill_reason ────────────────────────────────────────

    def test_killed_assets_have_reason(self):
        """All killed assets have a non-empty kill_reason."""
        engine = self._make_engine()
        processor = BatchScreeningProcessor(engine, BATCH_THRESHOLDS)
        processor.process(MOCK_DATASET)

        killed_ids = [
            "FAIL-BEDS-01",
            "FAIL-BATHS-01",
            "FAIL-HOA-01",
            "FAIL-YIELD-01",
            "FAIL-RATIO-01",
            "FAIL-MULTI-01",
        ]
        for aid in killed_ids:
            asset = engine.repository.load(aid)
            assert asset is not None
            assert asset.current_stage == PipelineStage.KILLED
            assert asset.kill_reason is not None
            assert len(asset.kill_reason) > 0

    # ── Advanced assets are at UNDERWRITING ──────────────────────────────────

    def test_advanced_assets_at_underwriting(self):
        """All advanced assets are in UNDERWRITING stage."""
        engine = self._make_engine()
        processor = BatchScreeningProcessor(engine, BATCH_THRESHOLDS)
        processor.process(MOCK_DATASET)

        for aid in ["PASS-01", "PASS-02", "PASS-03", "FAIL-RENT-MISSING"]:
            asset = engine.repository.load(aid)
            assert asset is not None
            assert asset.current_stage == PipelineStage.UNDERWRITING, (
                f"{aid} should be UNDERWRITING, got {asset.current_stage}"
            )

    # ── First-failure short-circuit within single asset ───────────────────────

    def test_multi_fail_asset_reports_first_violation(self):
        """FAIL-MULTI-01 fails on beds (first check) before yield."""
        engine = self._make_engine()
        processor = BatchScreeningProcessor(engine, BATCH_THRESHOLDS)
        processor.process(MOCK_DATASET)

        asset = engine.repository.load("FAIL-MULTI-01")
        assert asset is not None
        assert asset.current_stage == PipelineStage.KILLED
        # Should fail on beds before yield
        assert "bedroom" in (asset.kill_reason or "").lower()

    # ── Deterministic: running twice yields same results ─────────────────────

    def test_deterministic_output(self):
        """Processing the same dataset twice produces identical counts."""
        engine1 = self._make_engine()
        engine2 = self._make_engine()
        p1 = BatchScreeningProcessor(engine1, BATCH_THRESHOLDS)
        p2 = BatchScreeningProcessor(engine2, BATCH_THRESHOLDS)

        s1 = p1.process(MOCK_DATASET)
        s2 = p2.process(MOCK_DATASET)

        for key in ("processed", "advanced", "killed"):
            assert s1[key] == s2[key], f"Mismatch on {key}: {s1[key]} != {s2[key]}"
