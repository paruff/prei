"""Unit tests for export services."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal


from core.export_services import CSVExportService, JSONExportService, PDFExportService


class TestCSVExportService:
    """Test CSV export service."""

    def test_export_foreclosures_generates_valid_csv(self):
        """Test that CSV export generates valid RFC 4180 compliant CSV."""
        service = CSVExportService()

        properties = [
            {
                "property_id": "FC-FL-MD-12345",
                "street": "123 Ocean Drive",
                "city": "Miami",
                "state": "FL",
                "zip_code": "33139",
                "foreclosure_status": "auction",
                "filing_date": datetime(2024, 8, 15),
                "auction_date": datetime(2024, 12, 20),
                "opening_bid": Decimal("285000.00"),
                "estimated_value": Decimal("425000.00"),
                "bedrooms": 3,
                "bathrooms": Decimal("2.0"),
                "square_footage": 1850,
                "property_type": "single-family",
                "lender_name": "Wells Fargo Bank",
                "data_source": "ATTOM",
                "data_timestamp": datetime(2024, 12, 8, 10, 30, 0),
            }
        ]

        csv_content = service.export_foreclosures(properties)

        # Check that CSV has header
        assert "Property ID" in csv_content
        assert "Address" in csv_content
        assert "City" in csv_content

        # Check that data is present
        assert "FC-FL-MD-12345" in csv_content
        assert "Miami" in csv_content
        assert "FL" in csv_content

    def test_export_foreclosures_handles_special_characters(self):
        """Test that CSV export handles special characters correctly."""
        service = CSVExportService()

        properties = [
            {
                "property_id": "TEST-123",
                "street": 'Property "With" Quotes',
                "city": "Miami, Beach",
                "state": "FL",
                "zip_code": "33139",
                "foreclosure_status": "auction",
                "filing_date": None,
                "auction_date": None,
                "opening_bid": None,
                "estimated_value": None,
                "bedrooms": 0,
                "bathrooms": Decimal("0.0"),
                "square_footage": 0,
                "property_type": "",
                "lender_name": "",
                "data_source": "TEST",
                "data_timestamp": datetime.now(),
            }
        ]

        csv_content = service.export_foreclosures(properties)

        # Check that special characters are handled
        assert (
            'Property "With" Quotes' in csv_content
            or 'Property ""With"" Quotes' in csv_content
        )

    def test_export_foreclosures_with_selected_fields(self):
        """Test that CSV export respects field selection."""
        service = CSVExportService()

        properties = [
            {
                "property_id": "TEST-123",
                "street": "123 Main St",
                "city": "Miami",
                "state": "FL",
                "zip_code": "33139",
                "foreclosure_status": "auction",
                "filing_date": None,
                "auction_date": None,
                "opening_bid": None,
                "estimated_value": None,
                "bedrooms": 0,
                "bathrooms": Decimal("0.0"),
                "square_footage": 0,
                "property_type": "",
                "lender_name": "",
                "data_source": "TEST",
                "data_timestamp": datetime.now(),
            }
        ]

        # Export only specific fields
        fields = ["property_id", "street", "city", "state"]
        csv_content = service.export_foreclosures(properties, fields)

        # Check that selected fields are present
        assert "Property ID" in csv_content
        assert "Address" in csv_content
        assert "City" in csv_content
        assert "State" in csv_content

        # Check that non-selected fields are not in header
        assert "Bedrooms" not in csv_content
        assert "Square Feet" not in csv_content

    def test_generate_filename_with_location(self):
        """Test that filename generation includes location."""
        service = CSVExportService()

        filename = service.generate_filename("foreclosures", "Miami, FL", None)

        assert "foreclosures" in filename
        assert "miami" in filename
        assert "fl" in filename
        assert ".csv" in filename
        assert datetime.now().strftime("%Y-%m-%d") in filename

    def test_generate_filename_with_filters(self):
        """Test that filename generation includes filter information."""
        service = CSVExportService()

        filename = service.generate_filename(
            "foreclosures", "Miami, FL", {"stage": ["auction", "reo"]}
        )

        assert "auction" in filename or "reo" in filename


class TestJSONExportService:
    """Test JSON export service."""

    def test_export_with_metadata_includes_required_fields(self):
        """Test that JSON export includes all required metadata fields."""
        service = JSONExportService()

        data = [
            {
                "id": "FC-FL-MD-12345",
                "address": "123 Ocean Drive",
                "city": "Miami",
                "state": "FL",
            }
        ]

        filters = {
            "location": "Miami, FL",
            "stage": ["auction"],
        }

        json_content = service.export_with_metadata(
            data, "foreclosures", filters, "user@example.com"
        )

        # Parse JSON
        obj = json.loads(json_content)

        # Check metadata fields
        assert "metadata" in obj
        assert "version" in obj["metadata"]
        assert "exportedAt" in obj["metadata"]
        assert "exportedBy" in obj["metadata"]
        assert "exportType" in obj["metadata"]
        assert "recordCount" in obj["metadata"]
        assert "filters" in obj["metadata"]

        # Check data field
        assert "data" in obj
        assert len(obj["data"]) == 1

    def test_export_handles_decimal_values(self):
        """Test that JSON export correctly serializes Decimal values."""
        service = JSONExportService()

        data = [
            {
                "id": "TEST-123",
                "price": Decimal("285000.50"),
                "bedrooms": 3,
            }
        ]

        json_content = service.export_with_metadata(data, "foreclosures", None, None)

        # Parse JSON
        obj = json.loads(json_content)

        # Check that Decimal was converted to float
        assert obj["data"][0]["price"] == 285000.50

    def test_validate_json_schema_valid(self):
        """Test JSON schema validation for valid JSON."""
        service = JSONExportService()

        valid_json = json.dumps({"metadata": {"version": "1.0"}, "data": []})

        assert service.validate_json_schema(valid_json) is True

    def test_validate_json_schema_invalid(self):
        """Test JSON schema validation for invalid JSON."""
        service = JSONExportService()

        # Missing required field
        invalid_json = json.dumps({"metadata": {"version": "1.0"}})

        assert service.validate_json_schema(invalid_json) is False

    def test_validate_json_schema_malformed(self):
        """Test JSON schema validation for malformed JSON."""
        service = JSONExportService()

        malformed_json = "not valid json"

        assert service.validate_json_schema(malformed_json) is False


class TestPDFExportService:
    """Test PDF export service."""

    def test_generate_property_analysis_report_returns_bytes(self):
        """Test that PDF generation returns bytes."""
        service = PDFExportService()

        property_data = {
            "address": "123 Ocean Drive, Miami, FL 33139",
            "purchasePrice": 300000,
            "propertyType": "single-family",
            "squareFeet": 1850,
        }

        analysis_results = {
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
        }

        pdf_bytes = service.generate_property_analysis_report(
            property_data, analysis_results, None
        )

        # Check that we got bytes back
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

        # Check PDF magic number
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_property_analysis_report_handles_missing_data(self):
        """Test that PDF generation handles missing optional data."""
        service = PDFExportService()

        property_data = {
            "address": "Test Property",
            "purchasePrice": 200000,
            "propertyType": "condo",
        }

        analysis_results = {}

        # Should not raise exception
        pdf_bytes = service.generate_property_analysis_report(
            property_data, analysis_results, None
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_generate_filename_creates_valid_filename(self):
        """Test that PDF filename generation creates valid filenames."""
        service = PDFExportService()

        filename = service.generate_filename("123 Ocean Drive, Miami, FL")

        assert filename.endswith(".pdf")
        assert "property_analysis" in filename
        assert datetime.now().strftime("%Y-%m-%d") in filename

        # Check that special characters are removed
        assert "," not in filename
        assert " " not in filename or "_" in filename

    def test_pdf_file_size_reasonable(self):
        """Test that generated PDF file size is reasonable."""
        service = PDFExportService()

        property_data = {
            "address": "123 Ocean Drive, Miami, FL 33139",
            "purchasePrice": 300000,
            "propertyType": "single-family",
        }

        analysis_results = {
            "carryingCosts": {
                "monthly": {"total": 2000.00},
                "annual": {"total": 24000.00},
            },
        }

        pdf_bytes = service.generate_property_analysis_report(
            property_data, analysis_results, None
        )

        # Check that file size is reasonable (less than 5MB as per spec)
        assert len(pdf_bytes) < 5 * 1024 * 1024
