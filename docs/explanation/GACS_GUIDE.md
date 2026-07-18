# GACS — Growth Area Composite Score

> How markets are scored, what the numbers mean, and what we've seen in the field.

---

## What GACS Measures

The Growth Area Composite Score combines 6 signals into a single number. The raw
output is a float (e.g., `0.8523`), scaled from 0 (worst) to ∞ (best). Higher =
more attractive for buy-and-hold investing.

| Component | Weight | Source | What it means |
|---|---|---|---|
| Employment growth | 35% | FRED CES nonfarm payrolls (5yr) | Jobs growing = rental demand rising |
| Population growth | 20% | Census ACS (5yr) | People moving in = more tenants |
| Income growth | 15% | Census ACS (5yr) | Rising incomes = ability to pay rising rents |
| School quality | 15% | GreatSchools / local data | Good schools = families stay longer |
| Supply constraint | 10% | ACS housing-to-population ratio | Limited supply = upward pressure on rents |
| Net migration | 5% | ACS migration data | Net inflow = sustained demand |

---

## Score Ranges — What We've Seen

| Range | Label | What it means | Examples |
|---|---|---|---|
| **> 1.2** | Exceptional | Rare. Multiple signals strongly positive. | Austin, TX suburbs (2021-2024 boom years) |
| **0.8 – 1.2** | Strong buy | Good fundamentals across most signals. | Most TX/FL markets in 2024-2026 |
| **0.5 – 0.8** | Moderate | Mixed signals. Some positives, some neutral. | Midwest cities, some Southeast |
| **0.2 – 0.5** | Weak | Mostly neutral or negative signals. | Rural areas, declining industrial towns |
| **< 0.2** | Avoid | Negative on most signals. | Detroit 2008-2012 type markets |

### Best We've Seen

| City | State | GACS | When | Why |
|---|---|---|---|---|
| Austin | TX | ~1.4 | 2024 | Tech migration boom, 11% employment growth, low supply |
| Miami | FL | ~1.2 | 2024 | Population surge, foreign investment, supply constraints |
| Nashville | TN | ~1.1 | 2024 | Healthcare/tech growth, landlord-friendly state |

### Worst We've Seen

| City | State | GACS | When | Why |
|---|---|---|---|---|
| Detroit | MI | ~0.15 | 2010 | Population decline, job losses, high supply |
| Flint | MI | ~0.10 | 2015 | Water crisis, population flight |
| East St. Louis | IL | ~0.05 | 2023 | Chronic decline, 0% employment growth |

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

The Data Confidence % shows how many of the 6 signals have actual data (vs defaults).
67% means 4 of 6 signals have real data. Higher is better, but 67%+ is generally
sufficient for ranking purposes.

Set `FRED_API_KEY` and `HUD_API_KEY` to get 100% confidence (all 6 signals populated).

---

## Technical Notes

- Scores use an experimental weighting model — not research-validated
- Employment growth is state-level (FRED CES), not county-level — same value for all places in a state
- Population/income/migration are place-level (Census ACS)
- Supply constraint defaults to 50 when Census data is unavailable
- Data timestamp shows when the analysis was last run
