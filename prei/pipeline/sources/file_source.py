"""File-based discovery source — CSV/JSON file ingestion.

Reads property listings from structured files (CSV or JSON) and maps
columns to the canonical pipeline schema. Supports flexible column
mapping via a config file or sensible defaults.

This is the most practical "real" data source — counties and investors
routinely work with CSV downloads from recorder/assessor websites.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from prei.pipeline.sources.base import DiscoverySource

logger = logging.getLogger(__name__)

# Default column mappings for common CSV formats.
# Keys: canonical field names. Values: list of possible CSV column names
# (first match wins).
DEFAULT_COLUMN_MAP = {
    "id": ["id", "property_id", "parcel_number", "apn", "case_number"],
    "address": [
        "address",
        "street_address",
        "property_address",
        "full_address",
        "location",
    ],
    "price": [
        "price",
        "sale_price",
        "list_price",
        "opening_bid",
        "estimated_value",
        "judgment_amount",
    ],
    "rent": ["rent", "estimated_rent", "monthly_rent", "projected_rent"],
    "beds": ["beds", "bedrooms", "bed_count", "br", "bdrms"],
    "baths": ["baths", "bathrooms", "bath_count", "ba", "bthrms"],
    "sqft": ["sqft", "sq_ft", "square_feet", "living_area", "gla", "size"],
    "year_built": ["year_built", "year", "built", "yr_blt"],
}


class CsvFileSource(DiscoverySource):
    """Discovery source that reads structured property data from CSV files.

    Supports flexible column mapping — configurable via a dict mapping
    canonical fields to a list of possible CSV column names.

    Args:
        file_path: Path to the CSV file.
        column_map: Optional dict mapping canonical fields → list of
                    possible CSV column headers. Uses sensible defaults
                    for common county/MLS schemas if not provided.
        encoding: File encoding (default utf-8).
        delimiter: CSV delimiter (default comma).
    """

    def __init__(
        self,
        file_path: str,
        column_map: Optional[Dict[str, List[str]]] = None,
        encoding: str = "utf-8",
        delimiter: str = ",",
        label: Optional[str] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.column_map = column_map or DEFAULT_COLUMN_MAP
        self.encoding = encoding
        self.delimiter = delimiter
        self._label = label or self.file_path.stem

    @property
    def name(self) -> str:
        return f"csv_{self._label}"

    def fetch(
        self,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        limit: int = 500,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Read and parse CSV file, returning pipeline-compatible dicts.

        Args:
            state: Optional state filter — if provided, only records
                   where the address contains the state code are returned.
            zip_code: Optional ZIP code filter.
            limit: Max records to return.
        """
        if not self.file_path.exists():
            logger.error("CSV file not found: %s", self.file_path)
            return []

        listings: List[Dict[str, Any]] = []
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                if reader.fieldnames is None:
                    logger.warning("CSV file has no headers: %s", self.file_path)
                    return []

                for row_num, row in enumerate(reader):
                    if len(listings) >= limit:
                        break
                    try:
                        mapped = self._map_row(row, row_num)
                        if (
                            state
                            and state.upper() not in mapped.get("address", "").upper()
                        ):
                            continue
                        if zip_code and zip_code not in mapped.get("address", ""):
                            continue
                        listings.append(mapped)
                    except Exception as exc:
                        logger.debug("Skipping row %d: %s", row_num, exc)
                        continue
        except Exception as exc:
            logger.error("CSV read error for %s: %s", self.file_path, exc)
            return []

        logger.info(
            "CSV source loaded %d listings from %s (%d rows total)",
            len(listings),
            self._label,
            sum(1 for _ in open(self.file_path)) - 1 if self.file_path.exists() else 0,
        )
        return listings

    def _map_row(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Map a CSV row to a canonical listing dict using the column map."""
        mapped: Dict[str, Any] = {"_row": row_num}
        for canonical, headers in self.column_map.items():
            for header in headers:
                if header in row and row[header].strip():
                    mapped[canonical] = row[header].strip()
                    break
        return mapped


class JsonFileSource(DiscoverySource):
    """Discovery source that reads structured property data from JSON files.

    Expects either a list of objects or a dict with a 'properties'/'listings'
    key containing a list.

    Args:
        file_path: Path to the JSON file.
        label: Optional label for the source name.
    """

    def __init__(self, file_path: str, label: Optional[str] = None) -> None:
        self.file_path = Path(file_path)
        self._label = label or self.file_path.stem

    @property
    def name(self) -> str:
        return f"json_{self._label}"

    def fetch(
        self,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        limit: int = 500,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            logger.error("JSON file not found: %s", self.file_path)
            return []

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
        except Exception as exc:
            logger.error("JSON read error: %s", exc)
            return []

        if isinstance(data, list):
            all_listings = data
        elif isinstance(data, dict):
            all_listings = (
                data.get("properties") or data.get("listings") or data.get("data") or []
            )
        else:
            logger.warning("JSON root is not list/dict: %s", type(data))
            return []

        listings = []
        for item in all_listings[:limit]:
            if state and state.upper() not in str(item.get("address", "")).upper():
                continue
            listings.append(item)
        logger.info(
            "JSON source loaded %d listings from %s", len(listings), self._label
        )
        return listings
