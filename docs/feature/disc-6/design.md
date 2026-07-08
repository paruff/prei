# DISC-6 Design: ATTOM Preforeclosure Integration

## Architecture

### Existing: ATTOMAdapter
- `core/integrations/sources/attom_adapter.py`
- Provides: auth, rate limiting, error handling, HTTP transport
- Endpoints: `preforeclosure/detail` (with geoid/radius/postalcode params)
- Update: Add `postalcode` parameter support to `fetch_foreclosure_data()`

### New: attom_preforeclosure module
- `core/integrations/sources/attom_preforeclosure.py`
- `fetch_attom_preforeclosure(zip_code: str) → list[dict]`
  - Creates ATTOMAdapter, calls fetch_foreclosure_data with postalcode
  - Normalizes each result to CountyForeclosureNotice schema
- `_attom_stage_to_document_type(stage: str) → str`
  - Maps ATTOM foreclosure stage to DocumentType choice

### New: Management command
- `core/management/commands/fetch_attom_preforeclosure.py`
- CLI args: `--zip-code` (required), `--dry-run`
- Upserts into CountyForeclosureNotice

### New: Tests
- `core/tests/test_attom_preforeclosure.py`
- Mock ATTOM API responses at the `requests` level or patch adapter
- Test data normalization and model validation

## Data Flow

```
CLI ──> fetch_attom_preforeclosure command
         │
         ├─> attom_preforeclosure.fetch_attom_preforeclosure(zip_code)
         │       │
         │       ├─> ATTOMAdapter.fetch_foreclosure_data(postalcode=zip_code)
         │       │       │
         │       │       ├─> GET /preforeclosure/detail?postalcode=75201&radius=25
         │       │       └─> JSON response
         │       │
         │       ├─> _normalize_to_county_notice() per property
         │       │     Maps: caseNumber, address, city, state, zip,
         │       │            filingDate, auctionDate, unpaidBalance,
         │       │            lenderName, stage → documentType
         │       │
         │       └─> returns list[dict]
         │
         └─> for each notice:
               upsert into CountyForeclosureNotice
                 key: (case_number, county, state)
```

## Field Mapping: ATTOM → CountyForeclosureNotice

| ATTOM field | CountyForeclosureNotice | Notes |
|---|---|---|
| `preforeclosure.caseNumber` | `case_number` | |
| `preforeclosure.stage` | `document_type` | Mapped via `_attom_stage_to_document_type()` |
| `address.line1` | `address` | Street address |
| `address.locality` | `city` | |
| `address.countrySubd` | `state` | 2-letter code |
| `address.postal1` | `zip_code` | |
| `address.county` | `county` | |
| `preforeclosure.lenderName` | `lender_name` | |
| `preforeclosure.date` | `filing_date` | |
| `preforeclosure.auctionDate` | `sale_date` | |
| `preforeclosure.amount` | `unpaid_balance` | |
| `avm.amount.value` | `estimated_value` | |
| `address.latitude` / `longitude` | `raw_data` | Stored for audit |

## Document Type Mapping

| ATTOM stage | CountyForeclosureNotice.DocumentType |
|---|---|
| "preforeclosure" / "default" | `nod` (Notice of Default) |
| "lis pendens" | `lis_pendens` |
| "notice of sale" / "trustee" / "auction" | `nts` (Notice of Trustee Sale) |
| "reo" / "bank owned" | `sheriff_sale` / `auction` |

## File Inventory

| File | Type | Change |
|---|---|---|
| `core/integrations/sources/attom_adapter.py` | Modify | Add `postalcode` param to `fetch_foreclosure_data()` |
| `core/integrations/sources/attom_preforeclosure.py` | Create | New module with `fetch_attom_preforeclosure()` |
| `core/management/commands/fetch_attom_preforeclosure.py` | Create | Management command |
| `core/tests/test_attom_preforeclosure.py` | Create | Tests with mocked responses |
| `docs/feature/disc-6/spec.md` | Create | Specification |
| `docs/feature/disc-6/design.md` | Create | This document |
| `docs/feature/disc-6/tasks.json` | Create | Task tracking |
