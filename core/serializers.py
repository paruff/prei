from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import (
    AuctionAlert,
    ForeclosureProperty,
    GrowthArea,
    Notification,
    NotificationPreference,
    UserWatchlist,
)


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
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, allow_null=True
    )


class GrowthAreaSerializer(serializers.ModelSerializer):
    """Serializer for GrowthArea model with nested objects."""

    cityName = serializers.CharField(source="city_name")
    metroArea = serializers.CharField(source="metro_area")
    growthMetrics = GrowthMetricsSerializer(source="*")
    coordinates = CoordinatesSerializer(source="*")

    class Meta:
        model = GrowthArea
        fields = ["cityName", "metroArea", "growthMetrics", "coordinates"]


class AddressSerializer(serializers.Serializer):
    """Serializer for address nested object."""

    street = serializers.CharField()
    city = serializers.CharField()
    county = serializers.CharField()
    state = serializers.CharField()
    zipCode = serializers.CharField(source="zip_code")
    coordinates = CoordinatesSerializer(source="*")


class ForeclosureDetailsSerializer(serializers.Serializer):
    """Serializer for foreclosure details nested object."""

    status = serializers.CharField(source="foreclosure_status")
    stage = serializers.CharField(source="foreclosure_stage")
    filingDate = serializers.DateField(source="filing_date", allow_null=True)
    auctionDate = serializers.DateField(source="auction_date", allow_null=True)
    auctionTime = serializers.CharField(source="auction_time")
    auctionLocation = serializers.CharField(source="auction_location")
    openingBid = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="opening_bid", allow_null=True
    )
    unpaidBalance = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="unpaid_balance", allow_null=True
    )
    lenderName = serializers.CharField(source="lender_name")
    caseNumber = serializers.CharField(source="case_number")
    trusteeContact = serializers.SerializerMethodField()

    def get_trusteeContact(self, obj):
        """Return trustee contact information."""
        return {
            "name": obj.trustee_name,
            "phone": obj.trustee_phone,
        }


class PropertyDetailsSerializer(serializers.Serializer):
    """Serializer for property details nested object."""

    propertyType = serializers.CharField(source="property_type")
    bedrooms = serializers.IntegerField()
    bathrooms = serializers.DecimalField(max_digits=4, decimal_places=1)
    squareFootage = serializers.IntegerField(source="square_footage")
    lotSize = serializers.IntegerField(source="lot_size")
    yearBuilt = serializers.IntegerField(source="year_built", allow_null=True)
    stories = serializers.IntegerField(allow_null=True)
    garage = serializers.CharField()
    pool = serializers.BooleanField()
    condition = serializers.CharField()


class ValuationDataSerializer(serializers.Serializer):
    """Serializer for valuation data nested object."""

    estimatedValue = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="estimated_value", allow_null=True
    )
    lastSalePrice = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="last_sale_price", allow_null=True
    )
    lastSaleDate = serializers.DateField(source="last_sale_date", allow_null=True)
    taxAssessedValue = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="tax_assessed_value", allow_null=True
    )
    annualTaxes = serializers.DecimalField(
        max_digits=12, decimal_places=2, source="annual_taxes", allow_null=True
    )


class LinksSerializer(serializers.Serializer):
    """Serializer for links nested object."""

    propertyDetail = serializers.URLField(source="property_detail_url")
    redfin = serializers.URLField(source="redfin_url")
    zillow = serializers.URLField(source="zillow_url")


class ForeclosurePropertySerializer(serializers.ModelSerializer):
    """Serializer for ForeclosureProperty model with nested objects."""

    propertyId = serializers.CharField(source="property_id")
    address = AddressSerializer(source="*")
    foreclosureDetails = ForeclosureDetailsSerializer(source="*")
    propertyDetails = PropertyDetailsSerializer(source="*")
    valuationData = ValuationDataSerializer(source="*")
    links = LinksSerializer(source="*")

    class Meta:
        model = ForeclosureProperty
        fields = [
            "propertyId",
            "address",
            "foreclosureDetails",
            "propertyDetails",
            "valuationData",
            "images",
            "links",
        ]


# Carrying Cost Serializers


class LocationSerializer(serializers.Serializer):
    """Serializer for property location."""

    address = serializers.CharField(max_length=255)
    county = serializers.CharField(max_length=128, required=False, allow_blank=True)
    state = serializers.CharField(max_length=2)
    zip = serializers.CharField(max_length=16, source="zip_code")


class PropertyDetailsInputSerializer(serializers.Serializer):
    """Serializer for property details input."""

    purchasePrice = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0
    )
    propertyType = serializers.ChoiceField(
        choices=["single-family", "condo", "multi-family", "commercial"],
        default="single-family",
    )
    squareFeet = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    bedrooms = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    bathrooms = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=0, required=False, allow_null=True
    )
    yearBuilt = serializers.IntegerField(min_value=1800, required=False, default=2000)
    location = LocationSerializer()


