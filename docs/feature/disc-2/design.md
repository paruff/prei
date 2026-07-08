# Design: DISC-2 — USDA REO Ingestion (data.gov feed)

## Impacted Components

| Component | Change |
|---|---|
| `core/models.py` | Extend UsdaProperty: add `REMOVED` status choice |
| `core/management/commands/ingest_usda_reo.py` | **New** — management command |
| `core/tests/test_ingestion/test_usda_reo.py` | **New** — test file |
| `core/tests/test_ingestion/conftest.py` | **Append** — USDA fixtures added |
| `core/migrations/0035_add_usda_removed_status.py` | **New** — migration for REMOVED status |

## DISC-HG-2 Findings (Schema Inspection)

Inspected the USDA data.gov catalog entry and downloaded the raw TXT file:

- **URL:** `https://www.sc.egov.usda.gov/data/files/Property/FSASFHFOREData9-7-18.txt`
- **Format:** Fixed-width text file (pipes, no delimiters)
- **Last Updated:** September 10, 2018 (dataset may be stale)
- **Fields identified per line:**
  - Flag/status character (col 1)
  - Auction time "00:00.0"
  - Sale date (e.g., `8/28/2018`)
  - Garage/parking info
  - Case number (numeric, ~8 digits) ← maps to `usda_case_number`
  - Bedrooms
  - Foundation type (Block, Slab, Poured)
  - City name
  - Property style (Ranch, 1.5 Story, Split Level, etc.)
  - Street address
  - State abbreviation
  - Square footage
  - Bathrooms (partial — varies)
  - Opening bid amount (on continuation lines)
- **Secondary format:** Continuation lines with auction venue, address, and sale time
- **Alternative source:** HTML web app at `https://properties.sc.egov.usda.gov/resales/public/home` (no API)

## Model Extension

### UsdaProperty — New Status Choice

```python
class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING = "pending", "Pending"
    SOLD = "sold", "Sold"
    REMOVED = "removed", "Removed"  # NEW
```

No new fields needed — UsdaProperty already has `list_price`, `lot_size_acres`,
and all address fields from DISC-0.

## Management Command: `ingest_usda_reo`

### Signature

```bash
python manage.py ingest_usda_reo [--dry-run] [--endpoint URL]
```

- `--dry-run`: Use embedded fixture data instead of HTTP; writes to DB
- `--endpoint`: Override the default USDA data.gov TXT URL

### Algorithm

1. If `--dry-run`: load fixture data instead of HTTP fetch
2. Fetch TXT from endpoint (or load fixture in dry-run mode)
3. Parse each record line using fixed-width field positions:
   - Extract `usda_case_number` (positions vary — use regex)
   - Extract `address`, `city`, `state` from known offsets
   - Extract `bedrooms`, `square_feet` from known offsets
4. Map extracted fields to UsdaProperty
5. Upsert using `usda_case_number` as unique key
6. Mark stale records as REMOVED
7. Log counts

### Data Mapping: USDA Fixed-Width TXT → UsdaProperty

| TXT field | UsdaProperty field | Extraction method |
|---|---|---|
| Case number (numeric) | `usda_case_number` | Regex `\b(\d{6,9})\b` from line |
| Street address | `address` | From known column range (~cols 105-130) |
| City | `city` | From known column range (~cols 60-75) |
| State (2-letter) | `state` | From state column (~cols 130-132) |
| Bedrooms | `bedrooms` | Single digit after case number |
| Square feet | `square_feet` | From square footage column |
| Opening bid amount | `list_price` | From continuation lines or bid column |
| Status | `status` | Default `active` unless marked sold |

## Constraints

- All currency fields use Decimal, never float (AGENTS.md rule 3)
- `--dry-run` flag per DISC-1 pattern
- Parser module extracted to `_parse_usda_line()` and `_parse_usda_continuation()` pure functions
- USDA feed is TXT, not JSON — parser handles fixed-width format

## Test Strategy

### Unit Tests (5 tests in `core/tests/test_ingestion/test_usda_reo.py`)

| Test | What it validates |
|---|---|
| `test_usda_ingest_creates_records` | Fresh ingestion creates N UsdaProperty records |
| `test_usda_ingest_upserts_not_duplicates` | Second run doesn't duplicate |
| `test_usda_ingest_marks_removed` | Stale records get `status='removed'` |
| `test_usda_parser_extracts_fields` | Fixed-width parser extracts correct fields |
| `test_usda_price_is_decimal` | `list_price` type-check |

### Fixtures (`core/tests/test_ingestion/conftest.py`)

- `mock_usda_response`: Returns fixture TXT lines with sample USDA REO properties
- `existing_usda_record`: Creates a UsdaProperty with a `usda_case_number` not in fixture set
