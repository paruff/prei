# core/export_services

## Overview
Stateless service classes that serialise property and foreclosure data to CSV, JSON and PDF. Re-exported from `__init__.py`.

## Interface
- `CSVExportService` (csv_export.py): `export_foreclosures(properties, fields=None) -> str`, `generate_filename(...)`.
- `JSONExportService` (json_export.py): `export_with_metadata(data, export_type, filters=None, user_email=None) -> str`, `validate_json_schema(json_str) -> bool`, `generate_filename(...)`.
- `PDFExportService` (pdf_export.py): `generate_property_analysis_report(property_data, analysis_results, user_branding=None) -> bytes`, `generate_filename(...)`.

## Invariants
- `__all__` in `__init__.py` lists exactly the three services.
- csv_export.py raises `ValueError` for invalid input (see the `raise` near line 62).
- Services take plain dicts, not model instances.

## Side Effects
- None on the database or network. PDF output is built in memory (reportlab, matplotlib charts, `io`).

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)
