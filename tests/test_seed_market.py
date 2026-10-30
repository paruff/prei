"""seed_market loads one market (growth area + GACS, properties, rents) in one command."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from core.models import GrowthArea, Property, RentalIncome

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_seed_market_default_dallas_falls_back_to_fixture(monkeypatch) -> None:
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    call_command("seed_market")
    area = GrowthArea.objects.get(state="TX", city_name="Dallas")
    assert area.composite_score_display is not None
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
