"""E2E tests for the full pipeline orchestration (discovery → screening → underwriting → offer)."""

import pytest
from prei.pipeline.orchestrator import PipelineOrchestrator

PROPERTIES = [
    {
        "id": "E2E-FP-1",
        "address": "100 Prime St",
        "price": 300000,
        "rent": 2800,
        "beds": 3,
        "baths": 2,
    },
    {
        "id": "E2E-FP-2",
        "address": "200 Value Ave",
        "price": 220000,
        "rent": 2000,
        "beds": 3,
        "baths": 1,
    },
]

FAILING = {
    "id": "E2E-FAIL",
    "address": "999 Bad Rd",
    "price": 600000,
    "rent": 1500,
    "beds": 1,
    "baths": 0.5,
}


@pytest.mark.e2e
class TestPipelineE2E:
    def test_full_pipeline_happy_path(self):
        """All properties pass screening and reach UNDERWRITING."""
        orch = PipelineOrchestrator()
        for p in PROPERTIES:
            result = orch.run(p)
            assert result.success, f"{p['id']} should pass: {result.error}"
            assert result.asset.current_stage.value == "UNDERWRITING"
            assert result.underwriting.noi > 0
            assert result.underwriting.mao > 0

    def test_pipeline_rejects_failing_property(self):
        """Property failing screening is killed."""
        orch = PipelineOrchestrator()
        result = orch.run(FAILING)
        assert result.success  # Graceful handling
        assert result.screening_passed is False
        assert result.asset.current_stage.value == "KILLED"
        assert result.underwriting is None

    def test_pipeline_dedup(self):
        """Same address run twice → second is duplicate."""
        orch = PipelineOrchestrator()
        r1 = orch.run(PROPERTIES[0])
        assert r1.success
        r2 = orch.run(PROPERTIES[0])
        assert r2.success is False
        assert "Duplicate" in (r2.error or "")

    def test_pipeline_with_offer(self):
        """Pipeline → underwriting → offer chain works."""
        from prei.pipeline.handlers.offer import solve_offer, OfferInput, OfferStrategy

        orch = PipelineOrchestrator()
        result = orch.run(PROPERTIES[0])
        assert result.success
        offer = solve_offer(
            OfferInput(mao=result.underwriting.mao), OfferStrategy.TARGET
        )
        assert offer.offer_price > 0
        assert offer.premium_pct == pytest.approx(0, abs=1e-4)

    def test_multi_property_pipeline(self):
        """Multiple properties processed sequentially."""
        orch = PipelineOrchestrator()
        results = [orch.run(p) for p in PROPERTIES]
        assert all(r.success for r in results)
        assert results[0].underwriting.cap_rate != results[1].underwriting.cap_rate

    def test_pipeline_to_dict_includes_offer(self):
        """to_dict() contains all key pipeline outputs."""
        orch = PipelineOrchestrator()
        result = orch.run(PROPERTIES[0])
        d = result.to_dict()
        assert d["success"] is True
        assert d["current_stage"] == "UNDERWRITING"
        assert d["cap_rate"] > 0
        assert d["mao"] > 0
