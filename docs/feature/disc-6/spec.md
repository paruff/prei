# DISC-6: ATTOM Preforeclosure Integration

## Problem
Prei needs to fetch pre-foreclosure notices (NOD, NTS, Lis Pendens) for target markets from the ATTOM Data Solutions API. The ATTOM adapter already exists (`core/integrations/sources/attom_adapter.py`) with a `fetch_foreclosure_data(geoid, radius)` endpoint, but it's not wired to the `CountyForeclosureNotice` model or exposed via a management command.

## Requirements

### Functional
1. Accept a ZIP code and fetch preforeclosure notices via the ATTOM API
2. Normalize ATTOM response fields to `CountyForeclosureNotice` schema
3. Map ATTOM foreclosure stage to `DocumentType` (NOD, NTS, Lis Pendens, etc.)
4. Upsert results into `CountyForeclosureNotice` keyed by `case_number + county + state`
5. Expose via `fetch_attom_preforeclosure` management command

### Non-Functional
1. Reuse existing `ATTOMAdapter` for auth, rate limiting, error handling
2. Handle API errors gracefully (return empty list, log warning)
3. ATTOM API key loaded from `ATTOM_API_KEY` environment variable

### Human Gate DISC-HG-4
- Read `core/integrations/sources/attom_adapter.py`
- Confirm which endpoints are already implemented
- Confirm whether ATTOM subscription covers NOD/NTS/REO data or only property details/comps

## Acceptance Criteria

### AC-1: Fetch returns list (empty is valid)
```python
def test_attom_preforeclosure_fetch_returns_notices(mock_attom_response):
    notices = fetch_attom_preforeclosure(zip_code='75201')
    assert len(notices) >= 0  # 0 is valid if no active notices
```

### AC-2: Each notice validates against CountyForeclosureNotice model
```python
def test_attom_notice_normalizes_to_county_notice_model(mock_attom_response):
    notices = fetch_attom_preforeclosure(zip_code='75201')
    for n in notices:
        obj = CountyForeclosureNotice(**n)
        obj.full_clean()  # validates model constraints
```
