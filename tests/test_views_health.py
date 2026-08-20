"""Tests for data health views (refresh_all_sources, health_json)."""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def logged_in_client():
    User = get_user_model()
    user = User.objects.create_user("test_health_user", "t@t.com", "pass123")
    client = Client()
    client.force_login(user)
    return client


def test_refresh_all_sources_returns_redirect(logged_in_client):
    response = logged_in_client.post("/system/refresh-all/")
    assert response.status_code == 302


def test_refresh_all_sources_rejects_get(logged_in_client):
    response = logged_in_client.get("/system/refresh-all/")
    assert response.status_code == 405


def test_health_json_returns_list(logged_in_client):
    response = logged_in_client.get("/system/health-json/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
