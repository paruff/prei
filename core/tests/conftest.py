from __future__ import annotations

import json
from decimal import Decimal

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client(api_client: APIClient, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def auth_client_second(api_client: APIClient, second_user):
    api_client.force_authenticate(user=second_user)
    return api_client


@pytest.fixture
def parse_json():
    def _parse_json(response):
        return json.loads(response.content.decode("utf-8"))

    return _parse_json


@pytest.fixture
def assert_decimal_close():
    def _assert_decimal_close(actual, expected, tolerance: Decimal = Decimal("0.01")):
        actual_decimal = Decimal(str(actual))
        expected_decimal = Decimal(str(expected))
        assert abs(actual_decimal - expected_decimal) <= tolerance

    return _assert_decimal_close
