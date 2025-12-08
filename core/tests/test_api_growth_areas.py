from __future__ import annotations

import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient

from core.models import GrowthArea


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return APIClient()


@pytest.fixture
def sample_growth_areas(db):
    """Create sample growth areas for testing."""
    now = timezone.now()

    areas = []

    # California areas
    areas.append(
        GrowthArea.objects.create(
            state="CA",
            city_name="Sacramento",
            metro_area="Sacramento-Roseville-Folsom, CA",
            population_growth_rate=Decimal("2.3"),
            employment_growth_rate=Decimal("3.1"),
            median_income_growth=Decimal("4.2"),
            housing_demand_index=82,
            latitude=Decimal("38.5816"),
            longitude=Decimal("-121.4944"),
            data_timestamp=now,
        )
    )

    areas.append(
        GrowthArea.objects.create(
            state="CA",
            city_name="San Francisco",
            metro_area="San Francisco-Oakland-Berkeley, CA",
            population_growth_rate=Decimal("1.5"),
            employment_growth_rate=Decimal("2.0"),
            median_income_growth=Decimal("3.0"),
            housing_demand_index=70,
            latitude=Decimal("37.7749"),
            longitude=Decimal("-122.4194"),
            data_timestamp=now,
        )
    )

    # Texas area
    areas.append(
        GrowthArea.objects.create(
            state="TX",
            city_name="Austin",
            metro_area="Austin-Round Rock, TX",
            population_growth_rate=Decimal("3.0"),
            employment_growth_rate=Decimal("4.0"),
            median_income_growth=Decimal("5.0"),
            housing_demand_index=90,
            latitude=Decimal("30.2672"),
            longitude=Decimal("-97.7431"),
            data_timestamp=now,
        )
    )

    return areas


@pytest.mark.django_db
class TestGrowthAreasAPI:
    """Integration tests for the growth areas API."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def test_successful_retrieval_for_california(self, api_client, sample_growth_areas):
        """Test successful retrieval of growth areas for California."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "CA"})

        assert response.status_code == 200
        data = response.json()

        assert data["state"] == "CA"
        assert "dataTimestamp" in data
        assert data["totalResults"] == 2
        assert len(data["areas"]) == 2

        # Check first area (should be Sacramento due to higher composite score)
        first_area = data["areas"][0]
        assert "cityName" in first_area
        assert "metroArea" in first_area
        assert "growthMetrics" in first_area
        assert "coordinates" in first_area

        # Check growth metrics structure
        metrics = first_area["growthMetrics"]
        assert "compositeScore" in metrics
        assert "populationGrowthRate" in metrics
        assert "employmentGrowthRate" in metrics
        assert "medianIncomeGrowth" in metrics
        assert "housingDemandIndex" in metrics

    def test_returns_400_for_invalid_state(self, api_client):
        """Test that invalid state codes return 400 error."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "ZZ"})

        assert response.status_code == 400
        data = response.json()

        assert "error" in data
        assert data["code"] == "INVALID_STATE_CODE"
        assert "Invalid state code" in data["error"]

    def test_returns_400_for_missing_state(self, api_client):
        """Test that missing state parameter returns 400 error."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url)

        assert response.status_code == 400
        data = response.json()

        assert data["code"] == "INVALID_STATE_CODE"

    def test_returns_empty_list_for_state_with_no_data(self, api_client, db):
        """Test that states with no data return empty list with message."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "WY"})

        assert response.status_code == 200
        data = response.json()

        assert data["state"] == "WY"
        assert data["totalResults"] == 0
        assert len(data["areas"]) == 0
        assert "message" in data
        assert "No growth data available" in data["message"]

    def test_filter_by_minimum_growth_score(self, api_client, sample_growth_areas):
        """Test filtering by minimum growth score."""
        url = reverse("api:growth-areas-list")

        # Get Sacramento's composite score
        sacramento = sample_growth_areas[0]
        sacramento_score = float(sacramento.composite_score)

        # Request with minGrowthScore just above San Francisco's score
        response = api_client.get(
            url, {"state": "CA", "minGrowthScore": str(sacramento_score - 1)}
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return Sacramento
        assert data["totalResults"] == 1
        assert data["areas"][0]["cityName"] == "Sacramento"

    def test_sort_areas_by_growth_score_descending(self, api_client, sample_growth_areas):
        """Test that areas are sorted by composite score in descending order."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "CA", "minGrowthScore": "0"})

        assert response.status_code == 200
        data = response.json()

        assert len(data["areas"]) == 2

        # Sacramento should be first (higher score)
        assert data["areas"][0]["cityName"] == "Sacramento"
        assert data["areas"][1]["cityName"] == "San Francisco"

        # Verify scores are in descending order
        score1 = float(data["areas"][0]["growthMetrics"]["compositeScore"])
        score2 = float(data["areas"][1]["growthMetrics"]["compositeScore"])
        assert score1 > score2

    def test_response_includes_correct_timestamp(self, api_client, sample_growth_areas):
        """Test that response includes data timestamp."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "CA"})

        assert response.status_code == 200
        data = response.json()

        assert "dataTimestamp" in data
        # Check that it's a valid ISO timestamp
        from datetime import datetime

        timestamp = datetime.fromisoformat(data["dataTimestamp"].replace("Z", "+00:00"))
        assert timestamp is not None

    def test_caching_returns_same_data_within_24_hours(
        self, api_client, sample_growth_areas
    ):
        """Test that caching returns the same data for repeated requests."""
        url = reverse("api:growth-areas-list")

        # First request
        response1 = api_client.get(url, {"state": "CA", "minGrowthScore": "50"})
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request (should be cached)
        response2 = api_client.get(url, {"state": "CA", "minGrowthScore": "50"})
        assert response2.status_code == 200
        data2 = response2.json()

        # Both responses should be identical
        assert data1 == data2

    def test_lowercase_state_code_accepted(self, api_client, sample_growth_areas):
        """Test that lowercase state codes are normalized and accepted."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "ca"})

        assert response.status_code == 200
        data = response.json()

        assert data["state"] == "CA"
        assert data["totalResults"] == 2

    def test_state_code_with_whitespace_accepted(self, api_client, sample_growth_areas):
        """Test that state codes with whitespace are normalized."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": " CA "})

        assert response.status_code == 200
        data = response.json()

        assert data["state"] == "CA"

    def test_invalid_min_growth_score_returns_400(self, api_client, sample_growth_areas):
        """Test that invalid minGrowthScore values return 400."""
        url = reverse("api:growth-areas-list")

        # Test with negative value
        response = api_client.get(url, {"state": "CA", "minGrowthScore": "-10"})
        assert response.status_code == 400

        # Test with value above 100
        response = api_client.get(url, {"state": "CA", "minGrowthScore": "150"})
        assert response.status_code == 400

        # Test with non-numeric value
        response = api_client.get(url, {"state": "CA", "minGrowthScore": "invalid"})
        assert response.status_code == 400

    def test_coordinates_included_in_response(self, api_client, sample_growth_areas):
        """Test that coordinates are included in the response."""
        url = reverse("api:growth-areas-list")
        response = api_client.get(url, {"state": "CA"})

        assert response.status_code == 200
        data = response.json()

        first_area = data["areas"][0]
        assert "coordinates" in first_area
        assert "latitude" in first_area["coordinates"]
        assert "longitude" in first_area["coordinates"]

        # Sacramento coordinates
        if first_area["cityName"] == "Sacramento":
            assert first_area["coordinates"]["latitude"] is not None
            assert first_area["coordinates"]["longitude"] is not None
