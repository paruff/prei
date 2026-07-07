"""Tests for the BatchScreeningProcessor."""

from prei.models.pipeline import PipelineStage
from prei.pipeline.engine import InMemoryAssetRepository, PipelineEngine
from prei.pipeline.handlers.batch_screening import BatchScreeningProcessor
from prei.pipeline.handlers.screening import ScreeningThresholds

THRESHOLDS = ScreeningThresholds(
    min_gross_yield=0.07,
    max_price_to_rent_ratio=15.0,
    min_beds=2,
    min_baths=1,
)


def _make_engine() -> PipelineEngine:
    return PipelineEngine(repository=InMemoryAssetRepository())


# ── Fixtures ──────────────────────────────────────────────────────────────────

PASSING_PROPERTY = {
    "asset_id": "PASS-001",
    "address": "123 Good St",
    "estimated_monthly_rent": 2500.0,
    "purchase_price": 300_000.0,
    "beds": 3,
    "baths": 2,
}

FAILING_PROPERTY = {
    "asset_id": "FAIL-001",
    "address": "456 Bad Ave",
    "estimated_monthly_rent": 800.0,
    "purchase_price": 400_000.0,
    "beds": 1,
    "baths": 0.5,
}


class TestBatchScreeningProcessor:
    """Tests for the batch screening processor."""

    # ── Single property ───────────────────────────────────────────────────────

    def test_single_passing_property(self):
        """A single qualifying property advances to UNDERWRITING."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS)
        summary = processor.process([PASSING_PROPERTY])

        assert summary["processed"] == 1
        assert summary["advanced"] == 1
        assert summary["killed"] == 0
        assert summary["execution_time_ms"] >= 0

        asset = engine.repository.load("PASS-001")
        assert asset is not None
        assert asset.current_stage == PipelineStage.UNDERWRITING

    def test_single_failing_property(self):
        """A non-qualifying property is killed with reason."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS)
        summary = processor.process([FAILING_PROPERTY])

        assert summary["processed"] == 1
        assert summary["advanced"] == 0
        assert summary["killed"] == 1

        asset = engine.repository.load("FAIL-001")
        assert asset is not None
        assert asset.current_stage == PipelineStage.KILLED
        assert asset.kill_reason is not None
        assert "bedroom" in (asset.kill_reason or "").lower()

    # ── Mixed batch ───────────────────────────────────────────────────────────

    def test_mixed_batch(self):
        """Mixed passing and failing properties are correctly counted."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS)

        payloads = [
            PASSING_PROPERTY,
            FAILING_PROPERTY,
            {  # Another passing property
                "asset_id": "PASS-002",
                "address": "789 Nice Blvd",
                "estimated_monthly_rent": 3000.0,
                "purchase_price": 350_000.0,
                "beds": 4,
                "baths": 3,
            },
            {  # Another failing (yield too low)
                "asset_id": "FAIL-002",
                "address": "321 Pricey Ln",
                "estimated_monthly_rent": 2000.0,
                "purchase_price": 600_000.0,
                "beds": 3,
                "baths": 2,
            },
        ]
        summary = processor.process(payloads)

        assert summary["processed"] == 4
        assert summary["advanced"] == 2
        assert summary["killed"] == 2

        assert (
            engine.repository.load("PASS-001").current_stage
            == PipelineStage.UNDERWRITING
        )  # noqa
        assert (
            engine.repository.load("PASS-002").current_stage
            == PipelineStage.UNDERWRITING
        )  # noqa
        assert engine.repository.load("FAIL-001").current_stage == PipelineStage.KILLED
        assert engine.repository.load("FAIL-002").current_stage == PipelineStage.KILLED

    # ── Empty batch ───────────────────────────────────────────────────────────

    def test_empty_batch(self):
        """Empty list processes with zero counts."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS)
        summary = processor.process([])

        assert summary["processed"] == 0
        assert summary["advanced"] == 0
        assert summary["killed"] == 0

    # ── Batch of 1000 ─────────────────────────────────────────────────────────

    def test_batch_1000_properties(self):
        """1000 properties processed in under 2 seconds (sub-2ms each)."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS, max_workers=16)

        payloads = []
        for i in range(1000):
            passed = i % 2 == 0  # alternate pass/fail
            payloads.append(
                {
                    "asset_id": f"BATCH-{i:04d}",
                    "address": f"{i} Test St",
                    "estimated_monthly_rent": 2500.0 if passed else 800.0,
                    "purchase_price": 300_000.0,
                    "beds": 3 if passed else 1,
                    "baths": 2 if passed else 0.5,
                }
            )

        summary = processor.process(payloads)

        assert summary["processed"] == 1000
        assert summary["advanced"] == 500
        assert summary["killed"] == 500
        assert summary["execution_time_ms"] < 2000, (
            f"1000 properties took {summary['execution_time_ms']}ms (expected <2000ms)"
        )

    # ── Engine tracks all assets ──────────────────────────────────────────────

    def test_all_assets_tracked_in_repository(self):
        """All processed assets are saved to the engine's repository."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS)

        payloads = [PASSING_PROPERTY, FAILING_PROPERTY]
        processor.process(payloads)

        all_assets = engine.repository.list_all()
        assert len(all_assets) == 2
        ids = {a.asset_id for a in all_assets}
        assert ids == {"PASS-001", "FAIL-001"}

    # ── Transition context includes source metadata ───────────────────────────

    def test_killed_asset_has_screening_context(self):
        """Killed asset's stage log contains screening metrics."""
        engine = _make_engine()
        processor = BatchScreeningProcessor(engine, THRESHOLDS)

        payload = {
            **FAILING_PROPERTY,
            "asset_id": "CTX-CHECK",
        }
        processor.process([payload])

        asset = engine.repository.load("CTX-CHECK")
        assert asset is not None
        assert asset.current_stage == PipelineStage.KILLED

        last_log = asset.stage_history[-1]
        assert last_log.stage == PipelineStage.KILLED
        assert last_log.metrics_snapshot.get("asset_data", {}).get("beds") == 1
        assert (
            last_log.metrics_snapshot.get("asset_data", {}).get(
                "estimated_monthly_rent"
            )
            == 800.0
        )
