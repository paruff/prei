# Specification: PREI Full Acquisition & Leasing Pipeline
# Written: 2026-07-07 session with paruff
# Companion to: discovery-brief-pipeline.md, design-pipeline.md, tasks-pipeline.json
# Status: Ready for implementation via opencode / DeepSeek

---

## 0. Corrections and Verified Facts From Codebase

| Fact | Source | Confidence |
|---|---|---|
| ForeclosureProperty has data_source, property_id, foreclosure_status fields | core/models.py verified | High |
| Listing has source field (choices: dummy, external) | core/models.py verified | High |
| Property is post-acquisition owned property | core/models.py verified | High |
| UserWatchlist links User → ForeclosureProperty | core/models.py verified | High |
| InvestmentAnalysis is OneToOne with Property | core/models.py verified | High |
| No pipeline stage tracking model exists | core/models.py verified | High |
| No screening criteria model exists | core/models.py verified | High |
| No offer, DD, closing, or renovation model exists | core/models.py verified | High |
| AuctionAlert exists but pipeline linkage is backlog | paruff confirmed | High |

---

## 1. Core Data Model: PipelineProperty

### 1.1 Purpose

PipelineProperty is the CRM record for a property moving through the
acquisition pipeline. It:
- Links to the source record (VrmProperty, ForeclosureProperty, Listing,
  or future sources) via source_type + source_id
- Tracks current pipeline stage and status
- Records kill reasons when a property is eliminated
- Links to InvestmentAnalysis when underwriting is triggered
- Converts to a Property record at acquisition

### 1.2 Pipeline Stages (acquisition)

```
DISCOVERED → SCREENING → UNDERWRITING → OFFER → DUE_DILIGENCE → CLOSING → ACQUIRED → RENOVATION → STABILIZED
```

Each stage has:
- Entry criteria (what must be true to enter this stage)
- Exit criteria (what must be true to advance to next stage)
- Kill criteria (what eliminates a property at this stage)

### 1.3 Pipeline Status

```
ACTIVE    — property is being actively worked
KILLED    — eliminated (kill_reason required)
ON_HOLD   — paused (hold_reason optional)
ACQUIRED  — successfully purchased (links to Property record)
```

### 1.4 Source Type Pattern

Rather than GenericForeignKey (which adds complexity and queryset friction),
use source_type + source_id:

```
source_type: CharField choices = [
    ('vrm', 'VRM Property'),
    ('foreclosure', 'Foreclosure Property'),
    ('listing', 'Listing'),
    ('manual', 'Manually Added'),
    ('hud', 'HUD Home'),        # future
    ('usda', 'USDA Property'),  # future
    ('fannie', 'Fannie Mae'),   # future
    ('freddie', 'Freddie Mac'), # future
    ('county', 'County Sale'),  # future
    ('bank_reo', 'Bank REO'),   # future
]
source_id: CharField — stores the PK of the source record as string
```

This is extensible without schema changes when new sources are added.

### 1.5 PipelineProperty Model Fields

```python
# Identity
user                  ForeignKey(User, CASCADE)
source_type           CharField(max_length=32, choices=SOURCE_TYPE_CHOICES)
source_id             CharField(max_length=128)  # PK of source record
address               CharField(max_length=255)  # denormalized for display
city                  CharField(max_length=128)
state                 CharField(max_length=2)
zip_code              CharField(max_length=16)
latitude              DecimalField(9,6, null=True)
longitude             DecimalField(9,6, null=True)

# Pipeline tracking
stage                 CharField(max_length=32, choices=STAGE_CHOICES, default='DISCOVERED')
status                CharField(max_length=16, choices=STATUS_CHOICES, default='ACTIVE')
kill_reason           CharField(max_length=255, blank=True)
kill_stage            CharField(max_length=32, blank=True)  # which stage killed it
hold_reason           CharField(max_length=255, blank=True)
notes                 TextField(blank=True)

# Stage timestamps (null until that stage is reached)
discovered_at         DateTimeField(auto_now_add=True)
screened_at           DateTimeField(null=True, blank=True)
underwriting_at       DateTimeField(null=True, blank=True)
offer_at              DateTimeField(null=True, blank=True)
due_diligence_at      DateTimeField(null=True, blank=True)
closing_at            DateTimeField(null=True, blank=True)
acquired_at           DateTimeField(null=True, blank=True)
renovation_at         DateTimeField(null=True, blank=True)
stabilized_at         DateTimeField(null=True, blank=True)

# Links to downstream records
investment_analysis   ForeignKey(InvestmentAnalysis, null=True, blank=True)
property_record       ForeignKey(Property, null=True, blank=True)  # set at acquisition

# Screening results (stored so user can review)
screening_score       DecimalField(5,2, null=True, blank=True)
screening_passed      BooleanField(null=True)  # null=not yet screened
screening_notes       TextField(blank=True)

# Metadata
created_at            DateTimeField(auto_now_add=True)
updated_at            DateTimeField(auto_now=True)
```

