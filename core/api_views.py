from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .models import ForeclosureProperty, GrowthArea
from .serializers import ForeclosurePropertySerializer, GrowthAreaSerializer
from .validators import (
    validate_foreclosure_stages,
    validate_location_parameter,
    validate_min_growth_score,
    validate_positive_decimal,
    validate_positive_integer,
    validate_property_types,
    validate_state_code,
)

logger = logging.getLogger(__name__)


@api_view(["GET"])
@throttle_classes([UserRateThrottle, AnonRateThrottle])
def growth_areas_list(request):
    """
    Retrieve economic growth areas filtered by state.

    Query Parameters:
        - state (required): 2-letter US state code
        - minGrowthScore (optional): Minimum composite growth score (0-100, default: 50)

    Returns:
        JSON response with growth areas and metadata
    """
    try:
        # Log the request
        logger.info(
            f"Growth areas request received - state: {request.GET.get('state')}, "
            f"minGrowthScore: {request.GET.get('minGrowthScore')}"
        )

        # Validate state parameter
        state_code_raw = request.GET.get("state")
        if not state_code_raw:
            return Response(
                {
                    "error": "Invalid state code. Please use 2-letter US state abbreviations.",
                    "code": "INVALID_STATE_CODE",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            state_code = validate_state_code(state_code_raw)
        except serializers.ValidationError as e:
            return Response(
                {
                    "error": str(e),
                    "code": "INVALID_STATE_CODE",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate minGrowthScore parameter
        try:
            min_score = validate_min_growth_score(request.GET.get("minGrowthScore"))
        except serializers.ValidationError as e:
            return Response(
                {
                    "error": str(e),
                    "code": "INVALID_PARAMETER",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check cache first
        cache_key = f"growth_areas_{state_code}_{min_score}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Returning cached data for state: {state_code}")
            return Response(cached_data, status=status.HTTP_200_OK)

        # Query database
        try:
            queryset = GrowthArea.objects.filter(state=state_code)

            if not queryset.exists():
                response_data = {
                    "state": state_code,
                    "dataTimestamp": timezone.now().isoformat(),
                    "areas": [],
                    "totalResults": 0,
                    "message": "No growth data available for the specified state",
                }
                # Cache empty result for shorter duration (1 hour)
                cache.set(cache_key, response_data, 3600)
                return Response(response_data, status=status.HTTP_200_OK)

            # Filter by composite score and sort
            filtered_areas = []
            for area in queryset:
                if area.composite_score >= Decimal(str(min_score)):
                    filtered_areas.append(area)

            # Sort by composite score descending
            filtered_areas.sort(key=lambda x: x.composite_score, reverse=True)

            # Get the most recent data timestamp
            data_timestamp = (
                queryset.first().data_timestamp if queryset.exists() else timezone.now()
            )

            # Serialize the data
            serializer = GrowthAreaSerializer(filtered_areas, many=True)

            response_data = {
                "state": state_code,
                "dataTimestamp": data_timestamp.isoformat(),
                "areas": serializer.data,
                "totalResults": len(filtered_areas),
            }

            # Cache the result
            cache.set(
                cache_key,
                response_data,
                getattr(settings, "GROWTH_AREAS_CACHE_DURATION", 86400),
            )

            logger.info(
                f"Successfully retrieved {len(filtered_areas)} growth areas for state: {state_code}"
            )

            return Response(response_data, status=status.HTTP_200_OK)

        except DatabaseError as e:
            logger.error(f"Database error while retrieving growth areas: {str(e)}")
            return Response(
                {
                    "error": "Economic data service temporarily unavailable. Please try again later.",
                    "code": "SERVICE_UNAVAILABLE",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    except Exception as e:
        logger.error(f"Unexpected error in growth_areas_list: {str(e)}")
        return Response(
            {
                "error": "Economic data service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["GET"])
@throttle_classes([UserRateThrottle, AnonRateThrottle])
def foreclosures_list(request):
    """
    Retrieve foreclosure property listings filtered by location and criteria.

    Query Parameters:
        - location (required): Geographic identifier (city/state, county, ZIP, state)
        - stage (optional): Comma-separated foreclosure stages
        - minPrice/maxPrice (optional): Price range filter
        - propertyType (optional): Comma-separated property types
        - minBeds/maxBeds (optional): Bedroom count range
        - minBaths/maxBaths (optional): Bathroom count range
        - minSqft/maxSqft (optional): Square footage range
        - minYearBuilt/maxYearBuilt (optional): Year built range
        - sortBy (optional): Sort field (default: auctionDate)
        - order (optional): Sort order (asc/desc, default: asc)
        - page (optional): Page number (default: 1)
        - limit (optional): Results per page (default: 20, max: 100)

    Returns:
        JSON response with foreclosure properties and metadata
    """
    try:
        # Log the request
        logger.info(
            f"Foreclosures request received - location: {request.GET.get('location')}"
        )

        # Validate location parameter
        try:
            location = validate_location_parameter(request.GET.get("location"))
        except serializers.ValidationError as e:
            return Response(
                {
                    "error": str(e),
                    "code": "INVALID_LOCATION",
                    "validFormats": [
                        "City, State (e.g., 'Miami, FL')",
                        "County Name (e.g., 'Miami-Dade County')",
                        "ZIP Code (e.g., '33139')",
                        "State Code (e.g., 'FL')",
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build queryset based on location
        queryset = ForeclosureProperty.objects.all()

        # Parse location - check if it's a ZIP code, state code, or city/state
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
                        Q(county__icontains=single_value)
                        | Q(city__icontains=single_value)
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
                # Invalid state code in city, state format
                return Response(
                    {
                        "error": "Invalid geographic area. Please provide a valid city, county, ZIP code, or state.",
                        "code": "INVALID_LOCATION",
                        "validFormats": [
                            "City, State (e.g., 'Miami, FL')",
                            "County Name (e.g., 'Miami-Dade County')",
                            "ZIP Code (e.g., '33139')",
                            "State Code (e.g., 'FL')",
                        ],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Apply filters
        try:
            # Foreclosure stage filter
            stages = validate_foreclosure_stages(request.GET.get("stage"))
            if stages:
                queryset = queryset.filter(foreclosure_status__in=stages)

            # Property type filter
            property_types = validate_property_types(request.GET.get("propertyType"))
            if property_types:
                queryset = queryset.filter(property_type__in=property_types)

            # Price range filter (use opening_bid if available, else estimated_value)
            min_price = validate_positive_decimal(
                request.GET.get("minPrice"), "minPrice"
            )
            max_price = validate_positive_decimal(
                request.GET.get("maxPrice"), "maxPrice"
            )
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

            # Bedroom filter
            min_beds = validate_positive_integer(request.GET.get("minBeds"), "minBeds")
            max_beds = validate_positive_integer(request.GET.get("maxBeds"), "maxBeds")
            if min_beds is not None:
                queryset = queryset.filter(bedrooms__gte=min_beds)
            if max_beds is not None:
                queryset = queryset.filter(bedrooms__lte=max_beds)

            # Bathroom filter
            min_baths = validate_positive_decimal(
                request.GET.get("minBaths"), "minBaths"
            )
            max_baths = validate_positive_decimal(
                request.GET.get("maxBaths"), "maxBaths"
            )
            if min_baths is not None:
                queryset = queryset.filter(bathrooms__gte=min_baths)
            if max_baths is not None:
                queryset = queryset.filter(bathrooms__lte=max_baths)

            # Square footage filter
            min_sqft = validate_positive_integer(request.GET.get("minSqft"), "minSqft")
            max_sqft = validate_positive_integer(request.GET.get("maxSqft"), "maxSqft")
            if min_sqft is not None:
                queryset = queryset.filter(square_footage__gte=min_sqft)
            if max_sqft is not None:
                queryset = queryset.filter(square_footage__lte=max_sqft)

            # Year built filter
            min_year = validate_positive_integer(
                request.GET.get("minYearBuilt"), "minYearBuilt"
            )
            max_year = validate_positive_integer(
                request.GET.get("maxYearBuilt"), "maxYearBuilt"
            )
            if min_year is not None:
                queryset = queryset.filter(year_built__gte=min_year)
            if max_year is not None:
                queryset = queryset.filter(year_built__lte=max_year)

        except serializers.ValidationError as e:
            return Response(
                {"error": str(e), "code": "INVALID_PARAMETER"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sorting
        sort_by = request.GET.get("sortBy", "auctionDate")
        order = request.GET.get("order", "asc")

        sort_field_map = {
            "auctionDate": "auction_date",
            "price": "opening_bid",
            "squareFootage": "square_footage",
        }

        if sort_by not in sort_field_map:
            sort_by = "auctionDate"

        sort_field = sort_field_map[sort_by]
        if order == "desc":
            sort_field = f"-{sort_field}"

        queryset = queryset.order_by(sort_field, "-created_at")

        # Pagination
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20
        except (ValueError, TypeError):
            page = 1
            limit = 20

        total_results = queryset.count()
        total_pages = (total_results + limit - 1) // limit if total_results > 0 else 0

        # Get paginated results
        start = (page - 1) * limit
        end = start + limit
        properties = queryset[start:end]

        # Check if no results
        if total_results == 0:
            return Response(
                {
                    "location": location,
                    "resultsCount": 0,
                    "dataTimestamp": timezone.now().isoformat(),
                    "dataSources": [],
                    "properties": [],
                    "pagination": {
                        "currentPage": page,
                        "totalPages": 0,
                        "totalResults": 0,
                        "resultsPerPage": limit,
                    },
                    "message": "No foreclosure properties found in the specified area",
                },
                status=status.HTTP_200_OK,
            )

        # Get unique data sources
        data_sources = list(queryset.values_list("data_source", flat=True).distinct())

        # Get most recent data timestamp
        latest_property = queryset.order_by("-data_timestamp").first()
        data_timestamp = (
            latest_property.data_timestamp if latest_property else timezone.now()
        )

        # Serialize the data
        serializer = ForeclosurePropertySerializer(properties, many=True)

        response_data = {
            "location": location,
            "resultsCount": total_results,
            "dataTimestamp": data_timestamp.isoformat(),
            "dataSources": data_sources,
            "properties": serializer.data,
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalResults": total_results,
                "resultsPerPage": limit,
            },
        }

        logger.info(
            f"Successfully retrieved {len(properties)} foreclosure properties for location: {location}"
        )

        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        logger.error(f"Database error while retrieving foreclosures: {str(e)}")
        return Response(
            {
                "error": "Foreclosure data service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except Exception as e:
        logger.error(f"Unexpected error in foreclosures_list: {str(e)}")
        return Response(
            {
                "error": "Foreclosure data service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
