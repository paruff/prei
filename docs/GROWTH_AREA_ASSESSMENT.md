# Growth Area — Top-Tier Assessment

> A candid and comprehensive assessment from the perspective of a top
> 0.1% real-estate investor managing institutional portfolios across
> multiple markets and asset classes.

---

## What Works (Solid Foundation)

### 1. Data Source Selection is Correct
You picked the right primary APIs — **Census ACS** for demographic trends and
**FRED** for economic indicators. These are the same sources institutional
investors use. The auto-detection of ACS vintages from `/data.json` is a
nice touch that avoids hardcoded years.

### 2. Composite Scoring Has Logic Behind It
The 5-factor weighted score (pop 0.20, emp 0.35, income 0.20, housing 0.10,
supply 0.15) is defensible. Employment gets the highest weight (0.35), which
is correct — jobs drive everything else. Supply constraint (0.15) shows you
understand the difference between a growing market and a profitable one.

### 3. The Pipeline Bridge Shows Architectural Vision
Connecting "where to invest" (Growth Explorer) to "what to buy" (Discovery
Pipeline) is the right architecture. Most tools do one or the other, not
both. The VRM foreclosure source and CSV file source show you're thinking
about actual deal flow, not just market rankings.

### 4. Test Coverage is Unusual for a Solo Project
332 pipeline tests + BDD acceptance tests + CI coverage gate. Most
individual developers ship features without tests. This is production-grade
discipline.

---

## What's Missing (The Blind Spots)

### 1. No Rental Market Data — Your Biggest Gap

Population growth tells you people are moving there. It does **not** tell you
whether those people are renters, whether rents are rising, or whether the
rent-to-price ratio supports cash flow.

**What top investors track:**
- Year-over-year rent growth by metro (Zillow Observed Rent Index, CoStar,
  or Census median gross rent)
- Rent-to-income ratios
- Vacancy rates by submarket
- Concession rates (new construction giving 2 months free = soft market)

**You have:** population growth, income growth, housing demand index (a
proxy built from vacancy + population).
**You're missing:** actual rent trend data. The housing demand index is
clever but it's derived, not observed.

**Fix priority:** P0. Without rent data, you can't distinguish between
"Austin: 40% population growth, rents flat because overbuilding" and
"Miami: 15% population growth, rents up 18% because supply is constrained."

### 2. Employment is State-Level — Useless for City-Level Decisions

Knowing Texas employment grew 4.5% tells you nothing about whether that
growth was in Austin (tech), Midland (oil), or McAllen (retail). The
BLS QCEW (Quarterly Census of Employment and Wages) publishes **county-level**
employment data. FRED carries some of it.

**Fix:** `{STATE}{COUNTY}URN` or BLS QCEW county-level series. Even metro-level
would be a massive upgrade.

### 3. No Cash-Flow Modeling on Top of Growth

A 10% population growth rate in a market where median homes cost $800k and
cap rates are 3% is **not** a good investment. A 2% growth rate in a market
with $150k homes at 10% cap rates **is**.

**What the scoring should include:**
- Typical cap rate for the market
- Median home price
- Price-to-rent ratio
- Cash-on-cash at median price/rent for that market

**You have:** the underwriting solver computes these, but it's not wired into
the growth scoring. The pipeline bridge was step 1 — now connect the
underwriting output back to the growth score.

### 4. No Historical Validation

You rank cities by composite score. Has anyone checked whether last year's
top-ranked cities actually performed? A top investor wants to know:

- "The top 5 cities from 2019 — what's their actual appreciation since?"
- "How many deals killed in screening were actually good deals?"
- "What's the false-positive rate of the screening thresholds?"

This is a **feedback loop** problem. The data exists to validate — you just
need to build the reporting.

### 5. No Market Comparison Within a State

The Growth Explorer shows 10 cities ranked by score. But it doesn't show:

- How does Dallas compare to Houston on cap rates?
- Which of the 5 Texas cities in the top 10 has the lowest entry price?
- What's the spread in gross yield between Austin and San Antonio?

