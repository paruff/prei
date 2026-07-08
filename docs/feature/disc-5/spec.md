# DISC-5: Dallas County TX NTS Scraper (County Proof-of-Concept)

## Problem
Prei needs to ingest public Notice of Trustee Sale (NTS) records from county foreclosure data sources. Dallas County TX serves as the first county integration (proof-of-concept) because it publishes a freely accessible NTS list online.

## Requirements

### Functional
1. Fetch NTS listings from Dallas County public records via HTTP
2. Parse: property address, trustee name, lender/beneficiary, scheduled sale date, opening bid (if available)
3. Upsert parsed records into `CountyForeclosureNotice` model
4. Handle stale entries (mark records not seen in latest scrape as "removed"?)
5. Run via management command: `scrape_dallas_county_nts`

### Non-Functional
1. Respect rate limits (minimum 2s delay between requests)
2. Log errors without crashing the entire scrape
3. Return gracefully empty results if site structure changes (with warning log)
4. Idempotent: re-running the same scrape does not create duplicates

### Human Gate DISC-HG-3
- Manually visit the Dallas County foreclosure page
- Confirm URL structure, whether it serves JSON or HTML
- Confirm field names present in the source data
- Do not finalize the parser until confirmed

## Acceptance Criteria

### AC-1: Scraper returns parsed notices
```python
def test_dallas_county_scraper_returns_notices(mock_dallas_response):
    notices = scrape_dallas_county_nts()
    assert len(notices) > 0
```

### AC-2: Each notice has required fields
```python
def test_dallas_notice_has_required_fields(mock_dallas_response):
    notices = scrape_dallas_county_nts()
    for n in notices:
        assert n['address']
        assert n['notice_type'] == 'NTS'
        assert n['state'] == 'TX'
```

### AC-3: Sale date is TX-valid (first Tuesday)
```python
def test_dallas_notice_sale_date_is_first_tuesday():
    """TX law: NTS sales on first Tuesday. Spot-check parsed dates."""
    notices = scrape_dallas_county_nts()
    for n in notices:
        if n.get('sale_date'):
            assert n['sale_date'].weekday() == 1  # Tuesday
```