**Constraint:** UniqueConstraint on (user, source_type, source_id) —
a user cannot add the same property to their pipeline twice.

---

## 2. Screening Engine

### 2.1 Purpose

Eliminate 80–90% of properties before underwriting using fast, cheap
criteria. Screening must be near-instant — no external API calls.
All screening data must already exist on the source record.

### 2.2 ScreeningCriteria Model

User-configurable thresholds, one set per user (or use defaults).

```python
user                      OneToOneField(User, CASCADE)

# Price filters
max_price                 DecimalField(12,2, null=True)
min_price                 DecimalField(12,2, null=True)

# Yield filters
min_gross_yield_pct       DecimalField(5,2, null=True)
# gross yield = (annual rent / price) * 100
# I am not certain of a research-validated minimum — 8% is a common
# practitioner threshold. Verify before setting a default.

max_price_to_rent_ratio   DecimalField(6,2, null=True)
# price / monthly rent. Lower = better cashflow.
# Common practitioner range: 100–150 for strong cashflow markets.
# I do not have a verified research source for this range.

# Property filters
min_beds                  PositiveIntegerField(null=True)
max_beds                  PositiveIntegerField(null=True)
min_sqft                  PositiveIntegerField(null=True)
max_year_built            PositiveIntegerField(null=True)
# Note: older properties = higher capex risk. Common cutoff: 1980 or 1970.
# I do not have a verified research source for this specific threshold.

allowed_property_types    JSONField(default=list)
# e.g. ['single-family', 'duplex', 'triplex', 'fourplex']

allowed_states            JSONField(default=list)
# filter to landlord-friendly states

# Foreclosure stage filters
allowed_foreclosure_statuses JSONField(default=list)
# e.g. ['preforeclosure', 'reo', 'government']

# GACS filter
min_gacs_score            DecimalField(5,2, null=True)
# Only screen properties in markets above this GACS threshold
# Requires GrowthArea.gacs_score to be populated first

created_at                DateTimeField(auto_now_add=True)
updated_at                DateTimeField(auto_now=True)
```

### 2.3 Screening Logic

Screening is computed in `core/services/screening.py` (new file).
Not in the model. Not in the view.

```
screen_property(pipeline_property: PipelineProperty,
                criteria: ScreeningCriteria) -> ScreeningResult
```

Returns: passed (bool), score (0–100), notes (list of what passed/failed).

Scoring approach: each criterion that passes adds points; each hard
failure (e.g. wrong state, wrong property type) returns failed immediately
without computing further. This is the "fast kill" pattern.

**Important constraint:** Screening uses only data already on the source
record. No external API calls during screening (AGENTS.md rule 2).
If a field needed for screening is null on the source record, that
criterion is skipped and noted, not treated as a failure.

---

## 3. Offer Strategy

### 3.1 OfferRecord Model

```python
pipeline_property     ForeignKey(PipelineProperty, CASCADE)
offer_price           DecimalField(12,2)
offer_date            DateField()
offer_expiry          DateField(null=True, blank=True)
contingencies         JSONField(default=list)
# e.g. ['inspection', 'financing', 'appraisal']
status                CharField choices=[
                          ('pending', 'Pending'),
                          ('accepted', 'Accepted'),
                          ('rejected', 'Rejected'),
                          ('countered', 'Countered'),
                          ('withdrawn', 'Withdrawn'),
                      ]
counter_price         DecimalField(12,2, null=True, blank=True)
notes                 TextField(blank=True)
created_at            DateTimeField(auto_now_add=True)
```

