from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from investor_app.finance.utils import (
    calculate_break_even_rent,
    calculate_carrying_costs as calc_costs,
    calculate_flip_strategy,
    calculate_rental_strategy,
    calculate_roi_components,
    calculate_vacation_rental_strategy,
    cap_rate as calc_cap_rate,
    cash_on_cash as calc_coc,
    dscr as calc_dscr,
)

from .models import (
    AuctionAlert,
    ForeclosureProperty,
    GrowthArea,
    Notification,
    NotificationPreference,
    UserWatchlist,
)
from .serializers import (
    AuctionAlertSerializer,
    CarryingCostRequestSerializer,
    ForeclosurePropertySerializer,
    GrowthAreaSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
    StrategyComparisonRequestSerializer,
    UserWatchlistSerializer,
)
from .validators import (
    validate_foreclosure_stages,
    validate_location_parameter,
    validate_min_growth_score,
    validate_positive_decimal,
    validate_positive_integer,
    validate_property_types,
    validate_state_code,
)
from .export_services import CSVExportService, JSONExportService, PDFExportService
from .export_helpers import apply_foreclosure_filters, parse_and_filter_location

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


def get_property_type_defaults(
    property_type: str, purchase_price: Decimal
) -> Dict[str, Any]:
    """Get default values based on property type.

    Args:
        property_type: Type of property (single-family, condo, multi-family, commercial)
        purchase_price: Property purchase price

    Returns:
        Dictionary with default values for the property type
    """
    defaults = {
        "single-family": {
            "hoaMonthly": Decimal("0"),
            "utilitiesMonthly": Decimal("200"),  # Standard utilities
            "maintenanceAnnualPercent": Decimal("1.0"),  # 1% rule
            "propertyManagementPercent": Decimal("10"),  # Standard 10%
            "vacancyRatePercent": Decimal("8"),  # Industry average
            "description": "Single-family home with standard utilities and lawn/exterior maintenance",
        },
        "condo": {
            "hoaMonthly": Decimal(
                str(purchase_price * Decimal("0.0003"))
            ),  # ~0.03% of value per month
            "utilitiesMonthly": Decimal("150"),  # Lower utilities (no yard)
            "maintenanceAnnualPercent": Decimal("0.5"),  # Lower (HOA covers exterior)
            "propertyManagementPercent": Decimal("10"),
            "vacancyRatePercent": Decimal("8"),
            "description": "Condo with HOA fees covering exterior maintenance and some utilities",
        },
        "multi-family": {
            "hoaMonthly": Decimal("0"),
            "utilitiesMonthly": Decimal("300"),  # Per-unit utilities higher
            "maintenanceAnnualPercent": Decimal("1.5"),  # Higher maintenance
            "propertyManagementPercent": Decimal("12"),  # Higher management fees
            "vacancyRatePercent": Decimal("10"),  # Slightly higher vacancy
            "description": "Multi-family property with higher management fees and maintenance reserves",
        },
        "commercial": {
            "hoaMonthly": Decimal("0"),
            "utilitiesMonthly": Decimal("400"),  # Higher commercial utilities
            "maintenanceAnnualPercent": Decimal("2.0"),  # Higher for commercial
            "propertyManagementPercent": Decimal("8"),  # Professional management
            "vacancyRatePercent": Decimal("12"),  # Higher commercial vacancy
            "description": "Commercial property with triple-net lease adjustments possible",
        },
    }

    return defaults.get(property_type, defaults["single-family"])


