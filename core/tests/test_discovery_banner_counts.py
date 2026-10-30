from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import GrowthArea, ScreeningCriteria, VrmProperty


@pytest.mark.django_db
def test_banner_counts_screening_verdicts_without_criteria(client):
    user = get_user_model().objects.create_user("banner", password="x")  # noqa: S106
    area = GrowthArea.objects.create(
        state="TX",
        city_name="Austin",
        metro_area="Austin-Round Rock",
        population_growth_rate=Decimal("0.02"),
        employment_growth_rate=Decimal("0.03"),
        median_income_growth=Decimal("0.02"),
        housing_demand_index=80,
        supply_constraint_index=45,
        data_timestamp=timezone.now(),
        population=900000,
        composite_score=Decimal("75.50"),
    )
    now = timezone.now()
    VrmProperty.objects.create(
        vrm_property_id=1,
        vrm_listing_url="https://example.com/1",
        address="1 Count St",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        list_price=Decimal("200000"),
        projected_monthly_rent=Decimal("2000"),
        bedrooms=3,
        bathrooms=Decimal("2"),
        year_built=2001,
        status=VrmProperty.Status.FOR_SALE,
        scraped_at=now,
        last_seen_at=now,
    )
    assert not ScreeningCriteria.objects.filter(user=user).exists()
    client.force_login(user)

    resp = client.post(
        "/discovery/",
        {"growth_area_id": area.pk, "sources": ["vrm"]},
    )

    results = resp.context["discovery_results"]
    assert results["discovered"] == 1
    assert results["screening_passed"] + results["screening_failed"] == 1