A PipelineProperty can have multiple OfferRecords (counter-offers).
The most recent active one is the current offer.

---

## 4. Due Diligence

### 4.1 DueDiligenceChecklist Model

```python
pipeline_property     ForeignKey(PipelineProperty, CASCADE)

# Inspection
inspection_ordered    BooleanField(default=False)
inspection_date       DateField(null=True, blank=True)
inspection_passed     BooleanField(null=True)  # null=not yet completed
inspection_notes      TextField(blank=True)
inspection_cost       DecimalField(10,2, null=True, blank=True)

# Title
title_search_ordered  BooleanField(default=False)
title_clear           BooleanField(null=True)
title_notes           TextField(blank=True)

# Appraisal
appraisal_ordered     BooleanField(default=False)
appraisal_value       DecimalField(12,2, null=True, blank=True)
appraisal_date        DateField(null=True, blank=True)

# Insurance
insurance_quoted      BooleanField(default=False)
insurance_annual_cost DecimalField(10,2, null=True, blank=True)

# Contractor
contractor_bid        DecimalField(12,2, null=True, blank=True)
contractor_notes      TextField(blank=True)

# Final decision
go_no_go              CharField choices=[
                          ('pending', 'Pending'),
                          ('go', 'Go'),
                          ('no_go', 'No-Go'),
                      ] default='pending'
no_go_reason          CharField(max_length=255, blank=True)

created_at            DateTimeField(auto_now_add=True)
updated_at            DateTimeField(auto_now=True)
```

OneToOne with PipelineProperty — one DD checklist per property.

---

## 5. Acquisition / Closing

### 5.1 ClosingRecord Model

```python
pipeline_property     ForeignKey(PipelineProperty, CASCADE, OneToOne)
final_purchase_price  DecimalField(12,2)
closing_date          DateField()
closing_costs         DecimalField(10,2, default=0)
loan_amount           DecimalField(12,2, null=True, blank=True)
down_payment          DecimalField(12,2, null=True, blank=True)
lender                CharField(max_length=128, blank=True)
notes                 TextField(blank=True)
created_at            DateTimeField(auto_now_add=True)
```

On save: trigger conversion of PipelineProperty → Property record.
Set PipelineProperty.status = ACQUIRED, stage = ACQUIRED,
PipelineProperty.property_record = newly created Property.

**Note:** This trigger logic lives in a service function in
`core/services/pipeline.py`, not in the model save() method.
No business logic in model save() per architecture rules.

---

## 6. Renovation / Turnover

### 6.1 RenovationRecord Model

```python
pipeline_property     ForeignKey(PipelineProperty, CASCADE, OneToOne)
# Also link to Property once acquired
property_record       ForeignKey(Property, null=True, blank=True)

estimated_budget      DecimalField(12,2, default=0)
actual_cost           DecimalField(12,2, null=True, blank=True)
start_date            DateField(null=True, blank=True)
completion_date       DateField(null=True, blank=True)
contractor            CharField(max_length=128, blank=True)
scope_of_work         TextField(blank=True)
status                CharField choices=[
                          ('not_started', 'Not Started'),
                          ('in_progress', 'In Progress'),
                          ('complete', 'Complete'),
                      ] default='not_started'
notes                 TextField(blank=True)
created_at            DateTimeField(auto_now_add=True)
updated_at            DateTimeField(auto_now=True)
```

---

## 7. Leasing Pipeline

### 7.1 LeasingPipelineProperty Model

Separate from acquisition pipeline. Triggered when RenovationRecord.status
= complete (or manually by user).

