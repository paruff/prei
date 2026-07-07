"""Tests for the PipelineOrchestrator."""

from prei.models.pipeline import PipelineStage
from prei.pipeline.orchestrator import PipelineOrchestrator

PASSING_PAYLOAD = {
    "id": "ORCH-001",
    "address": "123 Pipeline Dr",
    "price": 300_000.0,
    "rent": 2500.0,
    "beds": 3,
    "baths": 2,
}

FAILING_PAYLOAD = {
    "id": "ORCH-002",
    "address": "456 Bad Yield Ln",
    "price": 500_000.0,
    "rent": 1200.0,  # (1200*12)/500000 = 2.88% — below 7%
    "beds": 1,
    "baths": 0.5,
}


class TestPipelineOrchestrator:
    def test_full_successful_pipeline(self):
        """Passing payload reaches UNDERWRITING with computed metrics."""
        orch = PipelineOrchestrator()
        result = orch.run(PASSING_PAYLOAD, source_name="test")
        assert result.success
        assert result.screening_passed is True
        assert result.asset is not None
        assert result.asset.current_stage == PipelineStage.UNDERWRITING
        assert result.underwriting is not None
        assert result.underwriting.mao > 0
        assert result.underwriting.noi > 0

    def test_screening_failure_kills_asset(self):
        """Failing payload is killed at SCREENING stage."""
        orch = PipelineOrchestrator()
        result = orch.run(FAILING_PAYLOAD, source_name="test")
        assert result.success  # no error — pipeline handled it gracefully
        assert result.screening_passed is False
        assert result.screening_reason is not None
        assert result.asset is not None
        assert result.asset.current_stage == PipelineStage.KILLED

    def test_missing_address_returns_error(self):
        """Payload without address fails at discovery."""
        orch = PipelineOrchestrator()
        result = orch.run({"id": "BAD"}, source_name="test")
        assert result.success is False
        assert "Discovery" in (result.error or "")

    def test_duplicate_address_hash_skipped(self):
        """Duplicate address hash returns error without processing."""
        orch = PipelineOrchestrator()
        # First run succeeds
        r1 = orch.run(PASSING_PAYLOAD, source_name="test")
        assert r1.success
        # Second run with same address is duplicate
        r2 = orch.run(PASSING_PAYLOAD, source_name="test")
        assert r2.success is False
        assert "Duplicate" in (r2.error or "")

    def test_underwriting_metrics_computed(self):
        """Underwriting metrics include NOI, cap rate, CoC, MAO."""
        orch = PipelineOrchestrator()
        result = orch.run(PASSING_PAYLOAD, source_name="test")
        uw = result.underwriting
        assert uw.noi > 0
        assert uw.cap_rate > 0
        assert uw.cash_on_cash > 0
        assert uw.mao > 0

    def test_to_dict_serialization_success(self):
        """to_dict() returns expected keys on success."""
        orch = PipelineOrchestrator()
        result = orch.run(PASSING_PAYLOAD, source_name="test")
        d = result.to_dict()
        assert d["success"] is True
        assert "asset_id" in d
        assert "current_stage" in d
        assert "screening_passed" in d
        assert "noi" in d
        assert "cap_rate" in d
        assert "mao" in d

    def test_to_dict_serialization_error(self):
        """to_dict() returns only success + error on failure."""
        orch = PipelineOrchestrator()
        result = orch.run({"id": "BAD"}, source_name="test")
        d = result.to_dict()
        assert d["success"] is False
        assert "error" in d
        assert "asset_id" not in d

    def test_stage_history_has_three_entries(self):
        """Successful run has GACS→DISCOVERY→SCREENING→UNDERWRITING in log."""
        orch = PipelineOrchestrator()
        result = orch.run(PASSING_PAYLOAD, source_name="test")
        assert len(result.asset.stage_history) == 3
        assert result.asset.stage_history[0].stage == PipelineStage.DISCOVERY
        assert result.asset.stage_history[1].stage == PipelineStage.SCREENING
        assert result.asset.stage_history[2].stage == PipelineStage.UNDERWRITING
