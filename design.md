# Design: Documentation Improvements for Investor Workflows

**Feature**: Documentation overhaul for Growth Areas, Discovery, Screening, and Underwriting
**Spec**: `specification.md`
**Status**: Draft

---

## Architecture Overview

The documentation will follow the existing `docs/` structure:
- **how-to-guides/** — Step-by-step user workflows (new files for each domain)
- **explanation/** — Conceptual guides (update GACS_GUIDE, add new)
- **reference/** — Technical reference (API keys, data sources, financial KPIs)
- **tutorials/** — End-to-end walkthroughs (getting-started exists, may extend)

---

## Component Design

### 1. Workflow Overview Document (New)

**File**: `docs/explanation/investor-workflow.md`

**Purpose**: Unifying narrative connecting all 4 stages

**Structure**:
```
# The prei Investor Workflow

## Overview
Buy-and-hold investors move through 4 stages:
1. **Growth Areas** — Find high-growth markets
2. **Discovery** — Source properties in those markets
3. **Screening** — Filter properties against your criteria
4. **Underwriting** — Analyze deals financially

## Stage 1: Growth Areas
- What is GACS? → GACS_GUIDE.md
- How to explore → growth_explorer UI
- Data confidence & limitations

## Stage 2: Discovery
- Source types: HUD, USDA, VRM, ATTOM, County
- Running discovery for a growth area
- Results → Screening

## Stage 3: Screening
- Setting criteria (screening_settings)
- Hard kills vs soft scoring
- Review queue & actions

## Stage 4: Underwriting
- Pipeline underwriting (per-property)
- BRRRR calculator (deal-level)
- Metrics: NOI, Cap Rate, CoC, MAO, DSCR

## Navigation Map
[Visual or table showing URL patterns and navigation flow]
```

### 2. Growth Areas Documentation

**Files**:
- **Update**: `docs/explanation/GACS_GUIDE.md` — Enhance with UI context
- **New**: `docs/how-to-guides/analyze-growth-areas.md` — Step-by-step user guide
- **Archive/Replace**: `docs/implementation-summary-growth-areas.md` → Move to `docs/assessments/` or reference

**GACS_GUIDE.md Enhancements**:
- Add UI screenshots references (describe what user sees)
- Link to Growth Explorer how-to
- Clarify "Data Confidence" meaning in UI context
- Add "Common Questions" section

**analyze-growth-areas.md Structure**:
```
# Analyzing Growth Areas

## Prerequisites
- FRED_API_KEY, HUD_API_KEY for full data confidence

## Step 1: Open Growth Explorer
[URL, what user sees: state picker, explanation]

## Step 2: Run Analysis
- Select state
- Click "Analyze"
- Wait for background job

## Step 3: Interpret Results
- Table columns explained (Rank, City, Growth metrics, Composite Score, Confidence)
- Expandable breakdown rows
- Confidence chips (success/warning/danger)
- "Discover Properties" → property_discovery
- "View Screened" → pipeline_screener

## Step 4: Export & Next Steps
- CSV export
- CMA undervalued listings section

## Understanding GACS
[Summary + link to GACS_GUIDE.md]

## Data Sources & Limitations
- Census ACS, FRED, HUD FMR, GreatSchools
- Employment = state-level, not county
- Experimental weights — not research-validated
```

### 3. Discovery Documentation

**File**: `docs/how-to-guides/discover-properties.md`

**Structure**:
```
# Discovering Properties

## Prerequisites
- Growth area analyzed (has GrowthArea record)
- API keys for full source coverage

## Step 1: Choose a Growth Area
- From Growth Areas list → "Discover Properties"
- Or direct: /discovery/?growth_area_id=X

## Step 2: Review Available Sources
[Table matching template: HUD REO, USDA REO, VRM, ATTOM, County]
- Counts per source
- Active checkboxes
- Descriptions

## Step 3: Run Discovery
- Select sources
- Click "Discover Properties in [City]"
- Loading overlay explanation

## Step 4: Review Results
- KPI cards: Discovered, Passed Screening, Failed, Already Existed
- Success/warning messages
- "View in Screener" button

## Source Details
### HUD REO
- Government-owned foreclosures
- Data from HUD API
- No rent estimates → yield/PTR skipped in screening

### USDA REO
- Rural Development foreclosures
- Similar to HUD

### VRM (VA REO)
- VA-owned foreclosures
- Has rent estimates → full screening

### ATTOM Pre-foreclosure
- Notice of Default / Notice of Trustee Sale
- Pre-foreclosure stage

### County Foreclosure Notices
- NTS, Sheriff Sale, Auction records
- County-level data

## Troubleshooting
- "No growth areas yet" → run Growth Explorer first
- Source count = 0 → API key missing or no data for area
- Discovery takes time → background thread, 30s timeout
```

### 4. Screening Documentation

**File**: `docs/how-to-guides/screen-properties.md`

**Structure**:
```
# Screening Properties

## Prerequisites
- Properties in pipeline (from discovery or manual add)
- Screening criteria configured

## Step 1: Set Screening Criteria
- Navigate: /pipeline/screening-settings/
- Hard criteria (immediate kill):
  - Allowed states
  - Allowed property types
  - Price range (min/max)
  - Allowed foreclosure statuses
- Soft criteria (score deduction):
  - Min GACS score
  - Min gross yield %
  - Max price-to-rent ratio
  - Max year built
  - Min/max beds

## Step 2: Run Screening
- Screener: /pipeline/screener/
- Filter by growth area
- "Re-Screen All" button
- Or individual properties screened on add

## Step 3: Review Results
- KPI summary: Total, Passed, Failed, Not Screened
- Filter: Passed Only / Failed Only / All
- Table columns: Address, Source, Price, Beds, Sqft, Est. Rent, Screening, Actions

## Understanding Screening Logic

### Hard Kill Criteria (any failure = killed)
1. State filter
2. Property type filter
3. Price range
4. Foreclosure status

### Soft Criteria (deduct from 100, kill if < 50)
5. **GACS Score** — Looks up GrowthArea by state+city; proportional deduction up to 20 pts
6. **Gross Yield** — (monthly_rent × 12) / price; needs rent data (VRM only); up to 15 pts
7. **Price-to-Rent Ratio** — price / monthly_rent; needs rent data; up to 10 pts
8. **Year Built** — Fixed 5 pts if older than cutoff
9. **Beds** — 5 pts per bed outside range, max 10 pts

### Rent Data Availability
- **VRM Properties**: Have projected_monthly_rent → full screening
- **HUD/USDA/County/ATTOM**: No rent data → yield & PTR skipped
- **Fallback**: HUD FMR lookup by ZIP (if available)

### Score Interpretation
- 100 = perfect match
- ≥ 50 = passed (soft failures but acceptable)
- < 50 = failed (too many/soft failures)
- 0 = hard kill

## Actions
- **→ Underwriting** (passed only) — advances to underwriting stage
- **Kill** — removes with reason
- **Re-Screen All** — re-runs with current criteria

## Common Questions
- Why was my property killed? Check kill reason
- Why is yield skipped? No rent data for this source type
- Can I adjust weights? Not currently — fixed deduction maxes
```

### 5. Underwriting Documentation

**File**: `docs/how-to-guides/underwrite-deals.md`

**Structure**:
```
# Underwriting Deals

## Two Underwriting Tools

### 1. Pipeline Underwriting (per-property)
**When**: After screening passes, click "→ Underwriting" in screener
**Where**: /pipeline/underwriting/<pk>/ (or similar flow)
**Input**: Property data + user assumptions
**Output**: NOI, Cap Rate, Cash-on-Cash, MAO

### 2. BRRRR Calculator (deal-level)
**When**: Quick deal analysis, standalone
**Where**: /brrrr-calculator/
**Input**: Purchase, Rehab, ARV, Rent, Refi terms, Expenses
**Output**: Total cost, Loan, Cash left, NOI, DSCR, CoC, Verdict

---

## Pipeline Underwriting

### Inputs (from property + user)
- Purchase price (from pipeline)
- Estimated rent (from VRM or HUD FMR fallback)
- Property tax (annual)
- Insurance (annual)
- Vacancy rate (default 5%)
- Rehab budget
- Maintenance reserve rate (default 10% of GPR)
- Management fee rate (default 8% of EGI)
- HOA annual

### Metrics Computed
1. **Gross Potential Rent (GPR)** = rent × 12
2. **Effective Gross Income (EGI)** = GPR × (1 - vacancy)
3. **Operating Expenses** = Tax + Insurance + (GPR × maint%) + (EGI × mgmt%) + HOA
4. **Net Operating Income (NOI)** = EGI - OpEx
5. **Cap Rate** = NOI / Purchase Price
6. **Cash-on-Cash** = NOI / (Price + Rehab) — all-cash baseline
7. **Max Allowable Offer (MAO)** = NOI / Target Cap Rate

### Target Cap Rate
- User sets minimum acceptable cap rate (e.g., 8%)
- MAO backsolves: max price to hit target cap rate

### Interpretation
- Cap Rate ≥ target = good buy
- Cash-on-Cash = unlevered return
- MAO = max price you should offer

---

## BRRRR Calculator

### Inputs
- Purchase Price
- Rehab Cost
- ARV (After-Repair Value) — **required**
- Monthly Rent (post-rehab)
- Refi LTV (default 75%)
- Refi Interest Rate
- Closing Costs %
- Annual Operating Expenses

### Outputs & Verdicts
- **Total Project Cost** = Purchase + Rehab + Closing
- **Max Refi Loan** = ARV × LTV
- **Cash Left in Deal** = Total Cost - Max Loan
  - ≤ $0 → **Full Cycle** (all capital recycled)
  - 1-25% of project cost → **Partial Recycle**
  - > 25% → **Capital Trap** (renegotiate)
- **Cash Out at Refi** = Max Loan - Purchase (if positive)
- **Monthly Mortgage** (30-yr amortization)
- **Post-Refi NOI** = (Rent × 12) - Expenses
- **DSCR** = NOI / Annual Debt Service (≥ 1.25 for lender qualification)
- **Post-Refi CoC** = Annual Cash Flow / Cash Left

### DSCR Warning
- Banner warns if DSCR < 1.25 — lender may not qualify refi

---

## Key Differences

| Aspect | Pipeline Underwriting | BRRRR Calculator |
|--------|----------------------|------------------|
| Context | Property in pipeline | Standalone deal analysis |
| Rent Source | Property data (VRM/FMR) | Manual input |
| Rehab | Optional field | Required input |
| Refinance | Not modeled | Full refi modeling |
| Target | Cap rate threshold | DSCR + cash recycle |
| Best For | Buy-and-hold evaluation | BRRRR strategy deals |
```

### 6. UX/UI Documentation

**File**: `docs/reference/ui-patterns.md`

**Structure**:
```
# UI Patterns Reference

## Design System
- CSS Custom Properties (tokens.css)
- Base styles (base.html)
- Component classes

## Page Layout
- `.page-header` with title, subtitle, nav-right actions
- `.kpi-grid` — 4-column metric cards
- `.card` — bordered content blocks
- `.table-wrap` + `.data-table` — responsive tables
- `.filter-bar` — inline form controls
- `.form-grid-2` — 2-column form layout
- `.form-actions` — button groups
- `.message` — success/warning/danger/info

## Data Table Patterns
- Sortable headers (links with sort/order params)
- Chips for status: `.chip-success`, `.chip-warning`, `.chip-danger`, `.chip-default`
- Truncated text with tooltip
- Hidden detail rows (expandable)

## Form Patterns
- `.form-group` with label + input
- `.form-hint` for helper text
- `.card-selectable` for checkbox cards
- Checkbox styling
- Select dropdowns

## Navigation
- Breadcrumbs via page-sub text
- Back links in nav-right
- Deep linking with query params (growth_area_id, passed, status)

## Loading States
- `.kanban-modal-overlay` + `.kanban-hidden`
- Inline loading messages

## Empty States
- `.empty-state` with icon, title, body, CTA

## Accessibility
- Semantic HTML: <table>, <form>, <button>, <a>
- ARIA: role="status" on empty states
- Focus visible on all interactive elements
- Color not sole indicator (chips have text + color)
```

---

## Data Flow Documentation

### User Journey: Growth Areas → Discovery → Screening → Underwriting

```
Growth Explorer (/growth-explorer/)
    │
    ▼
Growth Areas List (/growth-areas/)
    │  (click "Discover Properties" or "View Screened")
    ▼
Property Discovery (/property-discovery/?growth_area_id=X)
    │  (select sources, POST)
    ▼
Pipeline Screener (/pipeline/screener/?growth_area_id=X)
    │  (filter, re-screen, review)
    ▼
Pipeline Detail (/pipeline/<pk>/) → "→ Underwriting"
    │
    ▼
Underwriting Results (metrics display)
    │
    ▼
Offer / Due Diligence / Closing (kanban stages)
```

---

## Cross-Reference Strategy

| From | To | Link Pattern |
|------|-----|--------------|
| Workflow Overview | Each how-to guide | Relative: `../how-to-guides/analyze-growth-areas.md` |
| GACS_GUIDE | Growth Explorer how-to | `../how-to-guides/analyze-growth-areas.md` |
| Discovery guide | Screening guide | `screen-properties.md` |
| Screening guide | Underwriting guide | `underwrite-deals.md` |
| Underwriting guide | BRRRR calc | `/brrrr-calculator/` (URL) |
| All guides | API reference | `../reference/api-keys.md`, `../reference/data-sources.md` |
| All guides | Financial KPIs | `../reference/financial-kpis.md` |

---

## Implementation Notes

### Files to Create
1. `docs/explanation/investor-workflow.md` (new)
2. `docs/how-to-guides/analyze-growth-areas.md` (new)
3. `docs/how-to-guides/discover-properties.md` (new)
4. `docs/how-to-guides/screen-properties.md` (new)
5. `docs/how-to-guides/underwrite-deals.md` (new)
6. `docs/reference/ui-patterns.md` (new)

### Files to Update
1. `docs/explanation/GACS_GUIDE.md` — add UI context, cross-links
2. `docs/index.md` — add links to new guides
3. `docs/README.md` — update navigation
4. `docs/implementation-summary-growth-areas.md` — move to `docs/assessments/` or mark as implementation archive

### Files to Archive
- `docs/implementation-summary-growth-areas.md` → `docs/assessments/implementation-summary-growth-areas.md` (rename/move)

---

## Validation Checklist

- [ ] All documented UI elements exist in templates
- [ ] All URL patterns match `core/urls.py` and view functions
- [ ] All business logic matches service implementations
- [ ] No references to removed/renamed features
- [ ] Cross-references resolve
- [ ] Consistent tone and formatting
- [ ] Accessibility patterns documented
- [ ] Data confidence/warnings prominent
