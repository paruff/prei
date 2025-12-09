"""Integration tests for export API endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import ForeclosureProperty

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def auth_client(api_client, user):
    """Create authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def foreclosure_properties(db):
    """Create test foreclosure properties."""
    properties = []
    
    # Create properties in Miami, FL
    for i in range(5):
        prop = ForeclosureProperty.objects.create(
            property_id=f"FC-FL-MD-{12345 + i}",
            data_source="TEST",
            data_timestamp=timezone.now(),
            street=f"{100 + i} Ocean Drive",
            city="Miami",
            state="FL",
            zip_code="33139",
            foreclosure_status="auction",
            auction_date=datetime(2024, 12, 20),
            opening_bid=Decimal(f"{250000 + i * 10000}"),
            estimated_value=Decimal(f"{400000 + i * 10000}"),
            bedrooms=3,
            bathrooms=Decimal("2.0"),
            square_footage=1800 + i * 50,
            property_type="single-family",
            lender_name="Test Bank",
        )
        properties.append(prop)
    
    return properties


@pytest.mark.django_db
class TestExportForeclosuresCSV:
    """Test CSV export endpoint."""

    def test_export_foreclosures_csv_success(self, api_client, foreclosure_properties):
        """Test successful CSV export."""
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {
                "location": "Miami, FL",
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "text/csv"
        assert "Content-Disposition" in response
        assert "foreclosures" in response["Content-Disposition"]
        
        # Check CSV content
        content = response.content.decode("utf-8")
        assert "Property ID" in content
        assert "FC-FL-MD-12345" in content

    def test_export_foreclosures_csv_with_filters(self, api_client, foreclosure_properties):
        """Test CSV export with filters applied."""
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {
                "location": "Miami, FL",
                "stage": "auction",
                "minPrice": "260000",
                "maxPrice": "290000",
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check that filtered properties are in CSV
        content = response.content.decode("utf-8")
        assert "FC-FL-MD-12346" in content  # 260,000
        assert "FC-FL-MD-12347" in content  # 270,000
        assert "FC-FL-MD-12348" in content  # 280,000

    def test_export_foreclosures_csv_with_field_selection(self, api_client, foreclosure_properties):
        """Test CSV export with specific field selection."""
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {
                "location": "Miami, FL",
            },
            "fields": ["property_id", "street", "city", "state", "opening_bid"],
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        
        content = response.content.decode("utf-8")
        lines = content.split("\n")
        
        # Check header has only selected fields
        header = lines[0]
        assert "Property ID" in header
        assert "Address" in header
        assert "City" in header
        assert "State" in header
        assert "Opening Bid" in header
        
        # Check that non-selected fields are not in header
        assert "Bedrooms" not in header
        assert "Square Feet" not in header

    def test_export_foreclosures_csv_missing_location(self, api_client):
        """Test CSV export fails without location."""
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {}
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_export_foreclosures_csv_invalid_location(self, api_client):
        """Test CSV export fails with invalid location."""
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {
                "location": "",  # Empty location
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_export_foreclosures_csv_empty_results(self, api_client):
        """Test CSV export with no matching properties."""
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {
                "location": "Phoenix, AZ",  # No properties in this location
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        # Should still return CSV with headers
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode("utf-8")
        assert "Property ID" in content  # Header present


@pytest.mark.django_db
class TestExportForeclosuresJSON:
    """Test JSON export endpoint."""

    def test_export_foreclosures_json_success(self, api_client, foreclosure_properties):
        """Test successful JSON export."""
        url = reverse("api:export-foreclosures-json")
        
        data = {
            "filters": {
                "location": "Miami, FL",
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/json"
        assert "Content-Disposition" in response
        
        # Parse JSON content
        content = json.loads(response.content.decode("utf-8"))
        
        # Check metadata
        assert "metadata" in content
        assert "version" in content["metadata"]
        assert "exportedAt" in content["metadata"]
        assert "exportType" in content["metadata"]
        assert content["metadata"]["exportType"] == "foreclosures"
        assert "recordCount" in content["metadata"]
        
        # Check data
        assert "data" in content
        assert len(content["data"]) == 5

    def test_export_foreclosures_json_includes_filters(self, api_client, foreclosure_properties):
        """Test JSON export includes filter information in metadata."""
        url = reverse("api:export-foreclosures-json")
        
        data = {
            "filters": {
                "location": "Miami, FL",
                "stage": "auction",
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        
        content = json.loads(response.content.decode("utf-8"))
        
        # Check that filters are in metadata
        assert "filters" in content["metadata"]
        assert content["metadata"]["filters"]["location"] == "Miami, FL"
        assert content["metadata"]["filters"]["stage"] == "auction"

    def test_export_foreclosures_json_authenticated_user(self, auth_client, foreclosure_properties):
        """Test JSON export includes user email for authenticated users."""
        url = reverse("api:export-foreclosures-json")
        
        data = {
            "filters": {
                "location": "Miami, FL",
            }
        }
        
        response = auth_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        
        content = json.loads(response.content.decode("utf-8"))
        
        # Check that user email is in metadata
        assert content["metadata"]["exportedBy"] == "test@example.com"


@pytest.mark.django_db
class TestExportPropertyAnalysisPDF:
    """Test PDF export endpoint."""

    def test_export_property_analysis_pdf_success(self, auth_client):
        """Test successful PDF export."""
        url = reverse("api:export-property-pdf")
        
        data = {
            "propertyData": {
                "address": "123 Ocean Drive, Miami, FL 33139",
                "purchasePrice": 300000,
                "propertyType": "single-family",
                "squareFeet": 1850,
            },
            "analysisResults": {
                "carryingCosts": {
                    "monthly": {
                        "mortgage": 1500.00,
                        "propertyTax": 300.00,
                        "insurance": 150.00,
                        "maintenance": 100.00,
                        "total": 2050.00,
                    },
                    "annual": {
                        "mortgage": 18000.00,
                        "propertyTax": 3600.00,
                        "insurance": 1800.00,
                        "maintenance": 1200.00,
                        "total": 24600.00,
                    },
                },
                "cashFlow": {
                    "monthly": {
                        "grossRentalIncome": 2500.00,
                        "operatingExpenses": 550.00,
                        "debtService": 1500.00,
                        "netCashFlow": 450.00,
                    },
                },
                "investmentMetrics": {
                    "cocReturn": 8.5,
                    "capRate": 6.2,
                },
            },
        }
        
        response = auth_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert "Content-Disposition" in response
        assert "property_analysis" in response["Content-Disposition"]
        
        # Check PDF magic number
        assert response.content[:4] == b'%PDF'

    def test_export_property_analysis_pdf_requires_auth(self, api_client):
        """Test PDF export requires authentication."""
        url = reverse("api:export-property-pdf")
        
        data = {
            "propertyData": {"address": "Test"},
            "analysisResults": {},
        }
        
        response = api_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_export_property_analysis_pdf_missing_data(self, auth_client):
        """Test PDF export fails with missing required data."""
        url = reverse("api:export-property-pdf")
        
        # Missing analysisResults
        data = {
            "propertyData": {"address": "Test"},
        }
        
        response = auth_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_export_property_analysis_pdf_file_size(self, auth_client):
        """Test PDF export file size is reasonable."""
        url = reverse("api:export-property-pdf")
        
        data = {
            "propertyData": {
                "address": "123 Ocean Drive",
                "purchasePrice": 300000,
                "propertyType": "single-family",
            },
            "analysisResults": {
                "carryingCosts": {
                    "monthly": {"total": 2000.00},
                    "annual": {"total": 24000.00},
                },
            },
        }
        
        response = auth_client.post(url, data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check file size is less than 5MB
        assert len(response.content) < 5 * 1024 * 1024


@pytest.mark.django_db
class TestExportSizeLimits:
    """Test export size limits."""

    def test_csv_export_rejects_large_exports(self, api_client, db):
        """Test that CSV export rejects exports larger than 500 properties."""
        # Create 501 properties
        for i in range(501):
            ForeclosureProperty.objects.create(
                property_id=f"FC-TEST-{i:05d}",
                data_source="TEST",
                data_timestamp=timezone.now(),
                street=f"{i} Test St",
                city="Miami",
                state="FL",
                zip_code="33139",
                foreclosure_status="auction",
            )
        
        url = reverse("api:export-foreclosures-csv")
        
        data = {
            "filters": {
                "location": "Miami, FL",
            }
        }
        
        response = api_client.post(url, data, format="json")
        
        # Should reject as too large
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "EXPORT_TOO_LARGE" in response.data["code"]
        assert "totalCount" in response.data
        assert response.data["totalCount"] == 501
