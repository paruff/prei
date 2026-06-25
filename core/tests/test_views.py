from decimal import Decimal

from django.urls import reverse

from core.models import UserInvestmentTargets


def test_dashboard_redirects_anonymous(client):
    response = client.get(reverse("dashboard"))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


def test_health_check_returns_ok(client):
    response = client.get(reverse("health_check"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
