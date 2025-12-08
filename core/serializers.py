from __future__ import annotations

from rest_framework import serializers

from .models import GrowthArea


class GrowthMetricsSerializer(serializers.Serializer):
    """Serializer for growth metrics nested object."""

    compositeScore = serializers.DecimalField(
        max_digits=6, decimal_places=2, source="composite_score"
    )
    populationGrowthRate = serializers.DecimalField(
        max_digits=6, decimal_places=2, source="population_growth_rate"
    )
    employmentGrowthRate = serializers.DecimalField(
        max_digits=6, decimal_places=2, source="employment_growth_rate"
    )
    medianIncomeGrowth = serializers.DecimalField(
        max_digits=6, decimal_places=2, source="median_income_growth"
    )
    housingDemandIndex = serializers.IntegerField(source="housing_demand_index")


class CoordinatesSerializer(serializers.Serializer):
    """Serializer for coordinates nested object."""

    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, allow_null=True)


class GrowthAreaSerializer(serializers.ModelSerializer):
    """Serializer for GrowthArea model with nested objects."""

    cityName = serializers.CharField(source="city_name")
    metroArea = serializers.CharField(source="metro_area")
    growthMetrics = GrowthMetricsSerializer(source="*")
    coordinates = CoordinatesSerializer(source="*")

    class Meta:
        model = GrowthArea
        fields = ["cityName", "metroArea", "growthMetrics", "coordinates"]
