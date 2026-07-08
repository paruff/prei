# Design: PREI Full Acquisition & Leasing Pipeline
# Written: 2026-07-07 session with paruff
# Companion to: discovery-brief-pipeline.md, specification-pipeline.md, tasks-pipeline.json
# Status: Ready for implementation via opencode / DeepSeek

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAVIGATION                                │
│  Growth Areas | Purchase Pipeline | Portfolio | Leasing Pipeline │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐   ┌──────────────────────────────────────────────┐
│ Growth Areas │   │           Purchase Pipeline                   │
│              │   │                                               │
│ GACS scoring │──▶│ DISCOVERED → SCREENING → UNDERWRITING →      │
│ Market rank  │   │ OFFER → DUE_DILIGENCE → CLOSING →            │
│ Target MSAs  │   │ ACQUIRED → RENOVATION → STABILIZED           │
└──────────────┘   └─────────────────────┬────────────────────────┘
                                         │ at ACQUIRED
                                         ▼
                   ┌─────────────────────────────────────────────┐
                   │              Portfolio                        │
                   │  Property record + MonthlyActuals + Analysis │
                   └─────────────────────┬───────────────────────┘
                                         │ at rent-ready
                                         ▼
                   ┌─────────────────────────────────────────────┐
                   │           Leasing Pipeline                    │
                   │  LISTING → SHOWING → APPLICATION →           │
                   │  SCREENING → APPROVED → LEASE_SIGNED →       │
                   │  MOVE_IN → STABILIZED                        │
                   └─────────────────────────────────────────────┘
```

---

## 2. New File Structure

```
core/
  models.py                    — add PipelineProperty, ScreeningCriteria,
                                  OfferRecord, DueDiligenceChecklist,
                                  ClosingRecord, RenovationRecord,
                                  LeasingPipelineProperty
  services/
    pipeline.py                — NEW: stage advancement, kill, Property conversion
    screening.py               — NEW: screening criteria evaluation
    brrrr.py                   ✅ existing
    portfolio.py               ✅ existing
  views.py                     — add pipeline views (or split to views/pipeline.py)
  urls.py                      — add pipeline URL patterns

templates/
  base.html                    — update nav (four sections + submenus)
  pipeline/
    pipeline_list.html         — NEW: kanban/list of all PipelineProperty
    pipeline_detail.html       — NEW: single property full view
    pipeline_add.html          — NEW: add property to pipeline form
    screening_settings.html    — NEW: configure ScreeningCriteria
    offer_form.html            — NEW: create/edit OfferRecord
    dd_checklist.html          — NEW: DueDiligenceChecklist
    closing_form.html          — NEW: ClosingRecord
    renovation_form.html       — NEW: RenovationRecord
  leasing/
    leasing_list.html          — NEW: active leasing pipeline
    leasing_detail.html        — NEW: single leasing property
    leasing_add.html           — NEW: add to leasing pipeline

migrations/
  XXXX_pipeline_models.py      — NEW: all pipeline models in one migration
                                  (or split — paruff decides)
```

---

## 3. PipelineProperty — Implementation Detail

### 3.1 Model constants (top of models.py additions)

```python
class PipelineProperty(models.Model):

    class Stage(models.TextChoices):
        DISCOVERED     = 'DISCOVERED',     'Discovered'
        SCREENING      = 'SCREENING',      'Screening'
        UNDERWRITING   = 'UNDERWRITING',   'Underwriting'
        OFFER          = 'OFFER',          'Offer Submitted'
        DUE_DILIGENCE  = 'DUE_DILIGENCE',  'Due Diligence'
        CLOSING        = 'CLOSING',        'Closing'
        ACQUIRED       = 'ACQUIRED',       'Acquired'
        RENOVATION     = 'RENOVATION',     'Renovation'
        STABILIZED     = 'STABILIZED',     'Stabilized'

    class Status(models.TextChoices):
        ACTIVE   = 'ACTIVE',   'Active'
        KILLED   = 'KILLED',   'Killed'
        ON_HOLD  = 'ON_HOLD',  'On Hold'
        ACQUIRED = 'ACQUIRED', 'Acquired'

    class SourceType(models.TextChoices):
        VRM        = 'vrm',         'VRM Property'
        FORECLOSURE= 'foreclosure', 'Foreclosure Property'
        LISTING    = 'listing',     'Listing'
        MANUAL     = 'manual',      'Manually Added'
        HUD        = 'hud',         'HUD Home'
        USDA       = 'usda',        'USDA Property'
        FANNIE     = 'fannie',      'Fannie Mae'
        FREDDIE    = 'freddie',     'Freddie Mac'
        COUNTY     = 'county',      'County Sale'
        BANK_REO   = 'bank_reo',    'Bank REO'
