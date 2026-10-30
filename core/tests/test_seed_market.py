from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.management import call_command

from core.management.commands import seed_market as seed_market_command
from core.models import GrowthArea


@pytest.mark.django_db
def test_seed_market_dallas_fixture_gacs_is_sane_without_live_data(monkeypatch) -> None:
    GrowthArea.objects.filter(state="TX", city_name="Dallas").delete()

    def _fake_call_command(*args, **kwargs):
        return None

    monkeypatch.setattr(seed_market_command, "call_command", _fake_call_command)
    monkeypatch.setattr(seed_market_command, "FIXTURE_VRM_LISTINGS", ())

    call_command("seed_market", state="TX", city="Dallas")

    area = GrowthArea.objects.get(state="TX", city_name="Dallas")
    assert Decimal("0") <= area.composite_score <= Decimal("100")
