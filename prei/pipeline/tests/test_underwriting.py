"""Tests for the underwriting solver engine."""

import pytest

from prei.pipeline.handlers.underwriting import (
    UnderwritingInput,
    UnderwritingMetrics,
    cap_rate,
    cash_on_cash_yield,
    effective_gross_income,
    gross_potential_rent,
    max_allowable_offer,
    net_operating_income,
    solve_underwriting,
    total_operating_expenses,
)

# ── Sample input ──────────────────────────────────────────────────────────────

BASE_INPUT = UnderwritingInput(
    purchase_price=300_000.0,
    estimated_rent=2500.0,
    vacancy_rate=0.05,
    rehab_budget=20_000.0,
    property_tax_annual=3_600.0,
    insurance_annual=1_200.0,
    maintenance_reserve_rate=0.10,
    management_fee_rate=0.08,
    hoa_annual=600.0,
)

# Expected intermediate values for BASE_INPUT:
# GPR    = 2500 * 12 = 30_000
# EGI    = 30000 * (1 - 0.05) = 28_500
# Maint  = 30000 * 0.10 = 3_000
# Mgmt   = 28500 * 0.08 = 2_280
# OpEx   = 3600 + 1200 + 3000 + 2280 + 600 = 10_680
# NOI    = 28500 - 10680 = 17_820
# Cap    = 17820 / 300000 = 0.0594 = 5.94%
# CoC    = 17820 / (300000 + 20000) = 17820 / 320000 = 0.0556875 = 5.57%
# MAO (8%): 17820 / 0.08 = 222_750.00


# ═══════════════════════════════════════════════════════════════════════════════
#  Pure arithmetic helpers
# ═══════════════════════════════════════════════════════════════════════════════


class TestPureArithmetic:
    """Tests for individual pure functions."""

    def test_gross_potential_rent(self):
        assert gross_potential_rent(2500) == 30_000.0
        assert gross_potential_rent(0) == 0.0

    def test_effective_gross_income(self):
        assert effective_gross_income(30_000, 0.05) == 28_500.0
        assert effective_gross_income(30_000, 0) == 30_000.0
        assert effective_gross_income(30_000, 1) == 0.0

    def test_total_operating_expenses(self):
        opex = total_operating_expenses(
            property_tax_annual=3_600.0,
            insurance_annual=1_200.0,
            gpr=30_000.0,
            maintenance_reserve_rate=0.10,
            egi=28_500.0,
            management_fee_rate=0.08,
            hoa_annual=600.0,
        )
        assert opex == pytest.approx(10_680.0)

    def test_net_operating_income(self):
        assert net_operating_income(28_500, 10_680) == pytest.approx(17_820.0)
        assert net_operating_income(0, 0) == 0.0
        assert net_operating_income(10_000, 15_000) == pytest.approx(-5_000.0)

    # ── Division by zero guards ──────────────────────────────────────────────

    def test_cap_rate_zero_price(self):
        assert cap_rate(noi=10_000, purchase_price=0) == 0.0

    def test_cap_rate_negative_price(self):
        assert cap_rate(noi=10_000, purchase_price=-100) == 0.0

    def test_cash_on_cash_zero_initial(self):
        assert cash_on_cash_yield(noi=10_000, purchase_price=0, rehab_budget=0) == 0.0

    def test_cash_on_cash_all_cash(self):
        """All-cash purchase: CoC = NOI / price."""
        coc = cash_on_cash_yield(noi=17_820, purchase_price=300_000, rehab_budget=0)
        assert coc == pytest.approx(0.0594, rel=1e-4)

    def test_cash_on_cash_with_rehab(self):
        """With rehab budget: CoC = NOI / (price + rehab)."""
        coc = cash_on_cash_yield(
            noi=17_820, purchase_price=300_000, rehab_budget=20_000
        )
        assert coc == pytest.approx(0.0556875, rel=1e-5)

    def test_max_allowable_offer_zero_target(self):
        assert max_allowable_offer(noi=10_000, target_cap_rate=0) == 0.0

    def test_max_allowable_offer_negative_target(self):
        assert max_allowable_offer(noi=10_000, target_cap_rate=-0.05) == 0.0

    def test_max_allowable_offer_standard(self):
        """MAO = NOI / target_cap_rate."""
        mao = max_allowable_offer(noi=17_820, target_cap_rate=0.08)
        assert mao == pytest.approx(222_750.0)


# ═══════════════════════════════════════════════════════════════════════════════
#  Composition: solve_underwriting
# ═══════════════════════════════════════════════════════════════════════════════


