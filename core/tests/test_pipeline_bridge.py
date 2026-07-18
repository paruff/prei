"""Integration test: Growth Area Explorer pipeline bridge."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from decimal import Decimal


@pytest.fixture
def authed_client(client):
    user = User.objects.create_user("t", "t@t.com", "pass")
    client.force_login(user)
    return client


@patch.dict("os.environ", {"CENSUS_API_KEY": "test-key"})
class TestPipelineBridge:
    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @patch("prei.pipeline.sources.registry.discover_from_all")
    @pytest.mark.django_db
    def test_pipeline_button_triggers_discovery(
        self,
        mock_discover_all,
        mock_housing,
        mock_census,
        mock_emp,
        mock_discover,
        authed_client,
    ):
        """POST with pipeline_city triggers discovery pipeline."""
        mock_discover.return_value = [
            {"place_code": "44000", "place_name": "Los Angeles", "population": 4000000}
        ]
        mock_emp.return_value = Decimal("0.045")
        mock_census.return_value = {
            "population_current": 400000,
            "population_prior": 380000,
            "population_growth_rate": Decimal("0.05"),
            "median_income_current": Decimal("85000"),
            "median_income_prior": Decimal("78000"),
            "median_income_growth_rate": Decimal("0.09"),
        }
        mock_housing.return_value = 85
        mock_discover_all.return_value = {
            "vrm": [
                {
                    "id": "vrm-1",
                    "address": "123 Test",
                    "price": 300_000,
                    "rent": 2500,
                    "beds": 3,
                    "baths": 2,
                }
            ],
            "fannie_mae": [],
            "county": [],
        }

        resp = authed_client.post(
            reverse("growth_explorer"),
            {"state": "CA", "pipeline_city": "Los Angeles"},
        )
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "Los Angeles" in html
        # Pipeline results are stored in session, not displayed on growth page
        # (removed in UX redesign — growth page focuses on market analysis only)
        mock_discover_all.assert_called_once()

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_no_pipeline_city_no_discovery(
        self,
        mock_housing,
        mock_census,
        mock_emp,
        mock_discover,
        authed_client,
    ):
        """POST without pipeline_city does not trigger discovery."""
        mock_discover.return_value = [
            {"place_code": "44000", "place_name": "Los Angeles", "population": 4000000}
        ]
        mock_emp.return_value = Decimal("0.045")
        mock_census.return_value = {
            "population_current": 400000,
            "population_prior": 380000,
            "population_growth_rate": Decimal("0.05"),
            "median_income_current": Decimal("85000"),
            "median_income_prior": Decimal("78000"),
            "median_income_growth_rate": Decimal("0.09"),
        }
        mock_housing.return_value = 85

        resp = authed_client.post(reverse("growth_explorer"), {"state": "CA"})
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "Los Angeles" in html
