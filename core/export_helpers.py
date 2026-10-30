"""Helper utilities for export API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from django.db.models import Q, QuerySet
from rest_framework import serializers

from .models import ForeclosureProperty
from .validators import (
    validate_foreclosure_stages,
    validate_location_parameter,
    validate_positive_decimal,
    validate_property_types,
    validate_state_code,
)


def parse_and_filter_location(
    location: str,
) -> Tuple[str, QuerySet[ForeclosureProperty]]:
    """
    Parse location string and filter queryset accordingly.

    Args:
        location: Location string (city/state, ZIP, state code, or county)

    Returns:
        Tuple of (validated_location, filtered_queryset)

    Raises:
        serializers.ValidationError: If location is invalid
    """
    # Validate location parameter
    location = validate_location_parameter(location)

    # Build queryset based on location
    queryset = ForeclosureProperty.objects.all()

    # Parse location
    location_parts = [part.strip() for part in location.split(",")]

    if len(location_parts) == 1:
        single_value = location_parts[0]
        # Check if it's a ZIP code (5 digits)
        if single_value.isdigit() and len(single_value) == 5:
            queryset = queryset.filter(zip_code=single_value)
        # Check if it's a state code (2 letters)
        elif len(single_value) == 2 and single_value.isalpha():
            try:
                state_code = validate_state_code(single_value)
                queryset = queryset.filter(state=state_code)
            except serializers.ValidationError:
                # Not a valid state code, treat as county
                queryset = queryset.filter(
                    Q(county__icontains=single_value) | Q(city__icontains=single_value)
                )
        else:
            # Treat as county or city name
            queryset = queryset.filter(
                Q(county__icontains=single_value) | Q(city__icontains=single_value)
            )
    elif len(location_parts) == 2:
        # City, State format
        city_name, state_code = location_parts
        try:
            state_code = validate_state_code(state_code)
            queryset = queryset.filter(city__icontains=city_name, state=state_code)
        except serializers.ValidationError:
            raise serializers.ValidationError(
                "Invalid geographic area. Please provide a valid city, county, ZIP code, or state."
            )

    return location, queryset


def apply_foreclosure_filters(
    queryset: QuerySet[ForeclosureProperty], filters: Dict[str, Any]
) -> Tuple[QuerySet[ForeclosureProperty], List[str]]:
    """
    Apply filters to foreclosure property queryset.

    Args:
        queryset: Base queryset to filter
        filters: Dictionary of filter criteria

    Returns:
        Tuple of (filtered_queryset, list_of_stages)

    Raises:
        serializers.ValidationError: If filter values are invalid
    """
    # Foreclosure stage filter
    stages = validate_foreclosure_stages(filters.get("stage"))
    if stages:
        queryset = queryset.filter(foreclosure_status__in=stages)

    # Property type filter
    property_types = validate_property_types(filters.get("propertyType"))
    if property_types:
        queryset = queryset.filter(property_type__in=property_types)

    # Price range filter (use opening_bid if available, else estimated_value)
    min_price = validate_positive_decimal(filters.get("minPrice"), "minPrice")
    max_price = validate_positive_decimal(filters.get("maxPrice"), "maxPrice")

    if min_price is not None:
        queryset = queryset.filter(
            Q(opening_bid__gte=min_price, opening_bid__isnull=False)
            | Q(
                opening_bid__isnull=True,
                estimated_value__gte=min_price,
                estimated_value__isnull=False,
            )
        )
    if max_price is not None:
        queryset = queryset.filter(
            Q(opening_bid__lte=max_price, opening_bid__isnull=False)
            | Q(
                opening_bid__isnull=True,
                estimated_value__lte=max_price,
                estimated_value__isnull=False,
            )
        )

    return queryset, stages