A side-by-side comparison mode with 3-5 key metrics (not just the composite
score) would let investors make relative decisions, not just absolute ones.

### 6. Regulatory / Landlord-Friendliness Not in the Score

You recently added landlord-friendliness as a badge. Good start. But it
should be **in the composite score**, not just displayed as a badge.

A 9/10 growth score in California means nothing if it takes 90 days to
evict a non-paying tenant. The landlord score should be a weight in the
composite, not just a visual indicator.

### 7. No Property-Level Deal Flow from the Market

The pipeline bridge connects to VRM foreclosures. That's one source. A top
investor wants:

- **MLS active listings** with days-on-market filtering
- **Off-market/wholesale** feeds (investor networks, batchleads, propstream)
- **Pre-foreclosure** notices (NOD filings from county records — which you
  have the county source stubs for, but not implemented)
- **New construction** permits — indicates future supply competition
- **Tax delinquencies** — leading indicator of distress sales

**You have the architecture** (DiscoverySource ABC, registry) but only VRM
has real data flowing. The other sources return empty lists.

---

## What Top Investors Actually Do (Benchmark)

When a top 0.1% investor evaluates a market, they look at:

```
Market Score = (Demand Drivers × 0.40)
             + (Supply Constraints × 0.30)
             + (Regulatory Environment × 0.15)
             + (Exit Liquidity × 0.15)
```

**Demand Drivers (0.40):**
- Job growth by industry (not just total — tech jobs pay more, create more
  rental demand)
- Population growth with **in-migration breakdown** (are people moving from
  high-cost areas bringing equity?)
- Household formation rate (young adults forming new households = more
  rental demand)
- Corporate relocation announcements (Oracle moving to Nashville = thousands
  of high-income renters)

**Supply Constraints (0.30):**
- Building permits / housing starts vs population growth (you have this
  partially)
- Land availability (geographic constraints — Miami can't sprawl west)
- Entitlement timeline (how long to get a building permit — 6 months in
  Houston vs 3 years in San Francisco)
- Construction cost trends (materials + labor inflation)

**Regulatory Environment (0.15):**
- Eviction timeline (you have this data now)
- Rent control (yes/no/statewide preemption)
- Short-term rental restrictions
- Property tax burden (effective rate, not just nominal)

**Exit Liquidity (0.15):**
- Institutional buyer presence (are Blackstone/Invitation Homes active?)
- Days on market for recent sales
- Price-to-income ratio (can local buyers afford to buy from you?)
- iBuyer penetration (Opendoor, Offerpad — provides floor pricing)

**Your tool covers maybe 40% of this.** The demand drivers are partially
covered. Supply constraints are partially covered. Regulatory is a badge,
not a score factor. Exit liquidity is not addressed at all.

---

## Concrete Priority List

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 🔴 P0 | Wire underwriting output back into growth score | Medium | High |
| 🔴 P0 | Add actual rent growth data (Zillow/Census median gross rent) | Medium | High |
| 🔴 P0 | Make landlord score a weight in composite, not just a badge | Small | Medium |
| 🟡 P1 | Add county-level employment (BLS QCEW via FRED or direct) | Large | High |
| 🟡 P1 | Build market comparison mode (side-by-side cities) | Medium | Medium |
| 🟡 P1 | Implement at least one more real data source (county NOD feed) | Large | Medium |
| 🟢 P2 | Historical validation dashboard (did past predictions work?) | Medium | Medium |
| 🟢 P2 | Property-level metrics (median cap rate, price, PTR per market) | Medium | Medium |
| 🟢 P2 | Exit liquidity indicators (DOM, institutional presence) | Large | Medium |

---

## Overall Verdict

**Score: 6/10** — Solid architecture, correct data foundations, good test
discipline. The tool is better than 90% of what individual investors use
(which is usually Zillow + a spreadsheet).

But it's not yet at the level of institutional-grade market analysis. The
gap isn't in the code quality — it's in the **data breadth** and **feedback
loops**. You have the skeleton of an excellent tool. The next 6 months
should be about adding the 3-5 data sources that turn it from "good for a
solo developer" into "something a professional investor would pay for."
