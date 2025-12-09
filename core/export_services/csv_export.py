"""CSV export service for foreclosure properties and other data."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


class CSVExportService:
    """Service for exporting data to CSV format."""

    def __init__(self):
        """Initialize CSV export service with field mappings."""
        self.foreclosure_field_mapping = {
            "property_id": "Property ID",
            "street": "Address",
            "city": "City",
            "state": "State",
            "zip_code": "ZIP",
            "foreclosure_status": "Foreclosure Stage",
            "filing_date": "Filing Date",
            "auction_date": "Auction Date",
            "opening_bid": "Opening Bid",
            "estimated_value": "Estimated Value",
            "bedrooms": "Bedrooms",
            "bathrooms": "Bathrooms",
            "square_footage": "Square Feet",
            "property_type": "Property Type",
            "lender_name": "Lender",
            "data_source": "Data Source",
            "data_timestamp": "Last Updated",
        }

    def export_foreclosures(
        self, properties: List[Dict[str, Any]], fields: Optional[List[str]] = None
    ) -> str:
        """
        Export foreclosure properties to CSV.

        Args:
            properties: List of property dictionaries
            fields: Optional list of fields to include (uses all if not specified)

        Returns:
            CSV content as string
        """
        # Use all fields if none specified
        if not fields:
            fields = list(self.foreclosure_field_mapping.keys())

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[self.foreclosure_field_mapping[f] for f in fields],
            quoting=csv.QUOTE_ALL,
        )

        # Write header
        writer.writeheader()

        # Write data rows
        for prop in properties:
            row = {}
            for field in fields:
                value = prop.get(field)
                header = self.foreclosure_field_mapping[field]
                row[header] = self._format_value(value)
            writer.writerow(row)

        return output.getvalue()

    def _format_value(self, value: Any) -> str:
        """
        Format value for CSV output.

        Args:
            value: Value to format

        Returns:
            Formatted string value
        """
        if value is None:
            return ""
        elif isinstance(value, (int, float, Decimal)):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return str(value)

    def generate_filename(
        self,
        export_type: str,
        location: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate descriptive filename.

        Args:
            export_type: Type of export (e.g., 'foreclosures')
            location: Optional location string
            filters: Optional filter dictionary

        Returns:
            Generated filename with .csv extension
        """
        parts = [export_type]

        if location:
            # Clean location for filename
            location_clean = (
                location.lower().replace(" ", "_").replace(",", "").replace("/", "_")
            )
            parts.append(location_clean)

        if filters:
            if filters.get("stage"):
                stages = filters["stage"]
                if isinstance(stages, list):
                    parts.append("_".join(stages))

        # Add date
        date_str = datetime.now().strftime("%Y-%m-%d")
        parts.append(date_str)

        return "_".join(parts) + ".csv"