class FinancingSerializer(serializers.Serializer):
    """Serializer for financing details."""

    downPayment = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    loanAmount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    interestRate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    loanTermYears = serializers.IntegerField(min_value=1, max_value=50)
    closingCosts = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        default=Decimal("0"),
    )
    loanPoints = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        default=Decimal("0"),
    )


class OperatingExpensesSerializer(serializers.Serializer):
    """Serializer for operating expenses."""

    propertyTaxRate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0
    )
    insuranceAnnual = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    hoaMonthly = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, default=Decimal("0")
    )
    utilitiesMonthly = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, default=Decimal("0")
    )
    maintenanceAnnualPercent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, default=Decimal("1.0")
    )
    propertyManagementPercent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, default=Decimal("10")
    )
    vacancyRatePercent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100, default=Decimal("8")
    )


class RentalIncomeSerializer(serializers.Serializer):
    """Serializer for rental income."""

    monthlyRent = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    otherMonthlyIncome = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, default=Decimal("0")
    )


class CarryingCostRequestSerializer(serializers.Serializer):
    """Serializer for carrying cost calculation request."""

    propertyDetails = PropertyDetailsInputSerializer()
    financing = FinancingSerializer()
    operatingExpenses = OperatingExpensesSerializer()
    rentalIncome = RentalIncomeSerializer()
    investmentStrategy = serializers.ChoiceField(
        choices=["buy-and-hold", "flip", "vacation-rental"],
        default="buy-and-hold",
        required=False,
    )


# Auction Monitoring Serializers


class UserWatchlistSerializer(serializers.ModelSerializer):
    """Serializer for UserWatchlist model."""

    propertyId = serializers.CharField(source="property.property_id", read_only=True)
    property = ForeclosurePropertySerializer(read_only=True)
    addedAt = serializers.DateTimeField(source="added_at", read_only=True)

    class Meta:
        model = UserWatchlist
        fields = ["id", "propertyId", "property", "notes", "addedAt"]


class AuctionAlertSerializer(serializers.ModelSerializer):
    """Serializer for AuctionAlert model."""

    alertType = serializers.CharField(source="alert_type")
    isActive = serializers.BooleanField(source="is_active")
    propertyTypes = serializers.JSONField(source="property_types", required=False)
    minOpeningBid = serializers.DecimalField(
        source="min_opening_bid",
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    maxOpeningBid = serializers.DecimalField(
        source="max_opening_bid",
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    radiusMiles = serializers.IntegerField(
        source="radius_miles", required=False, allow_null=True
    )
    centerLatitude = serializers.DecimalField(
        source="center_latitude",
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    centerLongitude = serializers.DecimalField(
        source="center_longitude",
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    reminderDaysBefore = serializers.JSONField(
        source="reminder_days_before", required=False
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = AuctionAlert
        fields = [
            "id",
            "name",
            "alertType",
            "isActive",
            "states",
            "cities",
            "propertyTypes",
            "minOpeningBid",
            "maxOpeningBid",
            "radiusMiles",
            "centerLatitude",
            "centerLongitude",
            "reminderDaysBefore",
            "createdAt",
            "updatedAt",
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""

    notifyEmail = serializers.BooleanField(source="notify_email")
    notifySms = serializers.BooleanField(source="notify_sms")
    notifyPush = serializers.BooleanField(source="notify_push")
    notifyInApp = serializers.BooleanField(source="notify_in_app")
    quietHoursStart = serializers.TimeField(
        source="quiet_hours_start", required=False, allow_null=True
    )
    quietHoursEnd = serializers.TimeField(
        source="quiet_hours_end", required=False, allow_null=True
    )
    deviceTokens = serializers.JSONField(source="device_tokens", required=False)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "notifyEmail",
            "notifySms",
            "notifyPush",
            "notifyInApp",
            "quietHoursStart",
            "quietHoursEnd",
            "email",
            "phone",
            "deviceTokens",
            "createdAt",
            "updatedAt",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    notificationType = serializers.CharField(source="notification_type")
    propertyId = serializers.CharField(
        source="property.property_id", read_only=True, allow_null=True
    )
    isRead = serializers.BooleanField(source="is_read", read_only=True)
    isDismissed = serializers.BooleanField(source="is_dismissed", read_only=True)
    readAt = serializers.DateTimeField(
        source="read_at", read_only=True, allow_null=True
    )
    dismissedAt = serializers.DateTimeField(
        source="dismissed_at", read_only=True, allow_null=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notificationType",
            "priority",
            "title",
            "body",
            "propertyId",
            "url",
            "data",
            "isRead",
            "isDismissed",
            "readAt",
            "dismissedAt",
            "createdAt",
        ]
