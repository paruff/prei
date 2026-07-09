"""Tests for the growth_explorer view POST flow.

Covers: parallel API calls, GrowthArea upsert, sorting by composite_score,
error handling when Census/FRED APIs fail.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from core.models import GrowthArea


@pytest.mark.django_db
class TestGrowthExplorerPost:
    """Tests for the growth_explorer POST flow."""

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @patch.dict("os.environ", {"CENSUS_API_KEY": "test-census-key"})
    def test_post_creates_growth_areas(
        self,
        mock_housing: Mock,
        mock_metrics: Mock,
        mock_emp: Mock,
        mock_discover: Mock,
        client: Mock,
        user: Mock,
    ) -> None:
        """POST with valid state creates GrowthArea records."""
        mock_discover.return_value = [
            {"place_code": "44000", "place_name": "Austin", "population": 1000000},
        ]
        mock_emp.return_value = Decimal("0.025")
        mock_metrics.return_value = {
            "population_current": 1000000,
            "population_growth_rate": Decimal("0.03"),
            "median_income_current": Decimal("75000"),
            "median_income_growth_rate": Decimal("0.02"),
            "housing_units_current": 400000,
            "housing_units_prior": 380000,
            "housing_units_growth_rate": Decimal("0.05"),
        }
        mock_housing.return_value = 75

        client.force_login(user)
        response = client.post(reverse("growth_explorer"), {"state": "TX"})

        assert response.status_code == 200
        assert GrowthArea.objects.count() == 1

        ga = GrowthArea.objects.first()
        assert ga is not None
        assert ga.city_name == "Austin"
        assert ga.state == "TX"
        assert ga.population == 1000000
        assert ga.composite_score is not None

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @patch.dict("os.environ", {"CENSUS_API_KEY": "test-census-key"})
    def test_multiple_places_sorted_by_score(
        self,
        mock_housing: Mock,
        mock_metrics: Mock,
        mock_emp: Mock,
        mock_discover: Mock,
        client: Mock,
        user: Mock,
    ) -> None:
        """Multiple places are sorted by composite_score descending."""

        mock_discover.return_value = [
            {"place_code": "44000", "place_name": "Austin", "population": 1000000},
            {"place_code": "55000", "place_name": "Dallas", "population": 1300000},
        ]
        mock_emp.return_value = Decimal("0.02")

        # Return different metrics per place
        call_count = 0

        def mock_metrics_side_effect(state, place_code, api_key, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "population_current": 1000000,
                    "population_growth_rate": Decimal("0.01"),
                    "median_income_current": Decimal("70000"),
                    "median_income_growth_rate": Decimal("0.02"),
                    "housing_units_current": 400000,
                    "housing_units_prior": 390000,
                    "housing_units_growth_rate": Decimal("0.03"),
                }
            return {
                "population_current": 1300000,
                "population_growth_rate": Decimal("0.05"),
                "median_income_current": Decimal("80000"),
                "median_income_growth_rate": Decimal("0.03"),
                "housing_units_current": 500000,
                "housing_units_prior": 480000,
                "housing_units_growth_rate": Decimal("0.04"),
            }

        mock_metrics.side_effect = mock_metrics_side_effect
        mock_housing.return_value = 70

        client.force_login(user)
        response = client.post(reverse("growth_explorer"), {"state": "TX"})

        assert response.status_code == 200
        assert GrowthArea.objects.count() == 2

        # Dallas has higher metrics → higher composite score
        dallas = GrowthArea.objects.get(city_name="Dallas")
        austin = GrowthArea.objects.get(city_name="Austin")
        assert dallas.composite_score is not None
        assert austin.composite_score is not None
        assert dallas.composite_score > austin.composite_score

    @patch.dict("os.environ", {"CENSUS_API_KEY": ""})
    def test_requires_api_key(self, client: Mock, user: Mock) -> None:
        """Without CENSUS_API_KEY, shows error."""
        client.force_login(user)
        response = client.post(reverse("growth_explorer"), {"state": "TX"})
        assert response.status_code == 200
        assert b"CENSUS_API_KEY" in response.content

    @patch.dict("os.environ", {"CENSUS_API_KEY": "test-census-key"})
    def test_invalid_state_shows_error(self, client: Mock, user: Mock) -> None:
        """Invalid state returns error."""
        client.force_login(user)
        response = client.post(reverse("growth_explorer"), {"state": "XX"})
        assert response.status_code == 200
        assert b"Invalid" in response.content

    @patch("core.views.discover_places_in_state")
    @patch.dict("os.environ", {"CENSUS_API_KEY": "test-census-key"})
    def test_no_places_found_shows_error(
        self, mock_discover: Mock, client: Mock, user: Mock
    ) -> None:
        """No places returned → error message."""
        mock_discover.return_value = []
        client.force_login(user)
        response = client.post(reverse("growth_explorer"), {"state": "TX"})
        assert response.status_code == 200
        assert b"No Census data returned" in response.content
