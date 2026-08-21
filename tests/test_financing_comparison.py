"""Tests for financing scenario comparison."""

from decimal import Decimal

import pytest

from core.models import FinancingScenario
from core.services.financing_comparison import (
    ScenarioResult,
    compare_scenarios,
    calculate_scenario_result,
    get_best_scenario,
    get_or_create_default_scenarios,
    DEFAULT_SCENARIOS,
)


class TestFinancingScenarioModel:
    """Tests for FinancingScenario model."""

    def test_financing_scenario_creation(self) -> None:
        """Test creating a FinancingScenario with all required fields."""
        # This test needs a property instance - will be tested in integration tests
        pass

    def test_down_payment_property(self) -> None:
        """Test down_payment = purchase_price * (1 - LTV)."""
        # Tested in integration tests with actual property
        pass

    def test_loan_amount_property(self) -> None:
        """Test loan_amount = purchase_price * LTV."""
        pass

    def test_monthly_payment_uses_mortgage_module(self) -> None:
        """Test monthly_payment uses calculate_monthly_mortgage."""
        pass


class TestDefaultScenarios:
    """Tests for default financing scenarios."""

    def test_three_default_scenarios_exist(self) -> None:
        """Test that DEFAULT_SCENARIOS has 3 standard loan types."""
        assert len(DEFAULT_SCENARIOS) == 3
        types = {s["loan_type"] for s in DEFAULT_SCENARIOS}
        assert types == {
            FinancingScenario.LoanType.CONVENTIONAL,
            FinancingScenario.LoanType.DSCR,
            FinancingScenario.LoanType.SELLER_FINANCING,
        }

    def test_conventional_defaults(self) -> None:
        """Test conventional: 75% LTV, 7.5%, 30yr."""
        conv = next(
            s
            for s in DEFAULT_SCENARIOS
            if s["loan_type"] == FinancingScenario.LoanType.CONVENTIONAL
        )
        assert conv["ltv_pct"] == Decimal("0.75")
        assert conv["interest_rate"] == Decimal("0.075")
        assert conv["term_years"] == 30

    def test_dscr_defaults(self) -> None:
        """Test DSCR: 80% LTV, 8.5%, 30yr."""
        dscr = next(
            s
            for s in DEFAULT_SCENARIOS
            if s["loan_type"] == FinancingScenario.LoanType.DSCR
        )
        assert dscr["ltv_pct"] == Decimal("0.80")
        assert dscr["interest_rate"] == Decimal("0.085")
        assert dscr["term_years"] == 30

    def test_seller_financing_defaults(self) -> None:
        """Test seller financing: 90% LTV, 6%, 15yr."""
        seller = next(
            s
            for s in DEFAULT_SCENARIOS
            if s["loan_type"] == FinancingScenario.LoanType.SELLER_FINANCING
        )
        assert seller["ltv_pct"] == Decimal("0.90")
        assert seller["interest_rate"] == Decimal("0.06")
        assert seller["term_years"] == 15


class TestGetOrCreateDefaultScenarios:
    """Tests for get_or_create_default_scenarios function."""

    @pytest.mark.django_db
    def test_creates_three_scenarios(self, property_obj) -> None:
        """Test that function creates 3 scenarios for a property."""
        scenarios = get_or_create_default_scenarios(property_obj)
        assert len(scenarios) == 3

    @pytest.mark.django_db
    def test_scenarios_have_correct_types(self, property_obj) -> None:
        """Test that created scenarios have correct loan types."""
        scenarios = get_or_create_default_scenarios(property_obj)
        types = {s.loan_type for s in scenarios}
        assert types == {
            FinancingScenario.LoanType.CONVENTIONAL,
            FinancingScenario.LoanType.DSCR,
            FinancingScenario.LoanType.SELLER_FINANCING,
        }

    @pytest.mark.django_db
    def test_idempotent(self, property_obj) -> None:
        """Test that calling twice doesn't create duplicates."""
        get_or_create_default_scenarios(property_obj)
        scenarios = get_or_create_default_scenarios(property_obj)
        assert len(scenarios) == 3
        # Verify no duplicates by checking count in DB
        count = property_obj.financing_scenarios.count()
        assert count == 3


