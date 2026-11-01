from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from core.models import UserInvestmentTargets


def test_dashboard_redirects_anonymous(client):
    response = client.get(reverse("dashboard"))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


def test_health_check_returns_ok(client, db):
    response = client.get(reverse("health_check"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_returns_503_when_db_unreachable(client):
    with patch(
        "django.db.connection.cursor", side_effect=Exception("connection refused")
    ):
        response = client.get(reverse("health_check"))

    assert response.status_code == 503
    assert response.json()["status"] == "error"


def test_dashboard_returns_200_for_logged_in_user(client, user):
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200


def test_dashboard_shows_property_kpis(client, user, full_sfr):
    UserInvestmentTargets.objects.create(
        user=user,
        min_coc_pct=Decimal("0.08"),
        min_dscr=Decimal("1.25"),
        max_grm=Decimal("12.00"),
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert full_sfr["property"].address in content
    # Dashboard shows Deal Screener with score bar for the property
    assert "Deal screener" in content
    assert "score-bar-track" in content


def test_property_list_excludes_other_users_properties(
    client, user, property_sfr, property_owned_by_second_user
):
    client.force_login(user)

    response = client.get(reverse("property_list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert property_sfr.address in content
    assert property_owned_by_second_user.address not in content


def test_property_detail_404_for_wrong_user(
    client, user, property_owned_by_second_user
):
    client.force_login(user)

    response = client.get(
        reverse("property_detail", kwargs={"pk": property_owned_by_second_user.pk})
    )

    assert response.status_code == 404


def test_investment_targets_save_leaves_screening_preferences(client, user):
    from core.models import UserScreeningPreferences

    UserScreeningPreferences.objects.create(user=user, min_beds=3, min_baths=2)
    client.force_login(user)
    url = reverse("investment_targets_edit")
    form = client.get(url).context["form"]
    data = {k: v for k, v in form.initial.items() if v is not None}

    response = client.post(url, data)

    assert response.status_code in (200, 302)
    prefs = UserScreeningPreferences.objects.get(user=user)
    assert (prefs.min_beds, prefs.min_baths) == (3, 2)