```

### 3.2 Stage advancement rules

Stage order is linear. A property can only advance to the next stage
or be killed/held at any stage. It cannot skip stages.

```python
STAGE_ORDER = [
    Stage.DISCOVERED,
    Stage.SCREENING,
    Stage.UNDERWRITING,
    Stage.OFFER,
    Stage.DUE_DILIGENCE,
    Stage.CLOSING,
    Stage.ACQUIRED,
    Stage.RENOVATION,
    Stage.STABILIZED,
]
```

Implemented in `core/services/pipeline.py`:

```python
def advance_stage(pipeline_property: PipelineProperty) -> PipelineProperty:
    """Advance property to next stage. Records timestamp. Returns updated instance."""

def kill_property(pipeline_property: PipelineProperty,
                  reason: str) -> PipelineProperty:
    """Kill property at current stage. Records kill_stage and kill_reason."""

def hold_property(pipeline_property: PipelineProperty,
                  reason: str = '') -> PipelineProperty:
    """Place property on hold."""

def convert_to_property_record(pipeline_property: PipelineProperty,
                                closing_record: ClosingRecord) -> Property:
    """At acquisition: create Property record from pipeline data.
    Sets PipelineProperty.property_record FK.
    Called by closing_record save logic in service, not model."""
```

### 3.3 Adding a VrmProperty to pipeline (one-click flow)

The "Add to Pipeline" button on the VRM list view:
1. POSTs to `/pipeline/add-from-source/` with `source_type=vrm&source_id=<pk>`
2. View calls `core/services/pipeline.create_from_vrm(vrm_property, user)`
3. Service denormalizes address fields from VrmProperty → PipelineProperty
4. Service immediately runs screening via `core/services/screening.screen_property()`
5. Sets `screening_passed`, `screening_score`, `screening_notes`
6. Sets stage to SCREENING (even if passed — user confirms advancement)
7. Redirects to `/pipeline/<pk>/` detail view

This means screening is automatic on add — user sees results immediately
without a separate action.

### 3.4 Source record resolution

To display source data on the pipeline detail view without N+1 queries:

```python
def get_source_record(pipeline_property: PipelineProperty):
    """Resolve source_type + source_id to the actual source model instance."""
    if pipeline_property.source_type == 'vrm':
        return VrmProperty.objects.filter(
            pk=pipeline_property.source_id).first()
    elif pipeline_property.source_type == 'foreclosure':
        return ForeclosureProperty.objects.filter(
            pk=pipeline_property.source_id).first()
    elif pipeline_property.source_type == 'listing':
        return Listing.objects.filter(
            pk=pipeline_property.source_id).first()
    return None
```

---

## 4. Screening Service — Implementation Detail

File: `core/services/screening.py`

### 4.1 ScreeningResult (not a model — an in-memory result)

```python
from dataclasses import dataclass

@dataclass
class ScreeningResult:
    passed: bool
    score: Decimal          # 0-100
    hard_failures: list     # criteria that caused immediate fail
    soft_failures: list     # criteria that reduced score but did not kill
    passes: list            # criteria that passed
    notes: str              # human-readable summary
```

### 4.2 Screening logic flow

```python
def screen_property(pipeline_property: PipelineProperty,
                    criteria: ScreeningCriteria,
                    source_record=None) -> ScreeningResult:
    """
    Evaluate pipeline property against user's screening criteria.

    Hard failures return immediately (fast kill).
    Soft failures reduce score but do not kill.
    Missing data on source record = criterion skipped, noted.

    No external API calls. Uses only data already on the source record.
    """
