from __future__ import annotations

from rest_framework import serializers

from .models import ForeclosureProperty, GrowthArea


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
