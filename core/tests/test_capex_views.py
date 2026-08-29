"""Tests for the CapEx item edit view (GitHub issue #395)."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from core.models import CapExItem


@pytest.fixture
def capex_item(db, make_property, user):
    prop = make_property(user=user)
    return CapExItem.objects.create(
        prop=prop,
        component_type=CapExItem.ComponentType.ROOF,
        replacement_cost=Decimal("12000"),
        useful_life_years=25,
        age_years=5,
    )


@pytest.mark.django_db
class TestCapExItemEdit:
    def test_get_renders_form_with_current_values(self, client, user, capex_item):
        client.force_login(user)
        response = client.get(reverse("capex_item_edit", kwargs={"pk": capex_item.pk}))
        assert response.status_code == 200
        assert response.context["form"].instance == capex_item

    def test_post_updates_item_and_redirects_to_property_detail(
        self, client, user, capex_item
    ):
        client.force_login(user)
        response = client.post(
            reverse("capex_item_edit", kwargs={"pk": capex_item.pk}),
            {
                "replacement_cost": "15000",
                "useful_life_years": "20",
                "age_years": "6",
                "notes": "Replaced quote from contractor",
            },
        )
        assert response.status_code == 302
        assert response.url == reverse(
            "property_detail", kwargs={"pk": capex_item.prop.pk}
        )
        capex_item.refresh_from_db()
        assert capex_item.replacement_cost == Decimal("15000")
        assert capex_item.useful_life_years == 20
        assert capex_item.age_years == 6

    def test_non_owner_gets_404(self, client, second_user, capex_item):
        client.force_login(second_user)
        response = client.get(reverse("capex_item_edit", kwargs={"pk": capex_item.pk}))
        assert response.status_code == 404


@pytest.mark.django_db
def test_capex_kpi_visible_without_underwriting_score(client, user, capex_item):
    """Annual CapEx Reserve KPI must not depend on an unrelated underwriting score.

    Regression test for GitHub issue #395: the KPI was previously gated behind
    ``{% if score %}``, so it silently disappeared whenever scoring failed and
    ``score`` stayed None (property_detail swallows scoring errors).
    """
    client.force_login(user)
    with patch(
        "core.services.scoring.score_listing_v2",
        side_effect=RuntimeError("scoring unavailable"),
    ):
        response = client.get(
            reverse("property_detail", kwargs={"pk": capex_item.prop.pk})
        )
    assert response.status_code == 200
    assert response.context["score"] is None
    content = response.content.decode()
    assert "Annual CapEx Reserve" in content