```

### 4.3 Criterion evaluation order (hard kills first)

1. **State filter** (hard) — if allowed_states set and state not in list → KILL
2. **Property type** (hard) — if allowed_property_types set and type not in list → KILL
3. **Price range** (hard) — if price outside min/max → KILL
4. **Foreclosure status** (hard) — if status not in allowed → KILL
5. **GACS score** (soft) — if market gacs_score below threshold → score penalty
6. **Gross yield** (soft) — computed from price + rent estimate if available
7. **Price-to-rent ratio** (soft) — if above max → score penalty
8. **Year built** (soft) — if older than max_year_built → score penalty
9. **Beds** (soft) — if outside min/max → score penalty

Score starts at 100. Each soft failure deducts points proportionally.
Hard failures short-circuit — no score computed.

### 4.4 Getting rent estimate for screening

VrmProperty has `projected_monthly_rent` field — use this.
ForeclosureProperty does NOT have a rent field — skip yield-based criteria.
This is documented in ScreeningResult.notes so user knows why yield was skipped.

### 4.5 Default ScreeningCriteria values

```python
# Applied when user has not configured criteria yet
DEFAULT_CRITERIA = {
    'allowed_states': ['TX', 'FL', 'GA', 'NC', 'AZ',
                       'OH', 'IN', 'AL', 'SC'],  # landlord-friendly
    'max_price': None,          # no default — user must set
    'min_gross_yield_pct': None,# no default — user must set
    'max_price_to_rent_ratio': None,
    'min_beds': 2,
    'allowed_property_types': ['single-family', 'duplex',
                                'triplex', 'fourplex'],
}
```

Note: I am not confident of research-validated defaults for yield thresholds.
Leave max_price, min_gross_yield_pct, and max_price_to_rent_ratio as None
(no default) — user must configure these for their market before screening
produces meaningful results.

---

## 5. Pipeline Service — convert_to_property_record Detail

When a ClosingRecord is created, the service:

```python
def convert_to_property_record(pipeline_property, closing_record) -> Property:
    """
    Creates a Property record from pipeline + closing data.
    Does NOT call save() on pipeline_property directly —
    caller is responsible for the full transaction.
    """
    property = Property(
        user=pipeline_property.user,
        address=pipeline_property.address,
        city=pipeline_property.city,
        state=pipeline_property.state,
        zip_code=pipeline_property.zip_code,
        purchase_price=closing_record.final_purchase_price,
        purchase_date=closing_record.closing_date,
        # All other Property fields left at defaults
        # User completes them in Portfolio edit view
    )
    property.save()
    pipeline_property.property_record = property
    pipeline_property.status = PipelineProperty.Status.ACQUIRED
    pipeline_property.stage = PipelineProperty.Stage.ACQUIRED
    pipeline_property.acquired_at = timezone.now()
    pipeline_property.save(update_fields=[
        'property_record', 'status', 'stage', 'acquired_at'
    ])
    return property
```

All of this in a `transaction.atomic()` block.

---

## 6. Views Design

### 6.1 Pipeline list view (`/pipeline/`)

Queryset: `PipelineProperty.objects.filter(user=request.user)`

Display options:
- **List view** (default): sorted by updated_at desc, grouped by stage
- **Kanban view** (stretch goal — post-alpha): columns by stage

Context includes counts per stage so user sees funnel shape:
```
Discovered (12) | Screening (8) | Underwriting (3) | Offer (1) | ...
```

Filter sidebar:
- Status (Active / Killed / On Hold)
- Stage
- State
- Source type

### 6.2 Pipeline detail view (`/pipeline/<pk>/`)

Shows:
- Source record data (address, price, beds, baths, status)
- Current stage + status
- Screening result (passed/failed, score, notes)
- Stage history (timestamps for each stage reached)
- Offer records (if any)
- DD checklist (if any)
- Closing record (if any)
- Renovation record (if any)
- Action buttons: Advance Stage | Kill | Hold | Add Offer | Add DD | Close Deal

### 6.3 Screening settings view (`/pipeline/screening/settings/`)

Form for ScreeningCriteria. Uses user's existing UserInvestmentTargets
as reference but stores separately (different concerns).

Shows current defaults and what each criterion does.
Includes explanation: "Properties added to your pipeline are automatically
screened against these criteria."

### 6.4 Leasing pipeline list view (`/leasing/`)

Shows all LeasingPipelineProperty records for user.
Grouped by stage. Shows days-since-listed for LISTING stage
(helps user see how long a unit has been vacant).

---

## 7. Navigation Implementation

### 7.1 base.html nav structure

```html
<nav>
  <div class="nav-group">
    <a href="/growth/">Growth Areas</a>
    <div class="nav-submenu">
      <a href="/growth-explorer/">Market Explorer</a>
      <a href="/growth/">Target Markets</a>
    </div>
  </div>

  <div class="nav-group">
    <a href="/pipeline/">Purchase Pipeline</a>
    <div class="nav-submenu">
      <a href="/pipeline/">My Pipeline</a>
      <a href="/pipeline/add/">Add Property</a>
      <a href="/pipeline/screening/settings/">Screening Criteria</a>
      <a href="/vrm/">VRM Foreclosures</a>
      <a href="/foreclosures/">All Foreclosures</a>
    </div>
  </div>

  <div class="nav-group">
    <a href="/portfolio/">Portfolio</a>
    <div class="nav-submenu">
      <a href="/portfolio/">Dashboard</a>
      <a href="/portfolio/add/">Add Property</a>
      <a href="/brrrr/">BRRRR Calculator</a>
    </div>
  </div>

  <div class="nav-group">
    <a href="/leasing/">Leasing Pipeline</a>
    <div class="nav-submenu">
      <a href="/leasing/">Active Listings</a>
      <a href="/leasing/add/">Add Listing</a>
    </div>
  </div>
