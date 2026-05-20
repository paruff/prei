from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from core.models import VrmProperty


def make_vrm_property(**overrides: Decimal | str | bool | int | None) -> VrmProperty:
    data = {
        "vrm_property_id": 5001,
        "vrm_listing_url": "https://www.vrmproperties.com/properties/5001",
        "address": "369 Charles St",
        "city": "Winchester",
        "state": "VA",
        "zip_code": "22601",
        "status": VrmProperty.Status.FOR_SALE,
        "vendee_eligible": True,
        "scraped_at": timezone.now(),
        "last_seen_at": timezone.now(),
        "list_price": Decimal("225000.00"),
        "projected_monthly_rent": Decimal("1800.00"),
        "estimated_rehab": Decimal("15000.00"),
    }
    data.update(overrides)
    return VrmProperty.objects.create(**data)


@pytest.mark.django_db
@override_settings(
    VACANCY_RATE_PCT=8,
    MGMT_FEE_PCT=10,
    MAINTENANCE_PCT_OF_VALUE=1,
    INSURANCE_ANNUAL=1200,
    TAX_RATE_PCT=1.2,
    MIN_PROFIT_MARGIN_PCT=10,
)
def test_calculate_profitability_computes_and_persists_fields():
    vrm_property = make_vrm_property()

    vrm_property.calculate_profitability()
    vrm_property.refresh_from_db()

    assert vrm_property.gross_annual_rent == Decimal("21600.00")
    assert vrm_property.effective_gross_rent == Decimal("19872.00")
    assert vrm_property.annual_expenses == Decimal("8137.20")
    assert vrm_property.noi == Decimal("11734.80")
    assert vrm_property.total_investment == Decimal("240000.00")
    assert vrm_property.cap_rate == Decimal("4.89")
    assert vrm_property.profit_margin_pct == Decimal("59.05")
    assert vrm_property.meets_profit_target is True


@pytest.mark.django_db
def test_profitable_candidates_manager_filters_on_meets_profit_target():
    passing = make_vrm_property(
        vrm_property_id=5002, projected_monthly_rent=Decimal("1800")
    )
    failing = make_vrm_property(
        vrm_property_id=5003, projected_monthly_rent=Decimal("100")
    )

    passing.calculate_profitability()
    failing.calculate_profitability()

    assert passing in VrmProperty.profitable_candidates.all()
    assert failing not in VrmProperty.profitable_candidates.all()


@pytest.mark.django_db
def test_calculate_profitability_handles_zero_and_missing_inputs():
    zero_rent = make_vrm_property(
        vrm_property_id=5004, projected_monthly_rent=Decimal("0")
    )
    zero_rehab = make_vrm_property(vrm_property_id=5005, estimated_rehab=Decimal("0"))
    no_list_price = make_vrm_property(
        vrm_property_id=5006, list_price=None, estimated_rehab=Decimal("15000")
    )

    zero_rent.calculate_profitability()
    zero_rehab.calculate_profitability()
    no_list_price.calculate_profitability()

    zero_rent.refresh_from_db()
    zero_rehab.refresh_from_db()
    no_list_price.refresh_from_db()

    assert zero_rent.gross_annual_rent == Decimal("0.00")
    assert zero_rent.profit_margin_pct == Decimal("0.00")
    assert zero_rent.meets_profit_target is False
    assert zero_rehab.total_investment == Decimal("225000.00")
    assert no_list_price.total_investment == Decimal("15000.00")
