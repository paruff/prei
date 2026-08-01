# Analyzing Growth Areas

> Find the cities in a state with the strongest buy-and-hold fundamentals using the
> Growth Explorer and the Growth Areas list.

---

## Prerequisites

- A running prei instance with your account (see [Getting Started](../tutorials/getting-started.md)).
- **`CENSUS_API_KEY`** — **required** to run Growth Explorer analysis. Without it the
  explorer shows an error and will not run.
- **`FRED_API_KEY`** — recommended. Without it, employment growth (35% of GACS)
  defaults to 0, lowering every score.
- **`HUD_API_KEY`** — recommended for full data confidence.

Set these in your environment (`.env` locally, env vars on Render) and restart the app.

---

## Step 1: Open the Growth Explorer

Navigate to **Growth Areas → Explore** or browse directly to `/growth-explorer/`.

You'll see:

- A **state picker** (all 50 states + DC)
- A note showing whether `CENSUS_API_KEY` and `FRED_API_KEY` are configured
- If a key is missing, the UI shows a warning before you run anything

## Step 2: Run an Analysis

1. Select a state from the dropdown.
2. Click **Analyze**.

What happens:

- prei fetches the **top 10 places in the state by population** from the Census API.
- For each place it resolves the county, then fetches **county-level employment growth**
  (QCEW) when possible, falling back to a single **state-level FRED** value when county
  data is unavailable. Existing QCEW data is preserved on re-runs.
- For each place, it fetches **population growth**, **income growth**, and a
  **housing demand index** in parallel.
- Each place is saved as a `GrowthArea` record with a composite GACS score.

Analysis is synchronous — the page shows results when it completes, usually in a few
seconds. If a Census key is missing or the API is down, you'll see an error explaining
the likely cause.

## Step 3: Interpret the Results

After analysis, the Growth Explorer shows a ranked table. The **Growth Areas list**
(`/growth/`) shows the same data sorted by composite score, paginated 25 per page.

### Table columns (Growth Areas list)

| Column | What it means |
|---|---|
| City / State | The place analyzed |
| Population | Census population estimate |
| Pop Growth % | 5-year population growth rate |
| Emp Growth % | State-level employment growth (FRED CES) |
| Income Growth % | 5-year median income growth |
| Housing Demand / Supply Constraint | Demand index and supply constraint scores |
| **Composite Score** | GACS — higher is better |
| **Confidence** | % of the 7 GACS signals with real data |

### Confidence chips

- 🟢 **≥ 80%** — most signals have real data
- 🟡 **50–79%** — some defaults used
- 🔴 **< 50%** — many defaults; treat the score as a rough ranking

### Expandable rows

Click a row to expand a breakdown of the underlying signals. Each signal shows its
weight, value, and whether real data was used or a default.

### Actions per row

- **Discover Properties** → opens `/discovery/?growth_area_id=X` to source properties
  in that market (see [Discovering Properties](discover-properties.md)).
- **View Screened** → opens `/pipeline/screener/?growth_area_id=X` to see pipeline
  properties for that market (see [Screening Properties](screen-properties.md)).

## Step 4: Export & Next Steps

- **⬇ CSV** button on the Growth Areas list downloads all growth areas as
  `growth-areas-YYYYMMDD.csv` (State, City, Population, growth rates, Housing Demand,
  Supply Constraint, Composite Score, Data Timestamp).
- Move to the next stage: [Discovering Properties](discover-properties.md) in your
  top-ranked markets.

---

## Understanding GACS

The Growth Area Composite Score combines 7 signals into one number on a 0–100 scale:

| Component | Weight | Source |
|---|---|---|
| Employment growth | 30% | County QCEW (preferred), FRED CES fallback |
| Population growth | 15% | Census ACS |
| Income growth | 15% | Census ACS |
| School quality | 10% | GreatSchools / local |
| Rent growth (FMR YoY) | 15% | County-level HUD FMR |
| Supply constraint | 10% | ACS housing-unit growth |
| Net migration | 5% | Census ACS (proxy) |

Read the full explanation, score ranges, and the Landlord Score in the
[GACS Guide](../explanation/GACS_GUIDE.md).

## Data Sources & Limitations

- **Employment growth** prefers county-level QCEW data and falls back to state-level
  FRED — values can vary within a state depending on data availability.
- **School quality** is resolved via a city→ZIP map covering ~40 major cities; other
  cities get `None` (no penalty, but the signal is missing).
- **Experimental weights** — the GACS model is not research-validated.
- **Missing signals count as 0** toward the score — a market with sparse data scores
  lower than its true fundamentals; check the Confidence %.
- **Supply constraint defaults to 50** when Census data is unavailable.
- Scores rank markets for comparison; they do **not** predict short-term prices or
  account for landlord-friendliness (see the Landlord Score in the GACS Guide).

## Troubleshooting

| Problem | Cause / Fix |
|---|---|
| "CENSUS_API_KEY not configured" | Set the key in your environment and restart. Get a free key at [api.census.gov](https://api.census.gov/data/key_signup.html) |
| "No Census data returned for TX" | Key invalid, or Census API temporarily unavailable — retry later |
| All scores look low | FRED key missing → employment growth is 0; add `FRED_API_KEY` |
| Confidence below 80% | Missing optional API keys; add `HUD_API_KEY` / `FRED_API_KEY` and re-run |
| City not in results | Explorer analyzes the top 10 by population only; larger states omit smaller cities |
