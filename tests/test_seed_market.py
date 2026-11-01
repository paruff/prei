"""seed_market loads one market (growth area + GACS, properties, rents) in one command."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from django.utils import timezone

from core.models import GrowthArea, Property, RentalIncome

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_seed_market_default_dallas_falls_back_to_fixture(monkeypatch) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    call_command("seed_market")
    area = GrowthArea.objects.get(state="TX", city_name="Dallas")
    assert area.composite_score_display() is not None
    assert Property.objects.exists()
    assert RentalIncome.objects.exists()


def test_seed_market_is_idempotent(monkeypatch) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    call_command("seed_market")
    call_command("seed_market")
    assert GrowthArea.objects.filter(state="TX", city_name="Dallas").count() == 1


def test_seed_market_unknown_city_without_data_errors(monkeypatch) -> None:
    from django.core.management.base import CommandError

    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_market", city="Nowhere", state="ZZ")


def test_seed_market_fixture_is_refreshed_from_live_data_on_second_run(
    monkeypatch,
) -> None:
    from decimal import Decimal

    from core.management.commands import populate_growth_areas as pga

    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    call_command("seed_market")
    placeholder = GrowthArea.objects.get(state="TX", city_name="Dallas")
    assert placeholder.housing_demand_index == 72

    monkeypatch.setenv("CENSUS_API_KEY", "test-key")
    monkeypatch.setattr(
        pga,
        "fetch_place_growth_metrics",
        lambda **kw: {
            "population_growth_rate": Decimal("0.05"),
            "median_income_growth_rate": Decimal("0.06"),
            "housing_units_growth_rate": Decimal("0.02"),
            "population_current": 1300000,
        },
    )
    monkeypatch.setattr(pga, "fetch_housing_demand_index", lambda **kw: 88)
    monkeypatch.setattr(
        pga.FREDAdapter,
        "fetch_state_employment_growth",
        lambda self, state_code: Decimal("0.03"),
    )
    monkeypatch.setattr(pga, "fetch_fmr_data", lambda *a, **kw: None)
    monkeypatch.setattr(
        "core.integrations.market.qcew_adapter.fetch_county_employment_growth",
        lambda *a, **kw: None,
    )
    call_command("seed_market")

    area = GrowthArea.objects.get(state="TX", city_name="Dallas")
    assert area.housing_demand_index == 88
    assert area.population_growth_rate == Decimal("0.05")


def test_seed_market_other_city_gets_no_dallas_listings(monkeypatch) -> None:
    from core.models import VrmProperty

    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    call_command("seed_market")
    dallas = set(
        VrmProperty.objects.filter(city="Dallas").values_list("vrm_property_id", "city")
    )
    assert dallas

    GrowthArea.objects.create(
        state="TX",
        city_name="Austin",
        population_growth_rate=0,
        employment_growth_rate=0,
        median_income_growth=0,
        housing_demand_index=50,
        supply_constraint_index=50,
        data_timestamp=timezone.now(),
    )
    call_command("seed_market", city="Austin", state="TX")

    assert not VrmProperty.objects.filter(city="Austin").exists()
    assert (
        not VrmProperty.objects.exclude(city="Dallas")
        .filter(zip_code__in=["75201", "75204"])
        .exists()
    )
    assert (
        set(
            VrmProperty.objects.filter(city="Dallas").values_list(
                "vrm_property_id", "city"
            )
        )
        == dallas
    )
