from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import Property, PropertyShare

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        username="sharing_owner",
        email="sharing_owner@example.com",
        password="pass1234",
    )


@pytest.fixture
def team_member(db):
    return User.objects.create_user(
        username="sharing_team",
        email="sharing_team@example.com",
        password="pass1234",
    )


@pytest.fixture
def client_user(db):
    return User.objects.create_user(
        username="sharing_client",
        email="sharing_client@example.com",
        password="pass1234",
    )


@pytest.fixture
def property_obj(owner):
    return Property.objects.create(
        user=owner,
        address="123 Sharing St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("320000"),
    )


@pytest.mark.django_db
def test_owner_can_share_with_team_member(client, owner, team_member, property_obj):
    client.force_login(owner)

    response = client.post(
        reverse("property_share", kwargs={"pk": property_obj.pk}),
        data={"email": team_member.email, "role": "team"},
    )

    assert response.status_code == 302
    assert PropertyShare.objects.filter(
        property=property_obj, shared_with=team_member, role="team"
    ).exists()


@pytest.mark.django_db
def test_team_member_can_edit_but_not_delete(client, owner, team_member, property_obj):
    PropertyShare.objects.create(
        property=property_obj, shared_with=team_member, role="team"
    )

    client.force_login(team_member)

    edit_response = client.post(
        reverse("property_edit", kwargs={"pk": property_obj.pk}),
        data={
            "address": "123 Sharing St",
            "city": "Dallas",
            "state": "TX",
            "zip_code": "78701",
            "purchase_price": "320000.00",
            "purchase_date": "2025-01-01",
            "property_type": "single-family",
            "square_footage": "1800",
            "num_units": "1",
            "year_built": "2000",
        },
    )
    assert edit_response.status_code == 302
    property_obj.refresh_from_db()
    assert property_obj.city == "Dallas"

    edit_page = client.get(reverse("property_edit", kwargs={"pk": property_obj.pk}))
    assert edit_page.status_code == 200
    assert "Delete property" not in edit_page.content.decode()

    delete_response = client.post(
        reverse("property_delete", kwargs={"pk": property_obj.pk})
    )
    assert delete_response.status_code == 404
    assert Property.objects.filter(pk=property_obj.pk).exists()


@pytest.mark.django_db
def test_client_can_view_shared_property(client, owner, client_user, property_obj):
    PropertyShare.objects.create(
        property=property_obj,
        shared_with=client_user,
        role="client",
    )

    client.force_login(client_user)

    list_response = client.get(reverse("property_list"))
    assert list_response.status_code == 200
    assert property_obj.address in list_response.content.decode()

    detail_response = client.get(
        reverse("property_detail", kwargs={"pk": property_obj.pk})
    )
    assert detail_response.status_code == 200


@pytest.mark.django_db
def test_client_cannot_edit_shared_property(client, owner, client_user, property_obj):
    PropertyShare.objects.create(
        property=property_obj,
        shared_with=client_user,
        role="client",
    )

    client.force_login(client_user)

    response = client.get(reverse("property_edit", kwargs={"pk": property_obj.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_client_cannot_view_unshared_property(client, client_user, property_obj):
    client.force_login(client_user)

    response = client.get(reverse("property_detail", kwargs={"pk": property_obj.pk}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_only_owner_can_share(client, owner, team_member, property_obj):
    PropertyShare.objects.create(
        property=property_obj, shared_with=team_member, role="team"
    )

    client.force_login(team_member)

    response = client.post(
        reverse("property_share", kwargs={"pk": property_obj.pk}),
        data={"email": "sharing_client@example.com", "role": "client"},
    )

    assert response.status_code == 404
