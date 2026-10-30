"""JSON export service for structured data exports."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


class JSONExportService:
    """Service for exporting data to JSON format."""

    def export_with_metadata(
        self,
        data: List[Dict[str, Any]],
        export_type: str,
        filters: Optional[Dict[str, Any]] = None,
        user_email: Optional[str] = None,
    ) -> str:
        """
        Export data to JSON with metadata.

        Args:
            data: List of data dictionaries to export
            export_type: Type of export (e.g., 'foreclosures')
            filters: Optional filters applied to the data
            user_email: Optional user email who initiated export

        Returns:
            JSON string with metadata and data
        """
        export_obj = {
            "metadata": {
                "version": "1.0",
                "exportedAt": datetime.now().isoformat(),
                "exportedBy": user_email,
                "exportType": export_type,
                "recordCount": len(data),
                "filters": filters or {},
            },
            "data": data,
        }

        return json.dumps(export_obj, indent=2, default=self._json_serializer)

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer for special types.

        Args:
            obj: Object to serialize

        Returns:
            Serializable representation of object
        """
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def validate_json_schema(self, json_str: str) -> bool:
        """
        Validate JSON against schema.

        Args:
            json_str: JSON string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            obj = json.loads(json_str)
            # Check required fields
            required = ["metadata", "data"]
            return all(field in obj for field in required)
        except (json.JSONDecodeError, TypeError):
            return False

    def generate_filename(
        self,
        export_type: str,
        location: Optional[str] = None,
    ) -> str:
        """
        Generate descriptive filename for JSON export.

        Args:
            export_type: Type of export
            location: Optional location string

        Returns:
            Generated filename with .json extension
        """
        parts = [export_type]

        if location:
            # Clean location for filename
            location_clean = (
                location.lower().replace(" ", "_").replace(",", "").replace("/", "_")
            )
            parts.append(location_clean)

        # Add date
        date_str = datetime.now().strftime("%Y-%m-%d")
        parts.append(date_str)

        return "_".join(parts) + ".json"
