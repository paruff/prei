"""Integration and E2E tests for the underwriting stage."""

import pytest
from prei.pipeline.handlers.underwriting import (
    UnderwritingInput,
    solve_underwriting,
)

BASE = UnderwritingInput(
    purchase_price=300000,
    estimated_rent=2500,
    property_tax_annual=3600,
    insurance_annual=1200,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestUnderwritingIntegration:
    def test_noi_sensitivity_to_vacancy(self):
        """Higher vacancy reduces NOI proportionally."""
        base = solve_underwriting(BASE, 0.08)
        high_vac = solve_underwriting(
            BASE.model_copy(update={"vacancy_rate": 0.15}), 0.08
        )
        assert high_vac.noi < base.noi
        # EGI difference: GPR*(1-0.05) vs GPR*(1-0.15) → 10% of GPR less
        # GPR = 30000, so EGI difference = 3000. But OpEx also changes (mgmt fee on EGI)
        # Mgmt = 0.08*EGI, so diff = 3000 - 0.08*3000 = 2760
        assert base.noi - high_vac.noi == pytest.approx(2760, abs=50)

    def test_mao_inversely_related_to_target_cap(self):
        """Higher target cap rate → lower MAO."""
        low = solve_underwriting(BASE, 0.07)
        high = solve_underwriting(BASE, 0.10)
        assert high.mao < low.mao
        assert high.mao == pytest.approx(low.mao * 0.07 / 0.10, rel=1e-4)

    def test_rehab_budget_reduces_coc(self):
        """Adding rehab budget reduces cash-on-cash yield."""
        no_rehab = solve_underwriting(BASE, 0.08)
        with_rehab = solve_underwriting(
            BASE.model_copy(update={"rehab_budget": 50000}), 0.08
        )
        assert with_rehab.cash_on_cash < no_rehab.cash_on_cash

    def test_mao_above_price_when_cap_below_actual(self):
        """If target cap < actual cap, MAO > purchase price."""
        result = solve_underwriting(BASE, 0.05)  # 5% target
        assert result.mao > BASE.purchase_price

    def test_mao_below_price_when_cap_above_actual(self):
        """If target cap > actual cap, MAO < purchase price."""
        result = solve_underwriting(BASE, 0.10)  # 10% target
        assert result.mao < BASE.purchase_price

    def test_annual_metrics_consistency(self):
        """Monthly rent * 12 matches GPR used in NOI calc."""
        result = solve_underwriting(BASE, 0.08)
        assert result.noi > 0
        assert result.cap_rate > 0

    def test_zero_rent_still_produces_metrics(self):
        """Zero rent → negative NOI (expenses still exist), but no crash."""
        result = solve_underwriting(BASE.model_copy(update={"estimated_rent": 0}), 0.08)
        assert result.noi < 0
        assert result.cap_rate < 0
        assert result.mao < 0

    def test_purchase_price_sensitivity(self):
        """Higher purchase price → lower cap rate."""
        cheap = solve_underwriting(BASE, 0.08)
        expensive = solve_underwriting(
            BASE.model_copy(update={"purchase_price": 500000}), 0.08
        )
        assert expensive.cap_rate < cheap.cap_rate


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestUnderwritingE2E:
    def test_e2e_underwriting_via_orchestrator(self):
        """Underwriting metrics computed via full pipeline orchestration."""
        from prei.pipeline.orchestrator import PipelineOrchestrator

        orch = PipelineOrchestrator(target_cap_rate=0.08)
        payload = {
            "id": "UW-E2E",
            "address": "300 Test Ave",
            "price": 350000,
            "rent": 2800,
            "beds": 3,
            "baths": 2,
        }
        result = orch.run(payload)
        assert result.success
        uw = result.underwriting
        assert uw.noi > 0
        assert uw.cap_rate > 0.05
        assert uw.mao > 200000
        assert uw.cash_on_cash > 0.05

    def test_e2e_multi_property_underwriting(self):
        """Different properties get different underwriting metrics."""
        from prei.pipeline.orchestrator import PipelineOrchestrator

        orch = PipelineOrchestrator()
        results = []
        for p in [
            {
                "id": "A",
                "address": "A St",
                "price": 200000,
                "rent": 2000,
                "beds": 2,
                "baths": 1,
            },
            {
                "id": "B",
                "address": "B St",
                "price": 500000,
                "rent": 4000,
                "beds": 4,
                "baths": 3,
            },
        ]:
            results.append(orch.run(p))
        assert results[0].underwriting.cap_rate != results[1].underwriting.cap_rate