</nav>
```

**CSS rules:**
- No Bootstrap classes
- No inline style= on layout elements
- No !important
- Use existing CSS custom properties (tokens.css) for colors
- Submenu uses CSS-only hover show/hide or minimal JS toggle
- Active state uses a CSS class driven by current URL, not hardcoded

### 7.2 URLs to verify before implementation

These existing URL names must be confirmed in core/urls.py before
nav links are written — do not assume URL names:
- VRM list view URL name
- ForeclosureProperty list view URL name
- Portfolio dashboard URL name
- BRRRR calculator URL name
- Growth areas URL names

Agent must grep core/urls.py for actual URL names before writing
any `{% url %}` tags in base.html. Do not invent URL names.

---

## 8. Pipeline Kanban / List — Visual Design

### Stage funnel display (list view header)

```
┌──────────┬──────────┬──────────────┬───────┬──────────────┐
│Discovered│ Screening│ Underwriting │ Offer │ Due Diligence│ ...
│    12    │    8     │      3       │   1   │      1       │
└──────────┴──────────┴──────────────┴───────┴──────────────┘
```

Clicking a stage header filters the list to that stage.

### Property card in list

```
[Source badge: VRM]  123 Main St, Austin TX 78701
$245,000 | 3bd/2ba | 1,450 sqft
Screening: ✓ PASSED (82/100)  |  Added: 3 days ago
[Advance →]  [Kill ✗]  [Details]
```

### Kill confirmation

Killing a property requires a reason (short text or dropdown of common
reasons). This data becomes valuable over time — user can see patterns
in why they kill deals.

Common kill reasons (suggested defaults, user can type custom):
- Price too high
- Rent estimate too low
- Poor condition
- Bad market / low GACS
- Financing fell through
- Lost to other buyer
- Failed inspection
- Title issues

---

## 9. Risk Items

1. **Migration scope** — seven new models in one migration is high risk.
   Consider splitting into two migrations: (a) PipelineProperty + ScreeningCriteria,
   (b) remaining models. Both need paruff approval before running.

2. **URL name assumptions** — agent must grep core/urls.py before writing
   any nav template tags. Wrong URL names cause NoReverseMatch at runtime.

3. **VrmProperty → PipelineProperty denormalization** — when VRM data
   is re-scraped and a property's address or price changes, the
   PipelineProperty denormalized fields become stale. Acceptable for alpha;
   document in KNOWN_LIMITATIONS.md.

4. **Screening with missing rent data** — ForeclosureProperty has no
   projected_monthly_rent field. Yield-based screening criteria will be
   skipped for all ForeclosureProperty records. User must be informed
   of this clearly in the UI.

5. **convert_to_property_record partial data** — the created Property record
   will have minimal fields (address, price, date). User must complete
   the record in Portfolio. UI must make this obvious — show a
   "Complete your property record" prompt on the Portfolio dashboard
   for newly acquired properties with incomplete data.

6. **Leasing pipeline scope** — this is intentionally minimal (not full
   tenant management). If user expects rent collection, maintenance
   tracking, or lease renewal automation, that is Phase 3 and must
   be communicated clearly in the UI.

---

## 10. Sequencing (do in this order)

```
PIPE-0:  Update nav in base.html (verify URL names first)
         ← unblocks user orientation immediately
    │
PIPE-1:  PipelineProperty + ScreeningCriteria models + migration A
         ← human approval required before running
    │
PIPE-2:  core/services/screening.py
PIPE-3:  core/services/pipeline.py (advance, kill, hold)
    │
PIPE-4:  Pipeline list + detail views + templates
PIPE-5:  "Add to Pipeline" button on VRM list view
PIPE-6:  Screening settings view
    │
PIPE-7:  OfferRecord + DueDiligenceChecklist + ClosingRecord
         + RenovationRecord models + migration B
         ← human approval required before running
    │
PIPE-8:  Offer, DD, Closing, Renovation forms + views
PIPE-9:  convert_to_property_record service + closing view integration
    │
PIPE-10: LeasingPipelineProperty model + migration C
         ← human approval required before running
PIPE-11: Leasing pipeline views + templates
    │
PIPE-12: KNOWN_LIMITATIONS.md updates
PIPE-13: Tests for all new services and views
```

**Do not run any migration without paruff review.**
**Do not write nav template tags before grepping core/urls.py.**
**Do not write screening logic before PIPE-1 migration is approved and run.**
