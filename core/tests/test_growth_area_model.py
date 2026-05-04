from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from core.models import GrowthArea


@pytest.mark.django_db
class TestGrowthAreaModel:
    """Tests for the GrowthArea model."""

    def test_growth_area_creation(self):
        """Test creating a GrowthArea instance."""
        area = GrowthArea.objects.create(
            state="CA",
            city_name="Sacramento",
            metro_area="Sacramento-Roseville-Folsom, CA",
            population_growth_rate=Decimal("2.3"),
            employment_growth_rate=Decimal("3.1"),
            median_income_growth=Decimal("4.2"),
            housing_demand_index=82,
            latitude=Decimal("38.5816"),
            longitude=Decimal("-121.4944"),
            data_timestamp=timezone.now(),
        )

        assert area.state == "CA"
        assert area.city_name == "Sacramento"
        assert area.housing_demand_index == 82

    def test_calculate_composite_growth_score(self):
        """Test composite score calculation."""
        area = GrowthArea.objects.create(
            state="CA",
            city_name="Test City",
            metro_area="Test Metro",
            population_growth_rate=Decimal("2.0"),
            employment_growth_rate=Decimal("4.0"),
            median_income_growth=Decimal("3.0"),
            housing_demand_index=80,
            data_timestamp=timezone.now(),
        )

        # Expected: (2.0 * 0.25) + (4.0 * 0.35) + (3.0 * 0.25) + (80 * 0.15)
        # = 0.5 + 1.4 + 0.75 + 12 = 14.65
        expected_score = Decimal("14.65")
        assert area.composite_score == expected_score

    def test_composite_score_with_zero_values(self):
        """Test composite score with zero values."""
        area = GrowthArea.objects.create(
            state="CA",
            city_name="Test City",
            metro_area="Test Metro",
            population_growth_rate=Decimal("0"),
            employment_growth_rate=Decimal("0"),
            median_income_growth=Decimal("0"),
            housing_demand_index=0,
            data_timestamp=timezone.now(),
        )

        assert area.composite_score == Decimal("0")

    def test_composite_score_with_negative_values(self):
        """Test composite score with negative growth rates."""
        area = GrowthArea.objects.create(
            state="CA",
            city_name="Test City",
            metro_area="Test Metro",
            population_growth_rate=Decimal("-1.0"),
            employment_growth_rate=Decimal("-2.0"),
            median_income_growth=Decimal("-1.5"),
            housing_demand_index=50,
            data_timestamp=timezone.now(),
        )

        # Expected: (-1.0 * 0.25) + (-2.0 * 0.35) + (-1.5 * 0.25) + (50 * 0.15)
        # = -0.25 + -0.7 + -0.375 + 7.5 = 6.175
        expected_score = Decimal("6.175")
        assert area.composite_score == expected_score

    def test_string_representation(self):
        """Test the string representation of GrowthArea."""
        area = GrowthArea.objects.create(
            state="TX",
            city_name="Austin",
            metro_area="Austin-Round Rock, TX",
            population_growth_rate=Decimal("3.0"),
            employment_growth_rate=Decimal("4.0"),
            median_income_growth=Decimal("5.0"),
            housing_demand_index=90,
            data_timestamp=timezone.now(),
        )

        assert str(area) == "Austin, TX"

    def test_unique_together_constraint(self):
        """Test that state and city_name must be unique together."""
        timestamp = timezone.now()

        GrowthArea.objects.create(
            state="CA",
            city_name="Sacramento",
            metro_area="Sacramento-Roseville-Folsom, CA",
            population_growth_rate=Decimal("2.3"),
            employment_growth_rate=Decimal("3.1"),
            median_income_growth=Decimal("4.2"),
            housing_demand_index=82,
            data_timestamp=timestamp,
        )

        # Attempting to create duplicate should raise an error
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            GrowthArea.objects.create(
                state="CA",
                city_name="Sacramento",
                metro_area="Different Metro",
                population_growth_rate=Decimal("1.0"),
                employment_growth_rate=Decimal("1.0"),
                median_income_growth=Decimal("1.0"),
                housing_demand_index=50,
                data_timestamp=timestamp,
            )

    def test_ordering_by_data_timestamp(self):
        """Test that GrowthArea objects are ordered by data_timestamp descending."""
        from datetime import timedelta

        now = timezone.now()

        area1 = GrowthArea.objects.create(
            state="CA",
            city_name="City1",
            metro_area="Metro1",
            population_growth_rate=Decimal("1.0"),
            employment_growth_rate=Decimal("1.0"),
            median_income_growth=Decimal("1.0"),
            housing_demand_index=50,
            data_timestamp=now - timedelta(days=2),
        )

        area2 = GrowthArea.objects.create(
            state="CA",
            city_name="City2",
            metro_area="Metro2",
            population_growth_rate=Decimal("1.0"),
            employment_growth_rate=Decimal("1.0"),
            median_income_growth=Decimal("1.0"),
            housing_demand_index=50,
            data_timestamp=now,
        )

        areas = list(GrowthArea.objects.all())
        assert areas[0] == area2  # Most recent first
        assert areas[1] == area1
