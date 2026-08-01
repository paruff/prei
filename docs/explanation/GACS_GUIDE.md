# GACS — Growth Area Composite Score

> How markets are scored, what the numbers mean, and what we've seen in the field.

> **In the app:** to run a live analysis and see these scores, see
> [Analyzing Growth Areas](../how-to-guides/analyze-growth-areas.md).

---

## What GACS Measures

The Growth Area Composite Score combines 7 signals into a single number. The raw
output is a weighted sum scaled to a **0–100 index** (0 = no growth, 100 = exceptional
across all factors). Higher = more attractive for buy-and-hold investing.

| Component | Weight | Source | What it means |
|---|---|---|---|
| Employment growth | 30% | County-level QCEW (preferred), FRED CES fallback | Jobs growing = rental demand rising |
| Population growth | 15% | Census ACS (5yr) | People moving in = more tenants |
| Income growth | 15% | Census ACS (5yr) | Rising incomes = ability to pay rising rents |
| School quality | 10% | Placeholder (source not wired up) | Good schools = families stay longer |
| Rent growth (FMR YoY) | 15% | County-level HUD FMR year-over-year | Rents rising = income upside |
| Supply constraint | 10% | Default 50 (not currently sourced) | Limited supply = upward pressure on rents |
| Net migration | 5% | ACS migration data (proxy) | Net inflow = sustained demand |

Missing factors are treated as 0 so a partial score is still computable; the score is
only `None` when no weighted factor is available.

> **Note:** these are the GACS v2 weights (confirmed 2026-07-10). Earlier versions of
> this guide described a 6-signal model — the current app uses the 7-signal model above.

---

## Score Ranges — What We've Seen

| Range | Label | What it means | Examples |
|---|---|---|---|
| **> 60** | Exceptional | Rare. Multiple signals strongly positive. | Austin, TX suburbs (2021-2024 boom years) |
| **45 – 60** | Strong buy | Good fundamentals across most signals. | Most TX/FL markets in 2024-2026 |
| **30 – 45** | Moderate | Mixed signals. Some positives, some neutral. | Midwest cities, some Southeast |
| **15 – 30** | Weak | Mostly neutral or negative signals. | Rural areas, declining industrial towns |
| **< 15** | Avoid | Negative on most signals. | Detroit 2008-2012 type markets |

> These are field observations on the 0–100 scale. Actual scores depend on data
> availability — a market with missing signals will score lower than its true
> fundamentals because missing factors count as 0. Use the **Confidence %** to judge
> how much to trust the number.

### Best We've Seen

| City | State | GACS | When | Why |
|---|---|---|---|---|
| Austin | TX | ~70 | 2024 | Tech migration boom, 11% employment growth, low supply |
| Miami | FL | ~60 | 2024 | Population surge, foreign investment, supply constraints |
| Nashville | TN | ~55 | 2024 | Healthcare/tech growth, landlord-friendly state |

### Worst We've Seen

| City | State | GACS | When | Why |
|---|---|---|---|---|
| Detroit | MI | ~8 | 2010 | Population decline, job losses, high supply |
| Flint | MI | ~5 | 2015 | Water crisis, population flight |
| East St. Louis | IL | ~3 | 2023 | Chronic decline, 0% employment growth |

---

## How to Read the Score

### What GACS is good at
- Ranking markets within a state or region
- Identifying emerging markets before prices rise
- Comparing fundamentals across similar-sized cities

### What GACS is NOT good at
- Predicting short-term price movements (< 1 year)
- Accounting for regulatory risk (rent control, eviction moratoriums — those are in the Landlord Score)
- Replacing due diligence — it's a ranking tool, not a crystal ball

### The Landlord Score (0-10)
This is a SEPARATE score shown alongside GACS. It measures:
- Eviction speed (days from filing to removal)
- Rent control laws
- Security deposit caps
- Regulatory burden

| Score | Label | Examples |
|---|---|---|
| 7-10 | Landlord-Friendly | TX (9), FL (8), IN (8), AL (9) |
| 4-6 | Neutral | OH (6), NC (6), VA (5), PA (5) |
| 0-3 | Tenant-Friendly | CA (1), NY (1), OR (2), NJ (1) |

### Using Both Scores Together

```
High GACS + Landlord-Friendly = IDEAL (Austin TX, Tampa FL)
High GACS + Tenant-Friendly = CAUTION (good market, bad landlord laws)
Low GACS + Landlord-Friendly = PASS (cheap but no growth)
Low GACS + Tenant-Friendly = AVOID
```

---

## Data Confidence

The Data Confidence % shows how many of the 7 signals have actual data (vs defaults).
Each real signal earns ~14 points toward confidence; employment is weighted higher
(county-level QCEW = 17, state-level FRED fallback = 8) and metadata signals (FMR year,
landlord score) add ~8 points each. Higher is better, but 60%+ is generally sufficient
for ranking purposes.

Set `FRED_API_KEY` and `HUD_API_KEY` to get higher confidence (more signals populated).

### In the UI

The Growth Areas list and Growth Explorer show confidence as a colored chip next to
each score:

| Chip | Confidence | Meaning |
|---|---|---|
| 🟢 Success | ≥ 80% | Most signals have real data |
| 🟡 Warning | 50–79% | Some defaults used — score is a rough ranking |
| 🔴 Danger | < 50% | Many defaults — treat with caution |

Each expanded row breaks down the individual signals so you can see which one is
missing real data.

---

## Technical Notes

- Scores use an experimental weighting model — not research-validated
- Employment growth prefers **county-level QCEW** data; falls back to state-level FRED CES when county data is unavailable — values can differ within a state
- Rent growth (FMR YoY) is county-level HUD Fair Market Rent year-over-year
- Population/income/migration are place-level (Census ACS); employment is county QCEW
  with a state FRED fallback; supply constraint is always its default (50) today
- Missing factors count as 0 toward the score — a market with sparse data scores lower than its true fundamentals (check Confidence %)
- Data timestamp shows when the analysis was last run

---

## Common Questions

### Why is the GACS score different from what I saw before?
Scores update whenever an analysis is re-run for a state, and data sources (FRED,
Census ACS) refresh over time. Check the **Data Timestamp** on the row to see when the
score was computed.

### Why do cities in my state sometimes share the same employment growth?
Employment growth prefers **county-level QCEW** data, but falls back to **state-level
FRED CES** when county data is unavailable. Cities whose county data is missing will
share the state-level value. This is a known limitation — the score is still useful for
ranking cities on the other signals.

### Can I use GACS to predict house prices?
No. GACS ranks market fundamentals for buy-and-hold screening. It does not predict
short-term prices (< 1 year), and it does not account for regulatory risk — pair it
with the **Landlord Score** (above) for a full market view.

### How does GACS feed into property screening?
When you screen pipeline properties, prei looks up the `GrowthArea` for the property's
state + city. If the property's market GACS is below your configured minimum, points
are deducted from the screening score. See
[Screening Properties](../how-to-guides/screen-properties.md) for details.

### Where do the underlying numbers come from?
Census ACS (population, income, migration), FRED CES (employment, county QCEW preferred),
and HUD FMR (rent growth). School quality and supply constraint are placeholder signals
today (school data is not wired up; supply constraint stays at its default 50).
Configure the related API keys for full data confidence — see
[Data Sources & API Keys](../reference/data-sources.md).

### What does it mean to be in the app's "Growth Areas" list?
Running the Growth Explorer saves each analyzed place as a `GrowthArea` record. The
Growth Areas list (`/growth/`) is that collection, ranked by composite score. Use it
to pick markets for [property discovery](../how-to-guides/discover-properties.md).