class TestSolveUnderwriting:
    """Tests for the full underwriting solver."""

    def test_base_case(self):
        """All intermediate values match expected calculations."""
        result = solve_underwriting(BASE_INPUT, target_cap_rate=0.08)

        assert isinstance(result, UnderwritingMetrics)
        assert result.noi == pytest.approx(17_820.0, rel=1e-4)
        assert result.cap_rate == pytest.approx(0.0594, rel=1e-4)
        assert result.cash_on_cash == pytest.approx(0.0556875, rel=1e-5)
        assert result.mao == pytest.approx(222_750.0, rel=1e-4)

    def test_high_target_cap_rate_lowers_mao(self):
        """Higher target cap rate → lower MAO."""
        result_8 = solve_underwriting(BASE_INPUT, target_cap_rate=0.08)
        result_10 = solve_underwriting(BASE_INPUT, target_cap_rate=0.10)
        assert result_10.mao < result_8.mao
        assert result_10.mao == pytest.approx(178_200.0, rel=1e-4)  # 17820 / 0.10

    def test_low_target_cap_rate_raises_mao(self):
        """Lower target cap rate → higher MAO."""
        result_6 = solve_underwriting(BASE_INPUT, target_cap_rate=0.06)
        assert result_6.mao == pytest.approx(297_000.0, rel=1e-4)  # 17820 / 0.06

    def test_no_rehab(self):
        """Zero rehab budget → CoC = NOI / price."""
        inp = BASE_INPUT.model_copy(update={"rehab_budget": 0})
        result = solve_underwriting(inp, target_cap_rate=0.08)
        assert result.cash_on_cash == pytest.approx(0.0594, rel=1e-4)

    def test_higher_vacancy_lowers_noi(self):
        """Higher vacancy rate → lower EGI → lower NOI."""
        inp_high_vac = BASE_INPUT.model_copy(update={"vacancy_rate": 0.15})
        result = solve_underwriting(inp_high_vac, target_cap_rate=0.08)

        # EGI = 30000 * 0.85 = 25500
        # Mgmt = 25500 * 0.08 = 2040
        # OpEx = 3600 + 1200 + 3000 + 2040 + 600 = 10440
        # NOI  = 25500 - 10440 = 15060
        assert result.noi == pytest.approx(15_060.0, rel=1e-4)

    def test_zero_purchase_price(self):
        """Zero purchase price → cap_rate = 0, MAO still valid."""
        inp = BASE_INPUT.model_copy(update={"purchase_price": 0, "rehab_budget": 0})
        result = solve_underwriting(inp, target_cap_rate=0.08)
        assert result.cap_rate == 0.0
        assert result.cash_on_cash == 0.0
        # MAO should still be valid (based on NOI, not price)
        assert result.mao == pytest.approx(222_750.0, rel=1e-4)

    def test_all_defaults(self):
        """Solver works with only required fields and defaults."""
        inp = UnderwritingInput(
            purchase_price=200_000.0,
            estimated_rent=1800.0,
            property_tax_annual=2_400.0,
            insurance_annual=900.0,
        )
        result = solve_underwriting(inp, target_cap_rate=0.08)
        assert isinstance(result, UnderwritingMetrics)
        assert result.noi > 0
        assert result.cap_rate > 0
        assert result.cash_on_cash > 0
        assert result.mao > 0

    # ── Return type contract ─────────────────────────────────────────────────

    def test_returns_underwriting_metrics(self):
        """Return type is UnderwritingMetrics with all fields."""
        result = solve_underwriting(BASE_INPUT, target_cap_rate=0.08)
        assert isinstance(result, UnderwritingMetrics)
        for field in ("noi", "cap_rate", "cash_on_cash", "mao"):
            assert hasattr(result, field)

    # ── Deterministic ────────────────────────────────────────────────────────

    def test_deterministic(self):
        """Same inputs produce same outputs."""
        a = solve_underwriting(BASE_INPUT, 0.08)
        b = solve_underwriting(BASE_INPUT, 0.08)
        assert a == b

    # ── Performance ──────────────────────────────────────────────────────────

    def test_under_10ms(self):
        """Single solver run completes in under 10ms (trivially)."""
        import time

        start = time.perf_counter()
        for _ in range(10_000):
            solve_underwriting(BASE_INPUT, 0.08)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 10_000
        assert elapsed_ms < 10, (
            f"Average solver took {elapsed_ms:.4f}ms (expected <10ms)"
        )
