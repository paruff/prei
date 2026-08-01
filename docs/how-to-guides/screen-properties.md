# Screening Properties

> Filter pipeline properties against your buy criteria: hard kills first, then a
> soft-scoring pass that ranks how well each property fits.

---

## Prerequisites

- Properties in your pipeline — either from
  [Discovery](discover-properties.md) or added manually.
- (Optional) screening criteria configured — defaults apply if you haven't touched
  them.

## Step 1: Set Screening Criteria

Navigate to **Pipeline → Screening Settings** (`/pipeline/screening/settings/`).

### Hard criteria (immediate kill on any failure)

| Criteria | What it does |
|---|---|
| **Allowed states** | If set, property state must be in the list |
| **Allowed property types** | If set, property type must be in the list (single-family, duplex, triplex, fourplex) |
| **Price range (min/max)** | If set, purchase price must fall inside |
| **Allowed foreclosure statuses** | If set, the source's foreclosure status must be in the list |

### Soft criteria (deduct from a starting score of 100)

| Criteria | Max deduction |
|---|---|
| **Min GACS score** | Up to 20 pts (proportional to shortfall) |
| **Min gross yield %** | Up to 15 pts (proportional) |
| **Max price-to-rent ratio** | Up to 10 pts (proportional) |
| **Max year built** | Fixed 5 pts if property is older |
| **Min / max beds** | 5 pts per bed outside range, max 10 pts |

When you save, prei re-screens all **active** properties in the DISCOVERED or SCREENING
stages with the new criteria and shows how many were re-screened.

## Step 2: Run Screening

- Open the **Screener** (`/pipeline/screener/`), optionally filtered to a growth area
  (`?growth_area_id=X`).
- Use the filters: price, rent, minimum cap rate, status (ACTIVE / KILLED / ON_HOLD),
  and Passed / Failed / All.
- Sortable columns: price, rent, cap rate, and screening status.
- **Re-Screen All** re-runs screening on **all** of your pipeline properties (not just
  the filtered view) with the current criteria — useful after editing criteria or
  source data.

## Step 3: Review Results

The screener shows:

- **KPI summary** — total properties, passed, failed, not screened.
- **Table columns** — address, source, price, beds, sqft, est. rent, screening result
  (pass/fail + score), and actions.
- **Pass/fail indication** — passed properties can advance; failed properties show the
  score and reasons.

---

## Understanding Screening Logic

### Hard Kill Criteria (any failure = killed, score 0)

1. **State filter** — state not in allowed list
2. **Property type filter** — type not in allowed list
3. **Price range** — price above max or below min
4. **Foreclosure status** — status not in allowed list

A hard-killed property gets **score 0** and records the first hard-failure reason.

### Soft Criteria (deduct from 100, pass if final score ≥ 50)

5. **GACS Score** — looks up the property's `GrowthArea` by state + city; if the
   market's composite score is below your minimum, deducts proportionally (up to 20).
6. **Gross Yield** — `(monthly_rent × 12) / price`; needs rent data; deducts up to 15.
7. **Price-to-Rent Ratio** — `price / monthly_rent`; needs rent data; deducts up to 10.
8. **Year Built** — fixed 5 pts if built before your cutoff.
9. **Beds** — 5 pts per bed outside the range, capped at 10.

### Rent Data Availability

- **VRM properties** carry `projected_monthly_rent` → full screening including yield
  and PTR.
- **HUD, USDA, ATTOM, County** have no rent estimate → yield and PTR are skipped
  (a note is recorded on the result).
- **Fallback:** prei tries a **HUD Fair Market Rent lookup by ZIP** when the property
  has no rent estimate and a ZIP is available; if found, it's cached as the estimated
  rent and screening can proceed.

### Score Interpretation

| Score | Meaning |
|---|---|
| **100** | Perfect match — no soft failures |
| **≥ 50** | Passed — some soft failures but acceptable |
| **< 50** | Failed — too many deductions |
| **0** | Hard kill |

Note: a property passes if it has **no soft failures OR a final score ≥ 50**.

## Actions

| Action | What it does |
|---|---|
| **→ Underwriting** (passed only) | Sets stage to UNDERWRITING and records the timestamp — the property is now in the underwriting stage (see [Underwriting Deals](underwrite-deals.md)) |
| **Kill** | Marks the property KILLED with a reason (defaults to "Failed screening review") |
| **Re-Screen All** | Re-runs screening on all pipeline properties with current criteria |
| **Edit criteria** | Jump to Screening Settings |

---

## Common Questions

### Why was my property killed?
Check the kill reason shown on the property. Hard kills: state / property type /
price / foreclosure status. If it shows a score ≥ 50 but "failed", look at the soft
failure reasons — score is displayed with the deductions.

### Why is yield/PTR skipped for my property?
Your property came from a source without rent data (HUD/USDA/ATTOM/County), and no
HUD FMR fallback was available for its ZIP. Only VRM properties and properties with a
cached rent estimate get full screening.

### Can I adjust the deduction weights?
Not currently. Deduction maximums are fixed (GACS 20, yield 15, PTR 10, year-built 5,
beds 5/bed capped 10). You can only set the criteria thresholds themselves.

### Does screening auto-run when I add a property?
Properties are screened on save where applicable. Changing criteria or clicking
**Re-Screen All** re-runs the whole active pipeline.