```python
property_record       ForeignKey(Property, CASCADE)
user                  ForeignKey(User, CASCADE)

stage                 CharField choices=[
                          ('LISTING', 'Listed / Marketing'),
                          ('SHOWING', 'Showings Scheduled'),
                          ('APPLICATION', 'Application Received'),
                          ('SCREENING', 'Applicant Screening'),
                          ('APPROVED', 'Applicant Approved'),
                          ('LEASE_SIGNED', 'Lease Signed'),
                          ('MOVE_IN', 'Move-In Complete'),
                          ('STABILIZED', 'Stabilized'),
                      ] default='LISTING'
status                CharField choices=[
                          ('ACTIVE', 'Active'),
                          ('FILLED', 'Unit Filled'),
                          ('ON_HOLD', 'On Hold'),
                      ] default='ACTIVE'

# Listing details
asking_rent           DecimalField(10,2, null=True, blank=True)
listed_date           DateField(null=True, blank=True)
listing_source        CharField(max_length=128, blank=True)
# e.g. Zillow, Craigslist, word of mouth, property manager

# Applicant tracking (basic — not a full tenant management system)
applicant_name        CharField(max_length=128, blank=True)
application_date      DateField(null=True, blank=True)
screening_passed      BooleanField(null=True)
screening_notes       TextField(blank=True)

# Lease
lease_start_date      DateField(null=True, blank=True)
lease_end_date        DateField(null=True, blank=True)
signed_rent           DecimalField(10,2, null=True, blank=True)

# Timestamps
listed_at             DateTimeField(null=True, blank=True)
lease_signed_at       DateTimeField(null=True, blank=True)
stabilized_at         DateTimeField(null=True, blank=True)

created_at            DateTimeField(auto_now_add=True)
updated_at            DateTimeField(auto_now=True)
```

**Scope note:** This is basic leasing pipeline tracking — not a full
property management / tenant management system. Full tenant management
(maintenance requests, rent collection, lease renewals) is Phase 3
per the existing spec. This model supports the leasing pipeline nav
section without pre-building Phase 3.

---

## 8. Navigation Structure

### Confirmed top-level nav (paruff 2026-07-07):

```
Growth Areas | Purchase Pipeline | Portfolio | Leasing Pipeline
```

### Submenus:

**Growth Areas**
- Market Explorer (/growth-explorer/)
- Target Markets (/growth/) [ranked list]

**Purchase Pipeline**
- My Pipeline (/pipeline/) [kanban/list of all PipelineProperty]
- Add Property (/pipeline/add/)
- Screening Criteria (/pipeline/screening/settings/)
- VRM Foreclosures (/vrm/) [existing — discovery source]
- All Foreclosures (/foreclosures/) [existing ForeclosureProperty]

**Portfolio**
- Dashboard (/portfolio/) [existing]
- Add Property (/portfolio/add/) [existing]
- BRRRR Calculator (/brrrr/) [existing]

**Leasing Pipeline**
- Active Listings (/leasing/)
- Add Listing (/leasing/add/)

### Previous nav (to be replaced):
Buy / Maintain / Sell → replaced by the four sections above.

---

## 9. Service Layer (new files)

Per AGENTS.md rule 1 (finance math stays in services):

```
core/services/pipeline.py      — stage advancement, kill logic,
                                  Property conversion on acquisition
core/services/screening.py     — screening criteria evaluation
```

No business logic in models, views, or management commands.

---

## 10. Acceptance Criteria — Phase 1 (pipeline foundation)

- AC1: A user can add a VrmProperty to their pipeline from the VRM list view in one click
- AC2: A user can see all their pipeline properties grouped by stage
- AC3: A user can advance a property to the next stage or kill it with a reason
- AC4: Screening runs automatically when a property enters the pipeline and flags pass/fail
- AC5: A user can configure their own screening criteria
- AC6: A user can create an offer record against a pipeline property
- AC7: A user can create a DD checklist and mark items complete
- AC8: Closing a deal creates a Property record automatically
- AC9: A completed renovation can be converted to a leasing pipeline entry
- AC10: Nav reflects the four top-level sections with correct submenus
- AC11: All new models use Decimal for currency (never float)
- AC12: All migrations reviewed and approved by paruff before running

---

## 11. What Is Explicitly NOT In This Spec

- Automated property discovery or scraping
- MLS / IDX integration
- Full tenant management (maintenance, rent collection) — Phase 3
- AuctionAlert wiring to pipeline — backlog
- Multi-user pipeline sharing — post-alpha
- Email/SMS notifications for pipeline events — post-alpha
- Celery / background jobs — alpha constraint
