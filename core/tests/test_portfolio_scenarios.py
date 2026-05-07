"""Tests for portfolio what-if scenario modeling (Phase 4.1)."""

import pytest
from datetime import date
from decimal import Decimal

from core.models import Property, RentalIncome, OperatingExpense
from core.services.portfolio import aggregate_portfolio, compare_scenarios, run_scenario

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_property(user, purchase_price: str = "200000") -> Property:
    return Property.objects.create(
        user=user,
        address="1 Test St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal(purchase_price),
    )


def _add_rental_income(
    prop: Property, monthly_rent: str = "2000", vacancy_rate: str = "0.05"
) -> RentalIncome:
    return RentalIncome.objects.create(
        property=prop,
        monthly_rent=Decimal(monthly_rent),
        effective_date=date(2024, 1, 1),
        vacancy_rate=Decimal(vacancy_rate),
    )


def _add_expense(prop: Property, amount: str = "500") -> OperatingExpense:
    return OperatingExpense.objects.create(
        property=prop,
        category="maintenance",
        amount=Decimal(amount),
        frequency=OperatingExpense.Frequency.MONTHLY,
        effective_date=date(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# run_scenario tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_run_scenario_high_vacancy_reduces_noi(user):
    """run_scenario with vacancy_rate=0.5 produces NOI lower than baseline."""
    prop = _make_property(user)
    _add_rental_income(prop, monthly_rent="2000", vacancy_rate="0.05")
    _add_expense(prop, amount="500")

    baseline = aggregate_portfolio(user)
    result = run_scenario(user, {"vacancy_rate": Decimal("0.5")})

    assert result["total_noi"] < baseline["total_noi"]


@pytest.mark.django_db
def test_run_scenario_price_decrease_raises_cap_rate(user):
    """run_scenario with purchase_price_delta_pct=-10 produces a higher cap rate."""
    prop = _make_property(user, purchase_price="200000")
    _add_rental_income(prop, monthly_rent="2000", vacancy_rate="0.05")
    _add_expense(prop, amount="300")

    baseline = run_scenario(user, {})
    result = run_scenario(user, {"purchase_price_delta_pct": Decimal("-10")})

    assert result["avg_cap_rate"] > baseline["avg_cap_rate"]


@pytest.mark.django_db
def test_run_scenario_no_properties_returns_zero_kpis(user):
    """User with no properties returns zeroed KPIs without raising an exception."""
    result = run_scenario(user, {"vacancy_rate": Decimal("0.1")})

    assert result == {
        "total_noi": Decimal("0"),
        "avg_cap_rate": Decimal("0"),
        "avg_coc": Decimal("0"),
    }


@pytest.mark.django_db
def test_run_scenario_purchase_price_delta_to_zero_returns_zero_kpis(user):
    """Divide-by-zero guard: when purchase_price reaches zero after delta, return zero KPIs."""
    prop = _make_property(user, purchase_price="100000")
    _add_rental_income(prop, monthly_rent="1500", vacancy_rate="0.05")

    # -100 % delta → effective price = 0
    result = run_scenario(user, {"purchase_price_delta_pct": Decimal("-100")})

    assert result["avg_cap_rate"] == Decimal("0")
    assert result["avg_coc"] == Decimal("0")


@pytest.mark.django_db
def test_run_scenario_returns_expected_keys(user):
    """run_scenario always returns total_noi, avg_cap_rate, avg_coc keys."""
    result = run_scenario(user, {})

    assert set(result.keys()) == {"total_noi", "avg_cap_rate", "avg_coc"}


# ---------------------------------------------------------------------------
# compare_scenarios tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_compare_scenarios_returns_named_results(user):
    """compare_scenarios with two named scenarios returns list with correct labels."""
    prop = _make_property(user)
    _add_rental_income(prop, monthly_rent="1800", vacancy_rate="0.05")

    scenarios = [
        {"label": "Optimistic", "vacancy_rate": Decimal("0.03")},
        {"label": "Pessimistic", "vacancy_rate": Decimal("0.15")},
    ]
    results = compare_scenarios(user, scenarios)

    assert len(results) == 2
    assert results[0]["label"] == "Optimistic"
    assert results[1]["label"] == "Pessimistic"


@pytest.mark.django_db
def test_compare_scenarios_default_label_when_missing(user):
    """compare_scenarios falls back to 'Scenario N' when label is absent."""
    results = compare_scenarios(user, [{}, {}])

    assert results[0]["label"] == "Scenario 1"
    assert results[1]["label"] == "Scenario 2"


@pytest.mark.django_db
def test_compare_scenarios_each_result_has_kpi_keys(user):
    """Every scenario result contains the three KPI keys."""
    prop = _make_property(user)
    _add_rental_income(prop)

    results = compare_scenarios(user, [{"label": "A"}, {"label": "B"}])

    for r in results:
        assert "total_noi" in r
        assert "avg_cap_rate" in r
        assert "avg_coc" in r


@pytest.mark.django_db
def test_compare_scenarios_empty_list_returns_empty(user):
    """compare_scenarios with empty scenario list returns empty list."""
    assert compare_scenarios(user, []) == []