@api_view(["POST"])
@throttle_classes([UserRateThrottle, AnonRateThrottle])
def calculate_carrying_costs(request):
    """
    Calculate carrying costs and investment metrics for a property.

    Request Body:
        JSON object containing property details, financing, operating expenses, and rental income

    Returns:
        JSON response with detailed carrying cost breakdown, cash flow analysis, and investment metrics
    """
    try:
        # Validate request data
        serializer = CarryingCostRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Extract data
        property_details = data["propertyDetails"]
        financing = data["financing"]
        operating_expenses = data["operatingExpenses"]
        rental_income = data["rentalIncome"]

        purchase_price = property_details["purchasePrice"]
        property_type = property_details["propertyType"]
        year_built = property_details.get("yearBuilt", 2000)
        square_feet = property_details.get("squareFeet")

        down_payment = financing["downPayment"]
        loan_amount = financing["loanAmount"]
        interest_rate = financing["interestRate"]
        loan_term_years = financing["loanTermYears"]
        closing_costs = financing.get("closingCosts", Decimal("0"))
        loan_points = financing.get("loanPoints", Decimal("0"))

        property_tax_rate = operating_expenses["propertyTaxRate"]
        insurance_annual = operating_expenses.get("insuranceAnnual")
        hoa_monthly = operating_expenses["hoaMonthly"]
        utilities_monthly = operating_expenses["utilitiesMonthly"]
        maintenance_annual_percent = operating_expenses["maintenanceAnnualPercent"]
        property_management_percent = operating_expenses["propertyManagementPercent"]
        vacancy_rate_percent = operating_expenses["vacancyRatePercent"]

        monthly_rent = rental_income["monthlyRent"]
        other_monthly_income = rental_income.get("otherMonthlyIncome", Decimal("0"))

        # Calculate carrying costs
        carrying_costs = calc_costs(
            purchase_price=purchase_price,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            loan_term_years=loan_term_years,
            property_tax_rate=property_tax_rate,
            insurance_annual=insurance_annual,
            hoa_monthly=hoa_monthly,
            utilities_monthly=utilities_monthly,
            maintenance_annual_percent=maintenance_annual_percent,
            property_type=property_type,
            year_built=year_built,
        )

        # Calculate property management cost
        monthly_property_management = (
            monthly_rent * property_management_percent / Decimal(100)
        )
        annual_property_management = monthly_property_management * Decimal(12)

        # Add property management to carrying costs
        carrying_costs["monthly"]["propertyManagement"] = (
            monthly_property_management.quantize(Decimal("0.01"))
        )
        carrying_costs["annual"]["propertyManagement"] = (
            annual_property_management.quantize(Decimal("0.01"))
        )

        # Recalculate totals with property management
        carrying_costs["monthly"]["total"] = (
            carrying_costs["monthly"]["total"] + monthly_property_management
        ).quantize(Decimal("0.01"))
        carrying_costs["annual"]["total"] = (
            carrying_costs["annual"]["total"] + annual_property_management
        ).quantize(Decimal("0.01"))

        # Calculate cost breakdown percentages
        total_annual = carrying_costs["annual"]["total"]
        breakdown_percentages = {
            "mortgage": (
                float(
                    (
                        carrying_costs["annual"]["mortgage"]
                        / total_annual
                        * Decimal(100)
                    ).quantize(Decimal("0.1"))
                )
                if total_annual > 0
                else 0
            ),
            "propertyTax": (
                float(
                    (
                        carrying_costs["annual"]["propertyTax"]
                        / total_annual
                        * Decimal(100)
                    ).quantize(Decimal("0.1"))
                )
                if total_annual > 0
                else 0
            ),
            "insurance": (
                float(
                    (
                        carrying_costs["annual"]["insurance"]
                        / total_annual
                        * Decimal(100)
                    ).quantize(Decimal("0.1"))
                )
                if total_annual > 0
                else 0
            ),
            "utilities": (
                float(
                    (
                        carrying_costs["annual"]["utilities"]
                        / total_annual
                        * Decimal(100)
                    ).quantize(Decimal("0.1"))
                )
                if total_annual > 0
                else 0
            ),
            "maintenance": (
                float(
                    (
                        carrying_costs["annual"]["maintenance"]
                        / total_annual
                        * Decimal(100)
                    ).quantize(Decimal("0.1"))
                )
                if total_annual > 0
                else 0
            ),
            "propertyManagement": (
                float(
                    (annual_property_management / total_annual * Decimal(100)).quantize(
                        Decimal("0.1")
                    )
                )
                if total_annual > 0
                else 0
            ),
        }

        # Add breakdown to carrying costs
        carrying_costs["breakdown"] = {"percentages": breakdown_percentages}

        # Calculate per square foot metrics if square footage is available
        if square_feet and square_feet > 0:
            carrying_costs["perSquareFoot"] = {
                "monthly": float(
                    (
                        carrying_costs["monthly"]["total"] / Decimal(square_feet)
                    ).quantize(Decimal("0.01"))
                ),
                "annual": float(
                    (carrying_costs["annual"]["total"] / Decimal(square_feet)).quantize(
                        Decimal("0.01")
                    )
                ),
            }

        # Add data quality indicators
        carrying_costs["dataQuality"] = {
            "propertyTax": "calculated",
            "insurance": "estimated" if insurance_annual is None else "user_provided",
            "maintenance": "industry_standard",
            "utilities": "user_provided",
        }

        # Calculate cash flow
        gross_rental_income_monthly = monthly_rent + other_monthly_income
        gross_rental_income_annual = gross_rental_income_monthly * Decimal(12)

        vacancy_loss_monthly = (
            gross_rental_income_monthly * vacancy_rate_percent / Decimal(100)
        )
        vacancy_loss_annual = vacancy_loss_monthly * Decimal(12)

        effective_gross_income_monthly = (
            gross_rental_income_monthly - vacancy_loss_monthly
        )
        effective_gross_income_annual = effective_gross_income_monthly * Decimal(12)

        # Operating expenses (excluding debt service and property management)
        operating_expenses_monthly = (
            carrying_costs["monthly"]["propertyTax"]
            + carrying_costs["monthly"]["insurance"]
            + carrying_costs["monthly"]["hoa"]
            + carrying_costs["monthly"]["utilities"]
            + carrying_costs["monthly"]["maintenance"]
        )
        operating_expenses_annual = operating_expenses_monthly * Decimal(12)

        # NOI (Net Operating Income)
        noi_monthly = effective_gross_income_monthly - operating_expenses_monthly
        noi_annual = noi_monthly * Decimal(12)

        # Debt service
        debt_service_monthly = carrying_costs["monthly"]["mortgage"]
        debt_service_annual = debt_service_monthly * Decimal(12)

        # Net cash flow (after debt service and property management)
        net_cash_flow_monthly = (
            noi_monthly - debt_service_monthly - monthly_property_management
        )
        net_cash_flow_annual = net_cash_flow_monthly * Decimal(12)

        cash_flow = {
            "monthly": {
                "grossRentalIncome": float(
                    gross_rental_income_monthly.quantize(Decimal("0.01"))
                ),
                "vacancyLoss": float(vacancy_loss_monthly.quantize(Decimal("0.01"))),
                "effectiveGrossIncome": float(
                    effective_gross_income_monthly.quantize(Decimal("0.01"))
                ),
                "operatingExpenses": float(
                    operating_expenses_monthly.quantize(Decimal("0.01"))
                ),
                "noi": float(noi_monthly.quantize(Decimal("0.01"))),
                "debtService": float(debt_service_monthly.quantize(Decimal("0.01"))),
                "netCashFlow": float(net_cash_flow_monthly.quantize(Decimal("0.01"))),
            },
            "annual": {
                "grossRentalIncome": float(
                    gross_rental_income_annual.quantize(Decimal("0.01"))
                ),
                "vacancyLoss": float(vacancy_loss_annual.quantize(Decimal("0.01"))),
                "effectiveGrossIncome": float(
                    effective_gross_income_annual.quantize(Decimal("0.01"))
                ),
                "operatingExpenses": float(
                    operating_expenses_annual.quantize(Decimal("0.01"))
                ),
                "noi": float(noi_annual.quantize(Decimal("0.01"))),
                "debtService": float(debt_service_annual.quantize(Decimal("0.01"))),
                "netCashFlow": float(net_cash_flow_annual.quantize(Decimal("0.01"))),
            },
        }

        # Calculate investment metrics
        total_cash_invested = down_payment + closing_costs + loan_points

        # Cash-on-Cash Return
        coc_return = calc_coc(net_cash_flow_annual, total_cash_invested)
        coc_return_percent = float((coc_return * Decimal(100)).quantize(Decimal("0.1")))

        # COC interpretation
        if coc_return_percent < 0:
            coc_interpretation = "negative"
        elif coc_return_percent < 5:
            coc_interpretation = "poor"
        elif coc_return_percent < 8:
            coc_interpretation = "fair"
        elif coc_return_percent < 12:
            coc_interpretation = "good"
        else:
            coc_interpretation = "excellent"

        # Cap Rate
        cap_rate_value = calc_cap_rate(noi_annual, purchase_price)
        cap_rate_percent = float(
            (cap_rate_value * Decimal(100)).quantize(Decimal("0.1"))
        )

        # Break-even rent
        # Monthly costs excluding property management (will be added to break-even rent)
        monthly_costs_excl_mgmt = (
            carrying_costs["monthly"]["mortgage"]
            + carrying_costs["monthly"]["propertyTax"]
            + carrying_costs["monthly"]["insurance"]
            + carrying_costs["monthly"]["hoa"]
            + carrying_costs["monthly"]["utilities"]
            + carrying_costs["monthly"]["maintenance"]
        )

        break_even = calculate_break_even_rent(
            monthly_costs_excl_mgmt, vacancy_rate_percent, property_management_percent
        )

        coverage_ratio = (
            float((monthly_rent / break_even["monthly"]).quantize(Decimal("0.01")))
            if break_even["monthly"] > 0
            else 0
        )

        # Debt Service Coverage Ratio
        dscr_value = calc_dscr(noi_annual, debt_service_annual)
        dscr_ratio = float(dscr_value.quantize(Decimal("0.01")))

        # ROI Calculations
        roi_data = calculate_roi_components(
            purchase_price=purchase_price,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            loan_term_years=loan_term_years,
            total_cash_invested=total_cash_invested,
            annual_cash_flow=net_cash_flow_annual,
            appreciation_rate=Decimal("3.0"),  # Default 3% appreciation
            tax_bracket=Decimal("24"),  # Default 24% tax bracket
            num_years=5,
        )

        investment_metrics = {
            "totalCashInvested": float(total_cash_invested.quantize(Decimal("0.01"))),
            "cocReturn": coc_return_percent,
            "cocInterpretation": coc_interpretation,
            "capRate": cap_rate_percent,
            "breakEvenRent": {
                "monthly": float(break_even["monthly"]),
                "coverage": coverage_ratio,
            },
            "debtCoverageRatio": dscr_ratio,
            "roi": {
                "year1": float(roi_data["year1"]["roi"]),
                "year5Projected": float(roi_data["year5Projected"]["roi"]),
                "year5Annualized": float(roi_data["year5Projected"]["annualizedRoi"]),
                "components": {
                    "cashFlowReturn": float(roi_data["components"]["cashFlowReturn"]),
                    "appreciationReturn": float(
                        roi_data["components"]["appreciationReturn"]
                    ),
                    "equityBuildupReturn": float(
                        roi_data["components"]["equityBuildupReturn"]
                    ),
                    "taxBenefitsReturn": float(
                        roi_data["components"]["taxBenefitsReturn"]
                    ),
                },
                "breakdown": {
                    "year1": {
                        "totalReturn": float(roi_data["year1"]["totalReturn"]),
                        "cashFlow": float(roi_data["year1"]["cashFlow"]),
                        "principalPaydown": float(
                            roi_data["year1"]["principalPaydown"]
                        ),
                        "appreciation": float(roi_data["year1"]["appreciation"]),
                        "taxBenefits": float(roi_data["year1"]["taxBenefits"]),
                    },
                    "year5": {
                        "totalReturn": float(roi_data["year5Projected"]["totalReturn"]),
                        "totalCashFlow": float(
                            roi_data["year5Projected"]["totalCashFlow"]
                        ),
                        "totalPrincipalPaydown": float(
                            roi_data["year5Projected"]["totalPrincipalPaydown"]
                        ),
                        "totalAppreciation": float(
                            roi_data["year5Projected"]["totalAppreciation"]
                        ),
                        "totalTaxBenefits": float(
                            roi_data["year5Projected"]["totalTaxBenefits"]
                        ),
                    },
                },
            },
        }

        # Generate warnings
        warnings = []
        if net_cash_flow_monthly < 0:
            warnings.append(
                {
                    "type": "negative_cash_flow",
                    "severity": "high",
                    "message": f"Property shows negative cash flow. Monthly rent of ${float(monthly_rent)} does not cover monthly carrying costs of ${float(carrying_costs['monthly']['total'])}.",
                }
            )

        if break_even["monthly"] > monthly_rent:
            pct_over = float(
                (
                    (break_even["monthly"] - monthly_rent) / monthly_rent * Decimal(100)
                ).quantize(Decimal("0"))
            )
            warnings.append(
                {
                    "type": "break_even_mismatch",
                    "severity": "high",
                    "message": f"Break-even rent (${float(break_even['monthly'])}) exceeds market rent (${float(monthly_rent)}) by {pct_over}%. Property may not be viable as rental.",
                }
            )

        if dscr_ratio < 1.25 and loan_amount > 0:
            warnings.append(
                {
                    "type": "low_dcr",
                    "severity": "medium",
                    "message": f"Debt Coverage Ratio of {dscr_ratio} is below lender minimum (1.25). Refinancing may be difficult.",
                }
            )

        # Generate recommendations
        recommendations = []

        # Recommendation: Increase down payment if negative cash flow
        if net_cash_flow_monthly < 0:
            # Calculate required down payment for positive cash flow
            # Need to reduce monthly mortgage payment
            monthly_shortfall = abs(net_cash_flow_monthly)

            # Estimate loan amount reduction needed (simplified)
            # Using rough approximation: $1000 loan reduction ~ $7 monthly payment reduction
            estimated_loan_reduction = monthly_shortfall * Decimal(
                140
            )  # Rough multiplier
            new_down_payment = down_payment + estimated_loan_reduction

            down_payment_pct = new_down_payment / purchase_price * Decimal(100)

            if down_payment_pct <= Decimal(50):  # Only suggest if reasonable
                recommendations.append(
                    {
                        "type": "increase_down_payment",
                        "description": f"Increase down payment to {float(down_payment_pct):.0f}% (${float(new_down_payment):,.0f}) to reduce monthly debt service and improve cash flow",
                        "estimatedImpact": "Monthly cash flow would improve to approximately $0",
                    }
                )

        # Recommendation: Consider different strategy if flip would be better
        if net_cash_flow_monthly < 0 and break_even["monthly"] > monthly_rent * Decimal(
            "1.2"
        ):
            # Property struggling as rental - suggest flip
            recommendations.append(
                {
                    "type": "consider_flip_strategy",
                    "description": "Property may be better suited for fix-and-flip given negative rental cash flow and high break-even rent",
                    "estimatedImpact": "Consider renovation and quick sale to capture appreciation",
                }
            )

        # Recommendation: Refinance if DSCR is low but cash flow is positive
        if dscr_ratio < 1.25 and net_cash_flow_monthly > 0 and loan_amount > 0:
            recommendations.append(
                {
                    "type": "improve_dscr",
                    "description": "Consider refinancing to improve DSCR for future lending opportunities",
                    "estimatedImpact": "Increase rent or reduce operating expenses to achieve DSCR > 1.25",
                }
            )

        # Recommendation: Good investment if positive cash flow and good metrics
        if net_cash_flow_monthly > 0 and coc_return_percent > 8:
            recommendations.append(
                {
                    "type": "strong_investment",
                    "description": "Property shows strong fundamentals with positive cash flow and good CoC return",
                    "estimatedImpact": f"Annual cash flow of ${float(net_cash_flow_annual):,.0f} with {coc_return_percent:.1f}% CoC return",
                }
            )

        # Recommendation: Consider vacation rental for certain property types
        if (
            property_type in ["condo", "single-family"]
            and "location" in property_details
        ):
            location = property_details["location"]
            # Check if in potential vacation rental area (simplified - just check FL for demo)
            if location.get("state") == "FL":
                recommendations.append(
                    {
                        "type": "consider_vacation_rental",
                        "description": "Property location may be suitable for vacation rental strategy with potentially higher income",
                        "estimatedImpact": "Vacation rentals can generate 20-50% more income than traditional rentals in tourist areas",
                    }
                )

        # Build response
        # Convert Decimal to float for JSON serialization
        carrying_costs_output = {
            "monthly": {k: float(v) for k, v in carrying_costs["monthly"].items()},
            "annual": {k: float(v) for k, v in carrying_costs["annual"].items()},
            "breakdown": carrying_costs["breakdown"],
            "dataQuality": carrying_costs["dataQuality"],
        }

        if "perSquareFoot" in carrying_costs:
            carrying_costs_output["perSquareFoot"] = carrying_costs["perSquareFoot"]

        response_data = {
            "property": {
                "address": property_details["location"]["address"],
                "purchasePrice": float(purchase_price),
                "propertyType": property_type,
            },
            "carryingCosts": carrying_costs_output,
            "cashFlow": cash_flow,
            "investmentMetrics": investment_metrics,
            "warnings": warnings,
            "recommendations": recommendations,
            "calculationTimestamp": timezone.now().isoformat(),
        }

        logger.info(
            f"Carrying costs calculated for property at {property_details['location']['address']}"
        )

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in calculate_carrying_costs: {str(e)}")
        return Response(
            {
                "error": "Carrying cost calculation service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# Watchlist API endpoints


@api_view(["GET", "POST"])
@throttle_classes([UserRateThrottle])
def watchlist_view(request):
    """
    Get user's watchlist or add property to watchlist.

    GET: List all watchlist items
    POST: Add property to watchlist (requires propertyId in body)
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if request.method == "GET":
        watchlist = UserWatchlist.objects.filter(user=request.user).select_related(
            "property"
        )
        serializer = UserWatchlistSerializer(watchlist, many=True)
        return Response({"watchlist": serializer.data}, status=status.HTTP_200_OK)

    elif request.method == "POST":
        property_id = request.data.get("propertyId")
        notes = request.data.get("notes", "")

        if not property_id:
            return Response(
                {"error": "propertyId is required", "code": "INVALID_REQUEST"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            property_obj = ForeclosureProperty.objects.get(id=property_id)
        except ForeclosureProperty.DoesNotExist:
            return Response(
                {"error": "Property not found", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        watchlist_item, created = UserWatchlist.objects.get_or_create(
            user=request.user, property=property_obj, defaults={"notes": notes}
        )

        if not created:
            return Response(
                {"error": "Property already in watchlist", "code": "ALREADY_EXISTS"},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = UserWatchlistSerializer(watchlist_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@throttle_classes([UserRateThrottle])
def watchlist_item_delete(request, item_id):
    """Remove property from watchlist."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        watchlist_item = UserWatchlist.objects.get(id=item_id, user=request.user)
        watchlist_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except UserWatchlist.DoesNotExist:
        return Response(
            {"error": "Watchlist item not found", "code": "NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )


# Alerts API endpoints


@api_view(["GET", "POST"])
@throttle_classes([UserRateThrottle])
def alerts_view(request):
    """
    Get user's alerts or create new alert.

    GET: List all alerts
    POST: Create new alert
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if request.method == "GET":
        alerts = AuctionAlert.objects.filter(user=request.user)
        serializer = AuctionAlertSerializer(alerts, many=True)
        return Response({"alerts": serializer.data}, status=status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = AuctionAlertSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
@throttle_classes([UserRateThrottle])
def alert_detail(request, alert_id):
    """Get, update, or delete specific alert."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        alert = AuctionAlert.objects.get(id=alert_id, user=request.user)
    except AuctionAlert.DoesNotExist:
        return Response(
            {"error": "Alert not found", "code": "NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = AuctionAlertSerializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "PUT":
        serializer = AuctionAlertSerializer(alert, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "DELETE":
        alert.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Notifications API endpoints


@api_view(["GET"])
@throttle_classes([UserRateThrottle])
def notifications_view(request):
    """Get user's notifications."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Filter options
    is_read = request.GET.get("isRead")
    is_dismissed = request.GET.get("isDismissed")

    notifications = Notification.objects.filter(user=request.user)

    if is_read is not None:
        notifications = notifications.filter(is_read=is_read.lower() == "true")

    if is_dismissed is not None:
        notifications = notifications.filter(
            is_dismissed=is_dismissed.lower() == "true"
        )

    serializer = NotificationSerializer(notifications, many=True)
    return Response({"notifications": serializer.data}, status=status.HTTP_200_OK)


@api_view(["POST"])
@throttle_classes([UserRateThrottle])
def notification_mark_read(request, notification_id):
    """Mark notification as read."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_read()
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response(
            {"error": "Notification not found", "code": "NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST"])
@throttle_classes([UserRateThrottle])
def notification_dismiss(request, notification_id):
    """Dismiss notification."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.dismiss()
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response(
            {"error": "Notification not found", "code": "NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )


# Notification Preferences API endpoints


@api_view(["GET", "PUT"])
@throttle_classes([UserRateThrottle])
def notification_preferences_view(request):
    """Get or update user's notification preferences."""
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Get or create preferences
    prefs, created = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == "GET":
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "PUT":
        serializer = NotificationPreferenceSerializer(
            prefs, data=request.data, partial=True
        )

        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# Export API endpoints


@api_view(["POST"])
@throttle_classes([UserRateThrottle, AnonRateThrottle])
def export_foreclosures_csv(request):
    """
    Export foreclosure listings to CSV format.

    Request Body:
        - filters: Dictionary of filters to apply (location, stage, price range, etc.)
        - fields: Optional list of fields to include in export

    Returns:
        CSV file download
    """
    try:
        # Extract filters from request
        filters = request.data.get("filters", {})
        fields = request.data.get("fields")

        # Validate location parameter
        location = filters.get("location")
        if not location:
            return Response(
                {
                    "error": "Location parameter is required",
                    "code": "INVALID_REQUEST",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse and filter by location using helper
        try:
            location, queryset = parse_and_filter_location(location)
        except serializers.ValidationError as e:
            return Response(
                {
                    "error": str(e),
                    "code": "INVALID_LOCATION",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply additional filters using helper
        try:
            queryset, stages = apply_foreclosure_filters(queryset, filters)
        except serializers.ValidationError as e:
            return Response(
                {"error": str(e), "code": "INVALID_PARAMETER"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit export size (max 500 properties for synchronous export)
        total_count = queryset.count()
        if total_count > 500:
            return Response(
                {
                    "error": f"Export too large ({total_count} properties). Maximum 500 properties for synchronous export.",
                    "code": "EXPORT_TOO_LARGE",
                    "totalCount": total_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get properties
        properties = queryset.order_by("auction_date", "-created_at")[:500]

        # Convert to dictionaries for CSV export
        property_dicts = []
        for prop in properties:
            property_dicts.append(
                {
                    "property_id": prop.property_id,
                    "street": prop.street,
                    "city": prop.city,
                    "state": prop.state,
                    "zip_code": prop.zip_code,
                    "foreclosure_status": prop.foreclosure_status,
                    "filing_date": prop.filing_date,
                    "auction_date": prop.auction_date,
                    "opening_bid": prop.opening_bid,
                    "estimated_value": prop.estimated_value,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "square_footage": prop.square_footage,
                    "property_type": prop.property_type,
                    "lender_name": prop.lender_name,
                    "data_source": prop.data_source,
                    "data_timestamp": prop.data_timestamp,
                }
            )

        # Generate CSV
        csv_service = CSVExportService()
        try:
            csv_content = csv_service.export_foreclosures(property_dicts, fields)
        except ValueError as e:
            return Response(
                {"error": str(e), "code": "INVALID_FIELDS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate filename
        filename = csv_service.generate_filename(
            "foreclosures",
            location,
            {"stage": stages} if stages else None,
        )

        # Return CSV as download
        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(
            f"CSV export completed - {len(property_dicts)} properties exported for location: {location}"
        )

        return response

    except Exception as e:
        logger.error(f"Unexpected error in export_foreclosures_csv: {str(e)}")
        return Response(
            {
                "error": "Export service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["POST"])
@throttle_classes([UserRateThrottle, AnonRateThrottle])
def export_foreclosures_json(request):
    """
    Export foreclosure listings to JSON format with metadata.

    Request Body:
        - filters: Dictionary of filters to apply

    Returns:
        JSON file download
    """
    try:
        # Extract filters from request
        filters = request.data.get("filters", {})

        # Validate location parameter
        location = filters.get("location")
        if not location:
            return Response(
                {
                    "error": "Location parameter is required",
                    "code": "INVALID_REQUEST",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse and filter by location using helper
        try:
            location, queryset = parse_and_filter_location(location)
        except serializers.ValidationError as e:
            return Response(
                {
                    "error": str(e),
                    "code": "INVALID_LOCATION",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply additional filters using helper
        try:
            queryset, _ = apply_foreclosure_filters(queryset, filters)
        except serializers.ValidationError as e:
            return Response(
                {"error": str(e), "code": "INVALID_PARAMETER"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit export size
        total_count = queryset.count()
        if total_count > 500:
            return Response(
                {
                    "error": f"Export too large ({total_count} properties). Maximum 500 properties for synchronous export.",
                    "code": "EXPORT_TOO_LARGE",
                    "totalCount": total_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get properties and serialize
        properties = queryset.order_by("auction_date", "-created_at")[:500]
        serializer = ForeclosurePropertySerializer(properties, many=True)

        # Generate JSON with metadata
        json_service = JSONExportService()
        user_email = request.user.email if request.user.is_authenticated else None
        json_content = json_service.export_with_metadata(
            serializer.data,
            "foreclosures",
            filters,
            user_email,
        )

        # Generate filename
        filename = json_service.generate_filename("foreclosures", location)

        # Return JSON as download
        response = HttpResponse(json_content, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(
            f"JSON export completed - {len(properties)} properties exported for location: {location}"
        )

        return response

    except Exception as e:
        logger.error(f"Unexpected error in export_foreclosures_json: {str(e)}")
        return Response(
            {
                "error": "Export service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["POST"])
@throttle_classes([UserRateThrottle])
def export_property_analysis_pdf(request):
    """
    Export property analysis to PDF format.

    Request Body:
        - propertyData: Property information
        - analysisResults: Financial analysis results

    Returns:
        PDF file download
    """
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "code": "UNAUTHORIZED"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        # Extract data from request
        property_data = request.data.get("propertyData", {})
        analysis_results = request.data.get("analysisResults", {})

        if not property_data or not analysis_results:
            return Response(
                {
                    "error": "Both propertyData and analysisResults are required",
                    "code": "INVALID_REQUEST",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user branding (optional)
        user_branding = None

        # Generate PDF
        pdf_service = PDFExportService()
        pdf_bytes = pdf_service.generate_property_analysis_report(
            property_data,
            analysis_results,
            user_branding,
        )

        # Generate filename
        property_address = property_data.get("address", "property")
        filename = pdf_service.generate_filename(property_address)

        # Return PDF as download
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(f"PDF export completed for property: {property_address}")

        return response

    except Exception as e:
        logger.error(f"Unexpected error in export_property_analysis_pdf: {str(e)}")
        return Response(
            {
                "error": "Export service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@api_view(["POST"])
@throttle_classes([UserRateThrottle, AnonRateThrottle])
def compare_investment_strategies(request):
    """
    Compare different investment strategies for a property.

    Request Body:
        JSON object containing property details, financing, operating expenses,
        strategies to compare, and strategy-specific assumptions

    Returns:
        JSON response with side-by-side strategy comparison and recommendation
    """
    try:
        # Validate request data
        serializer = StrategyComparisonRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Extract common data
        property_details = data["propertyDetails"]
        financing = data["financing"]
        operating_expenses = data["operatingExpenses"]
        strategies = data["strategies"]
        assumptions = data.get("assumptions", {})

        purchase_price = property_details["purchasePrice"]
        property_type = property_details["propertyType"]
        year_built = property_details.get("yearBuilt", 2000)

        down_payment = financing["downPayment"]
        loan_amount = financing["loanAmount"]
        interest_rate = financing["interestRate"]
        loan_term_years = financing["loanTermYears"]
        closing_costs = financing.get("closingCosts", Decimal("0"))

        property_tax_rate = operating_expenses["propertyTaxRate"]
        insurance_annual = operating_expenses.get("insuranceAnnual")
        hoa_monthly = operating_expenses["hoaMonthly"]
        utilities_monthly = operating_expenses["utilitiesMonthly"]
        maintenance_annual_percent = operating_expenses["maintenanceAnnualPercent"]
        property_management_percent = operating_expenses["propertyManagementPercent"]
        vacancy_rate_percent = operating_expenses["vacancyRatePercent"]

        # Calculate carrying costs (needed for rental strategies)
        carrying_costs = calc_costs(
            purchase_price=purchase_price,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            loan_term_years=loan_term_years,
            property_tax_rate=property_tax_rate,
            insurance_annual=insurance_annual,
            hoa_monthly=hoa_monthly,
            utilities_monthly=utilities_monthly,
            maintenance_annual_percent=maintenance_annual_percent,
            property_type=property_type,
            year_built=year_built,
        )

        results = {}

        # Calculate flip strategy
        if "flip" in strategies:
            flip_assumptions = assumptions.get("flip", {})

            flip_result = calculate_flip_strategy(
                purchase_price=purchase_price,
                renovation_costs=Decimal(
                    str(flip_assumptions.get("renovationCosts", 0))
                ),
                holding_period_months=int(
                    flip_assumptions.get("holdingPeriodMonths", 6)
                ),
                expected_sale_price=Decimal(
                    str(flip_assumptions.get("expectedSalePrice", purchase_price))
                ),
                selling_costs=Decimal(str(flip_assumptions.get("sellingCosts", 0))),
                down_payment=down_payment,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                loan_term_years=loan_term_years,
                closing_costs=closing_costs,
                property_tax_rate=property_tax_rate,
                insurance_annual=insurance_annual,
                utilities_monthly=utilities_monthly,
                property_type=property_type,
                year_built=year_built,
            )

            results["flip"] = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in flip_result.items()
            }

        # Calculate rental strategy
        if "rental" in strategies:
            rental_assumptions = assumptions.get("rental", {})
            monthly_rent = Decimal(str(rental_assumptions.get("monthlyRent", 0)))
            holding_period_years = int(rental_assumptions.get("holdingPeriodYears", 5))
            appreciation_rate = Decimal(
                str(rental_assumptions.get("appreciationRate", 3.0))
            )

            # Calculate annual cash flow
            monthly_property_management = (
                monthly_rent * property_management_percent / Decimal(100)
            )
            monthly_total = (
                carrying_costs["monthly"]["total"] + monthly_property_management
            )

            gross_income = monthly_rent
            vacancy_loss = gross_income * vacancy_rate_percent / Decimal(100)
            effective_income = gross_income - vacancy_loss
            annual_cash_flow = (effective_income - monthly_total) * Decimal(12)

            rental_result = calculate_rental_strategy(
                purchase_price=purchase_price,
                down_payment=down_payment,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                loan_term_years=loan_term_years,
                closing_costs=closing_costs,
                annual_cash_flow=annual_cash_flow,
                appreciation_rate=appreciation_rate,
                holding_period_years=holding_period_years,
            )

            results["rental"] = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in rental_result.items()
            }

        # Calculate vacation rental strategy
        if "vacation_rental" in strategies:
            vr_assumptions = assumptions.get("vacation_rental", {})

            avg_nightly_rate = Decimal(str(vr_assumptions.get("avgNightlyRate", 0)))
            avg_occupancy_rate = Decimal(
                str(vr_assumptions.get("avgOccupancyRate", 65))
            )
            cleaning_fee = Decimal(str(vr_assumptions.get("cleaningFeePerStay", 150)))

            # Operating expenses for vacation rental (higher than normal rental)
            # Maintenance is 1.5x higher due to increased turnover and wear
            maintenance_multiplier = Decimal("1.5")
            monthly_operating = (
                carrying_costs["monthly"]["propertyTax"]
                + carrying_costs["monthly"]["insurance"]
                + carrying_costs["monthly"]["hoa"]
                + carrying_costs["monthly"]["utilities"]
                + carrying_costs["monthly"]["maintenance"] * maintenance_multiplier
            )

            vr_result = calculate_vacation_rental_strategy(
                purchase_price=purchase_price,
                down_payment=down_payment,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                loan_term_years=loan_term_years,
                closing_costs=closing_costs,
                avg_nightly_rate=avg_nightly_rate,
                avg_occupancy_rate=avg_occupancy_rate,
                cleaning_fee_per_stay=cleaning_fee,
                monthly_operating_expenses=monthly_operating,
                holding_period_years=5,
            )

            results["vacation_rental"] = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in vr_result.items()
            }

        # Determine best strategy
        best_strategy = None
        best_roi = Decimal("-999999")

        for strategy_name, strategy_data in results.items():
            roi = Decimal(str(strategy_data.get("roi", 0)))
            if roi > best_roi:
                best_roi = roi
                best_strategy = strategy_name

        # Generate recommendation
        recommendation = {
            "bestStrategy": best_strategy,
            "reasoning": "",
            "riskFactors": [],
        }

        if best_strategy == "flip":
            recommendation["reasoning"] = (
                f"Fix-and-flip offers highest return ({float(best_roi):.1f}% ROI) with shortest timeline. "
                "This strategy provides quick capital turnover."
            )
            recommendation["riskFactors"] = [
                "Market conditions could change during renovation",
                "Renovation could exceed budget or timeline",
                "Flipping requires active management and expertise",
            ]
        elif best_strategy == "rental":
            recommendation["reasoning"] = (
                f"Buy-and-hold rental offers {float(best_roi):.1f}% ROI with steady long-term growth. "
                "This strategy provides passive income and wealth building through appreciation and equity."
            )
            recommendation["riskFactors"] = [
                "Tenant vacancies can impact cash flow",
                "Property management and maintenance are ongoing",
                "Market appreciation is not guaranteed",
            ]
        elif best_strategy == "vacation_rental":
            recommendation["reasoning"] = (
                f"Vacation rental offers {float(best_roi):.1f}% ROI with higher income potential. "
                "This strategy can generate more cash flow than traditional rentals in the right market."
            )
            recommendation["riskFactors"] = [
                "Seasonal fluctuations in occupancy",
                "More hands-on management required",
                "Higher operating costs and regulations",
            ]

        # Build response
        response_data = {
            "property": {
                "address": property_details["location"]["address"],
                "purchasePrice": float(purchase_price),
                "propertyType": property_type,
            },
            "strategies": results,
            "recommendation": recommendation,
            "calculationTimestamp": timezone.now().isoformat(),
        }

        logger.info(
            f"Strategy comparison completed for property at {property_details['location']['address']}"
        )

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in compare_investment_strategies: {str(e)}")
        return Response(
            {
                "error": "Strategy comparison service temporarily unavailable. Please try again later.",
                "code": "SERVICE_UNAVAILABLE",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
