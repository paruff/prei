# Design: DISC-0 — Source Data Models

## Impacted Components

| Component | Change |
|---|---|
| `core/models.py` | Add HudProperty, UsdaProperty, CountyForeclosureNotice models |
| `core/migrations/DISC-0_migration.py` | Generated migration (DO NOT RUN — attach for review) |

## Model Designs

### HudProperty

Stores raw property listings from HUD Homestore (hudhomestore.com).
Follows VrmProperty pattern with source-specific ID.

```python
class HudProperty(models.Model):
    """HUD Homestore REO property listing."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"
        CONTINGENT = "contingent", "Contingent"

    hud_case_number = models.CharField(max_length=64, unique=True, db_index=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16)
    county = models.CharField(max_length=128, blank=True, default="")
    list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    square_feet = models.IntegerField(null=True, blank=True)
    property_type = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, choices=Status.choices)
    listing_url = models.URLField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### UsdaProperty

Stores raw property listings from USDA Rural Development REO.

```python
class UsdaProperty(models.Model):
    """USDA Rural Development REO property listing."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"

    usda_case_number = models.CharField(max_length=64, unique=True, db_index=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16)
    county = models.CharField(max_length=128, blank=True, default="")
    list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    square_feet = models.IntegerField(null=True, blank=True)
    lot_size_acres = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=32, choices=Status.choices)
    listing_url = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### CountyForeclosureNotice

Stores public foreclosure notices from county records (NOD, NTS, Sheriff Sale).

```python
class CountyForeclosureNotice(models.Model):
    """Public foreclosure notice from county records."""

    class DocumentType(models.TextChoices):
        NOD = "nod", "Notice of Default"
        NTS = "nts", "Notice of Trustee Sale"
        SHERIFF_SALE = "sheriff_sale", "Sheriff Sale"
        LIS_PENDENS = "lis_pendens", "Lis Pendens"
        AUCTION = "auction", "Auction Calendar"

    case_number = models.CharField(max_length=128, unique=True, db_index=True)
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    borrower_name = models.CharField(max_length=255, blank=True, default="")
    lender_name = models.CharField(max_length=255, blank=True, default="")
    trustee_name = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    zip_code = models.CharField(max_length=16, blank=True, default="")
    county = models.CharField(max_length=128, db_index=True)
    filing_date = models.DateField(null=True, blank=True)
    sale_date = models.DateField(null=True, blank=True, db_index=True)
    auction_time = models.CharField(max_length=64, blank=True, default="")
    auction_location = models.TextField(blank=True, default="")
    opening_bid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unpaid_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    parcel_number = models.CharField(max_length=128, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    raw_data = models.JSONField(default=dict, blank=True)
    scraped_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Constraints

- All currency fields use Decimal, never float (AGENTS.md rule 3)
- Each model has at least one unique identifier from its source
- created_at/updated_at auto-timestamps on all models
- Migration file is generated but NOT run — attached for paruff review