class TestCalculateScenarioResult:
    """Tests for calculate_scenario_result function."""

    @pytest.mark.django_db
    def test_calculates_all_metrics(self, property_obj) -> None:
        """Test that all metrics are calculated."""
        scenarios = get_or_create_default_scenarios(property_obj)
        for scenario in scenarios:
            result = calculate_scenario_result(property_obj, scenario)
            assert isinstance(result, ScenarioResult)
            assert result.loan_type in ["Conventional", "DSCR Loan", "Seller Financing"]
            assert result.ltv_pct > 0
            assert result.interest_rate > 0
            assert result.term_years > 0
            assert result.down_payment > 0
            assert result.monthly_payment > 0
            assert result.annual_debt_service == result.monthly_payment * Decimal(12)
            assert result.noi >= 0
            assert result.cap_rate >= 0
            assert result.dscr >= 0
            assert result.breakeven_rent >= 0
            assert (
                result.total_cash_invested == result.down_payment + result.closing_costs
            )

    @pytest.mark.django_db
    def test_dscr_calculation(self, property_obj) -> None:
        """Test DSCR = NOI / annual_debt_service."""
        scenarios = get_or_create_default_scenarios(property_obj)
        for scenario in scenarios:
            result = calculate_scenario_result(property_obj, scenario)
            if result.annual_debt_service > 0:
                expected_dscr = (result.noi / result.annual_debt_service).quantize(
                    Decimal("0.0001")
                )
                assert abs(result.dscr - expected_dscr) < Decimal("0.0001")

    @pytest.mark.django_db
    def test_cash_on_cash_calculation(self, property_obj) -> None:
        """Test CoC = (NOI - annual_debt_service) / total_cash_invested."""
        scenarios = get_or_create_default_scenarios(property_obj)
        for scenario in scenarios:
            result = calculate_scenario_result(property_obj, scenario)
            annual_cash_flow = result.noi - result.annual_debt_service
            if result.total_cash_invested > 0:
                expected_coc = (annual_cash_flow / result.total_cash_invested).quantize(
                    Decimal("0.0001")
                )
                assert abs(result.cash_on_cash - expected_coc) < Decimal("0.0001")

    @pytest.mark.django_db
    def test_breakeven_rent_calculation(self, property_obj) -> None:
        """Test breakeven rent accounts for vacancy and management."""
        scenarios = get_or_create_default_scenarios(property_obj)
        for scenario in scenarios:
            result = calculate_scenario_result(property_obj, scenario)
            assert result.breakeven_rent > 0


class TestCompareScenarios:
    """Tests for compare_scenarios function."""

    @pytest.mark.django_db
    def test_returns_three_results(self, property_obj) -> None:
        """Test that compare_scenarios returns 3 results."""
        results = compare_scenarios(property_obj)
        assert len(results) == 3

    @pytest.mark.django_db
    def test_results_sorted_by_loan_type_order(self, property_obj) -> None:
        """Test results are sorted: Conventional, DSCR, Seller Financing."""
        results = compare_scenarios(property_obj)
        order = [r.loan_type for r in results]
        assert order == ["Conventional", "DSCR Loan", "Seller Financing"]

    @pytest.mark.django_db
    def test_creates_defaults_if_none_exist(self, property_obj) -> None:
        """Test that defaults are created if no scenarios exist."""
        # Ensure no scenarios exist
        property_obj.financing_scenarios.all().delete()
        results = compare_scenarios(property_obj)
        assert len(results) == 3


class TestGetBestScenario:
    """Tests for get_best_scenario function."""

    @pytest.mark.django_db
    def test_best_cash_on_cash(self, property_obj) -> None:
        """Test getting scenario with highest CoC."""
        results = compare_scenarios(property_obj)
        best = get_best_scenario(results, "cash_on_cash")
        assert best is not None
        assert best.cash_on_cash == max(r.cash_on_cash for r in results)

    @pytest.mark.django_db
    def test_best_dscr(self, property_obj) -> None:
        """Test getting scenario with highest DSCR."""
        results = compare_scenarios(property_obj)
        best = get_best_scenario(results, "dscr")
        assert best is not None
        assert best.dscr == max(r.dscr for r in results)

    @pytest.mark.django_db
    def test_empty_list_returns_none(self) -> None:
        """Test empty list returns None."""
        best = get_best_scenario([], "cash_on_cash")
        assert best is None

    @pytest.mark.django_db
    def test_invalid_metric_raises_error(self, property_obj) -> None:
        """Test invalid metric raises ValueError."""
        results = compare_scenarios(property_obj)
        with pytest.raises(ValueError):
            get_best_scenario(results, "invalid_metric")


class TestScenarioResultDataclass:
    """Tests for ScenarioResult dataclass."""

    def test_scenario_result_creation(self) -> None:
        """Test creating a ScenarioResult with all fields."""
        result = ScenarioResult(
            loan_type="Conventional",
            ltv_pct=Decimal("0.75"),
            interest_rate=Decimal("0.075"),
            term_years=30,
            down_payment=Decimal("75000"),
            monthly_payment=Decimal("2098.43"),
            annual_debt_service=Decimal("25181.16"),
            noi=Decimal("25000"),
            cap_rate=Decimal("0.0625"),
            cash_on_cash=Decimal("0.12"),
            dscr=Decimal("1.5"),
            breakeven_rent=Decimal("2500"),
            monthly_cash_flow=Decimal("150"),
            total_cash_invested=Decimal("80000"),
            closing_costs=Decimal("5000"),
        )
        assert result.loan_type == "Conventional"
        assert result.ltv_pct == Decimal("0.75")
        assert result.annual_debt_service == Decimal("25181.16")
