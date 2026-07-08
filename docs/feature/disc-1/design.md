# Design: DISC-1 — HUD REO Ingestion (data.gov feed)

## Impacted Components

| Component | Change |
|---|---|
| `core/models.py` | Extend HudProperty: add `REMOVED` status, `asking_price`, `insured_status` fields |
| `core/management/commands/ingest_hud_reo.py` | **New** — management command |
| `core/tests/test_ingestion/test_hud_reo.py` | **New** — test file |
| `core/tests/test_ingestion/conftest.py` | **New** — test fixtures (mock_hud_response, existing_hud_record) |
| `core/migrations/0034_add_hud_reo_fields.py` | **New** — migration for model changes |

## Model Extensions

### HudProperty — New Status Choice

```python
class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING = "pending", "Pending"
    SOLD = "sold", "Sold"
    CONTINGENT = "contingent", "Contingent"
    REMOVED = "removed", "Removed"  # NEW
```

### HudProperty — New Fields

```python
asking_price = models.DecimalField(
    max_digits=12,
    decimal_places=2,
    null=True,
    blank=True,
    validators=[MinValueValidator(Decimal("0"))],
)
insured_status = models.CharField(
    max_length=32,
    choices=InsuredStatus.choices,
    blank=True,
    default="",
)
```

### HudProperty — New Inner Class

```python
class InsuredStatus(models.TextChoices):
    FHA_INSURED = "fha_insured", "FHA Insured"
    CONVENTIONAL = "conventional", "Conventional"
    UNINSURED = "uninsured", "Uninsured"
    VA = "va", "VA"
```

## Management Command: `ingest_hud_reo`

### Signature

```bash
python manage.py ingest_hud_reo [--dry-run] [--endpoint URL]
```

- `--dry-run`: Log what *would* happen but don't make network calls or write to DB
- `--endpoint`: Override the default data.gov HUD REO JSON URL (default: `DEFAULT_ENDPOINT` constant — see human gate DISC-HG-1)

### Algorithm

1. If `--dry-run`: load fixture data instead of HTTP fetch, skip DB writes
2. Fetch JSON from endpoint (or load fixture in dry-run mode)
3. Parse each record:
   - Map `case_number` → `hud_case_number`
   - Map `asking_price` → `asking_price`
   - Map `street_address`, `city`, `state`, `zip` → address fields
   - Map `status` → `status` (active/pending/sold)
   - Map `insured_status` → `insured_status`
   - Set `scraped_at` and `last_seen_at` to now
4. Upsert using `hud_case_number` as unique key:
   - `HudProperty.objects.update_or_create(hud_case_number=..., defaults={...})`
5. After upsert: mark `status='removed'` for records in DB whose `hud_case_number` not in fetched set
6. Log counts: `Added: N, Updated: M, Removed: R`

### Dry-Run Behavior

- `--dry-run`: Skip HTTP fetch, skip DB writes, use an internal fixture JSON, still compute logs
- Test fixtures replace the HTTP endpoint entirely via `unittest.mock.patch`

## Data Mapping: data.gov JSON → HudProperty

| data.gov field | HudProperty field | Notes |
|---|---|---|
| `case_number` | `hud_case_number` | Unique key for upsert |
| `asking_price` | `asking_price` | Decimal, nullable |
| `street_address` | `address` | |
| `city` | `city` | |
| `state` | `state` | |
| `zip` | `zip_code` | |
| `county` | `county` | |
| `bedrooms` | `bedrooms` | |
| `bathrooms` | `bathrooms` | |
| `square_feet` | `square_feet` | |
| `property_type` | `property_type` | |
| `status` | `status` | Maps HUD statuses to HudProperty.Status |
| `insured_status` | `insured_status` | New field |
| `listing_url` | `listing_url` | |
| `image_url` | `image_url` | |
| `description` | `description` | |

## Constraints

- All currency fields use Decimal, never float (AGENTS.md rule 3)
- `--dry-run` flag per existing pattern (cf. `collect_fannie_mae --dry-run`)
- Test fixtures in `core/tests/test_ingestion/` (not in `core/fixtures/`) — co-located with tests
- URL endpoint is a module-level constant gated by DISC-HG-1

## Test Strategy

### Unit Tests (5 tests in `core/tests/test_ingestion/test_hud_reo.py`)

| Test | What it validates |
|---|---|
| `test_hud_ingest_creates_records` | Fresh ingestion creates `N` HudProperty records |
| `test_hud_ingest_upserts_not_duplicates` | Second run doesn't duplicate |
| `test_hud_ingest_marks_removed` | Stale records get `status='removed'` |
| `test_hud_price_is_decimal` | `asking_price` type-check |
| `test_hud_insured_status_choices` | `insured_status` enum validation |

### BDD Scenarios (in `core/tests/test_ingestion/test_hud_reo_bdd.py`)

| Scenario | Gherkin |
|---|---|
| Fresh ingest creates records | Given 50 properties in feed → When ingest runs → Then 50 HudProperty records with status 'active' |
| Re-ingest no duplicates | Given 50 records exist → When ingest runs with same feed → Then count is still 50 |

### Fixtures (`core/tests/test_ingestion/conftest.py`)

- `mock_hud_response`: Returns fixture JSON with N sample HUD REO properties
- `existing_hud_record`: Creates a HudProperty record with a `hud_case_number` *not* in the fixture set
