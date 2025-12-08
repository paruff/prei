from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .models import GrowthArea
from .serializers import GrowthAreaSerializer
from .validators import validate_min_growth_score, validate_state_code

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
        except Exception as e:
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
        except Exception as e:
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

        except Exception as e:
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
