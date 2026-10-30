"""Screening rent chain reaches HUD Small Area FMR for a Dallas listing (G1.8)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import GrowthArea, PipelineProperty
from core.services.screening import _get_monthly_rent

pytestmark = pytest.mark.django_db


def _fmr_response() -> dict:
    return {
        "data": {
            "basicdata": [
                {
                    "zip_code": "75201",
                    "Efficiency": "1200",
                    "One-Bedroom": "1450",
                    "Two-Bedroom": "1700",
                    "Three-Bedroom": "2150",
                    "Four-Bedroom": "2500",
                },
                {
                    "zip_code": "MSA level",
                    "Efficiency": "1000",
                    "One-Bedroom": "1250",
                    "Two-Bedroom": "1500",
                    "Three-Bedroom": "1900",
                    "Four-Bedroom": "2250",
                },
            ]
        }
    }


@pytest.fixture
def dallas_listing() -> PipelineProperty:
    GrowthArea.objects.create(
        state="TX",
        city_name="Dallas",
        county_fips="48113",
        population_growth_rate=Decimal("1"),
        median_income_growth=Decimal("1"),
        housing_demand_index=100,
        data_timestamp=timezone.now(),
    )
    user = get_user_model().objects.create_user("u", password="p")
    return PipelineProperty.objects.create(
        user=user,
        source_type=PipelineProperty.SourceType.VRM,
        source_id="VRM-DAL-1",
        address="1 Main St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        beds=0,
        price=Decimal("200000"),
        discovered_at=timezone.now(),
    )


def test_hud_small_area_fmr_reaches_screening(dallas_listing: PipelineProperty) -> None:
    with (
        patch("core.integrations.market.hud_fmr.settings") as s,
        patch("core.integrations.market.hud_fmr.FMRClient._get") as get,
    ):
        s.HUD_API_KEY = "k"
        get.return_value = _fmr_response()
        rent = _get_monthly_rent(dallas_listing, None, cache_rent=False)

    assert rent == Decimal("1200")  # studio ZIP row, not the 2BR default
    assert get.call_args.args[0] == "data/4811399999"


def test_no_growth_area_means_no_hud_rent(dallas_listing: PipelineProperty) -> None:
    GrowthArea.objects.all().delete()
    with (
        patch("core.integrations.market.hud_fmr.settings") as s,
        patch("core.integrations.market.hud_fmr.FMRClient._get") as get,
    ):
        s.HUD_API_KEY = "k"
        assert _get_monthly_rent(dallas_listing, None, cache_rent=False) is None
    get.assert_not_called()
