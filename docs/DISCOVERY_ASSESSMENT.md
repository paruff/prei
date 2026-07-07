# Property Discovery — Top-Tier Assessment

> A candid evaluation of the discovery pipeline from the perspective of a
> top 0.1% investor who processes thousands of properties per week across
> multiple acquisition channels.

---

## What They'd Notice First

### The Dedup Engine is the Best Part

The `DiscoverySanitizer.clean_address()` → SHA-256 hash → dedup against
`existing_hashes` flow is exactly what production-grade systems do. A top
investor getting the same property from 3 different wholesalers, MLS, and a
county foreclosure feed **must** deduplicate. Your implementation handles:

- Punctuation stripping (`Apt.`, `#`, commas)
- Case normalization
- Whitespace collapsing
- Hash-based O(1) lookup

This is **correct**. The hash-as-primary-key pattern is how Zillow, Redfin,
and MLS systems deduplicate listings internally. They just use more
sophisticated normalization (geocoding + parcel number matching).

**NIT:** The regex `[^\w\s]` strips hyphens without inserting spaces. `"Suite-A"` becomes `"suitea"` while `"Suite A"` becomes `"suite a"`. A top
system would normalize hyphenated words to their spaced equivalents. Minor
edge case, but it means "123 Main St Suite-A" and "123 Main St Suite A"
don't match. In production, you'd add a pre-pass that replaces hyphens with
spaces before the strip pass.

---

## What Works Well

### 1. Multi-Source Architecture is Correct

The `DiscoverySource` ABC + registry pattern is exactly right. Each source
(fannie_mae, hud, va, usda, county, vrm) implements the same interface and
plug into the same pipeline. A top investor's technology stack has the same
shape — just with more sources and real data.

**What they have that you don't:**
- A dedicated data engineering team maintaining each scraper
- Automated retry with exponential backoff and circuit breakers
- Alerting when a source stops returning data
- A "source health" dashboard showing last successful fetch per source

### 2. Batch Processing with ThreadPoolExecutor is Pragmatic

Using `ThreadPoolExecutor` with configurable workers for parallel API calls
is the right approach for this scale (hundreds to low thousands of
properties). A top investor's system would use async I/O (asyncio/httpx) for
thousands of concurrent requests, but ThreadPool is perfectly adequate for
the current scale.

### 3. Type Coercion is Thoughtfully Done

The `CanonicalPropertyPayload` field validators handle the mess that real
property data throws at you:
- `"$350,000"` → `350000.0`
- `"3.0"` → `3` (beds)
- `None` → `None` (optional fields)
- `"N/A"` → `0.0` (non-numeric price)

This is the kind of defensive code that prevents production incidents. A top
investor's data pipeline has hundreds of these validators — you've built the
right pattern.

### 4. The Pipeline Orchestrator Shows Systems Thinking

Chaining `DiscoverySanitizer` → `DiscoveryProcessor` → screening →
underwriting in a single `PipelineOrchestrator.run()` call is the right
abstraction. It means the operator (or a future scheduler) only needs to
call one function per property. The `PipelineResult` with `.to_dict()` makes
it API-friendly.

---

## What's Missing (The Blind Spots)

### 1. No Geocoding — This is a Major Gap

A top 0.1% investor doesn't deduplicate on normalized address strings
alone. They use **geocoding** (lat/lng → parcel boundary) and **parcel
number matching**. Here's why:

```
Scenario A:
  "123 Main St, Austin, TX 78701" (MLS listing)
  "123 Main Street, Austin, TX 78701-1234" (county NOD)
  "123 MAIN ST AUSTIN TX" (wholesaler spreadsheet)

  Your SHA-256 approach: ✓ These all normalize to the same hash.
                          Dedup works.

Scenario B:
  "123 Main St, Austin, TX 78701" (MLS listing)
  "Lot 4 Block 7, Main Street Subdivision" (county legal description)

  Your SHA-256 approach: ✗ Completely different strings = different hashes.
                          Duplicate not detected.

Scenario C:
  "123 Main St, Austin, TX 78701" (single-family home)
  "123 Main St, Unit A, Austin, TX 78701" (duplex — same address, different
                                           unit, same parcel)

  Your SHA-256 approach: ✗ Different strings = different hashes. But it's
                          the same property from an investor's perspective.
```

**Fix:** Add optional geocoding (Google Maps API, Census Geocoder, or local
libpostal) to resolve addresses to coordinates + parcel numbers. Use parcel
number as a second dedup key.

**Current risk:** You'll miss deduping properties that use legal
descriptions instead of street addresses (common in county data).

### 2. Data Sources Return Empty — The Pipeline is Starving

This is the most practical problem. You have 7 registered sources. Only VRM
has real data flowing. The other 6 return `[]`.

| Source | Status | What it needs |
|--------|--------|---------------|
| Fannie Mae | Live HTTP call, returns empty | Their API might require different params or is geo-restricted |
| HUD Homestore | Live HTTP call, returns empty | Authentication or different endpoint |
| VA Foreclosures | Live HTTP call, returns empty | Same |
| USDA | Live HTTP call, returns empty | Same |
| Texas counties | CSV parsing works | Manual CSV downloads from county sites |
| VRM Foreclosures | ✅ Works | Already populated from VRM scraper |

A top investor's system has **at least one high-volume source** fully
operational — usually MLS (via an IDX feed or API), county records (via a
subscription service like CoreLogic or Black Knight), or a foreclosure
aggregator (RealtyTrac, ATTOM).

**Fix:** Choose ONE high-volume source and make it work end-to-end. The VRM
source is working but likely has limited data. Consider:
- A property data API subscription (ATTOM, CoreLogic, Estated)
- An MLS IDX feed (requires real estate license in most states)
- Manual CSV imports from county websites (already supported via CsvFileSource)

### 3. No Data Freshness Tracking

The `DiscoveryProcessor` processes a batch and returns counts. But there's
no concept of:

- "When was this batch last processed?"
- "How many new properties since last week?"
- "Source X returned 0 properties — is it broken or is there nothing new?"

A top investor's system has freshness monitoring per source. If Fannie Mae
returns 0 properties for 3 consecutive days when it normally returns 50,
someone gets paged.

### 4. No Enrichment Step After Discovery

The pipeline flow is:

```
raw → clean → dedup → screen → underwrite → offer
```

What's missing between dedup and screen is **enrichment**:

- **Comparable sales** — What did similar properties sell for recently?
- **Rental comps** — What's the market rent for this bed/bath/neighborhood?
- **Tax assessment** — What's the assessed value and tax rate?
- **Neighborhood metrics** — Crime, school rating, walk score
- **Flood zone / climate risk** — Is this property in a flood zone?

The screening step evaluates based on `estimated_monthly_rent` and
`purchase_price` from the raw source data. But if the source doesn't have
rent data (county foreclosure notices almost never do), the screening is
comparing against `None`.

**Fix:** Add an enrichment step that fills in missing data from secondary
sources. Even a simple Zillow/Redfin scrape for rent estimates would
dramatically improve screening accuracy for county-sourced properties.

### 5. No Quality Scoring on Source Data

Not all sources are equally reliable. A $350,000 list price from MLS is more
trustworthy than a $350,000 "estimated value" from a county assessor (which
might use a 3-year-old assessment).

A top investor's system assigns a **confidence score** to each data point
based on its source. The screening evaluator could use this to flag
properties where key metrics come from low-confidence sources.

### 6. Screening Throws Away the Baby with the Bathwater

The `BatchScreeningProcessor` kills properties that fail screening. The
violation reason is recorded, but the property is moved to KILLED and never
re-evaluated.

In reality, a top investor doesn't permanently kill properties. They:

1. **Watchlist** properties that almost pass (e.g., yield is 6.8% vs 7%
   target). If the price drops or rent estimate increases, re-evaluate.
2. **Flag for manual review** — "Failed screening, but in a top growth
   market. Worth a second look?"
3. **Re-evaluate on data refresh** — A new rent comp or price reduction
   could change the result.

Your current design makes KILLED terminal (no transitions out). This is
correct for the state machine but creates a dead-end for borderline deals.

**Fix:** Add a `WATCHLIST` stage between SCREENING and KILLED for properties
that fail by a small margin (e.g., 10% below threshold). Add a periodic
re-evaluation job that rechecks watchlisted properties when new data arrives.

### 7. No Bulk Pricing / Portfolio Discount Logic

The underwriting solver computes MAO for a single property. A top investor
buying 10 properties from the same seller expects a portfolio discount. The
pipeline has no concept of:

- "These 5 properties are from the same wholesaler — negotiate a bundle
  price"
- "This property is in the same ZIP as 3 we already own — management
  efficiencies reduce our OpEx by 5%"
- "We already own 8 properties in this county — concentration risk
  threshold reached"

---

## What a Top Investor's Pipeline Actually Looks Like

```
Sources (50+)           Enrichment           Scoring             Decisions
───────────────         ───────────          ──────────          ─────────
MLS IDX ──────┐         ┌─ Zillow API ──┐    ┌─ Screening    ──→ Pass/Watch/Kill
County API ───┤         │               │    │                  (configurable
ATTOM/Core ───┤         ├─ Tax Assessor ─┤    ├─ Underwriting ──→ MAO + IRR
Wholesaler ───┤         │               │    │                  (with debt models)
FSBO scrape ──┤─ Dedup ─┼─ Rent comps ───┼────┤
RSS feeds ────┤  (3-    │               │    ├─ Offer strategy ─→ conservative/
Bank REO ─────┤  way    ├─ Flood zone ───┤    │                    target/aggressive
Auction cal ──┤  match) │               │    │
Tax delinq ───┘         └─ Crime data ───┘    └─ Portfolio fit  ──→ adds or skips
                                                                    based on existing
                                                                    holdings

Monitoring: source health, dedup rate, screening pass rate, offer acceptance
rate, time from discovery → offer, false positive tracking
```

**Your system covers:**
- Sources: 7 registered, 1 with data
- Dedup: 1-way (address hash)
- Enrichment: None
- Scoring: Screen → Underwrite → Offer
- Monitoring: None

**That's about 25% of a production-grade pipeline.** The remaining 75% is
enrichment, monitoring, and source reliability.

---

## Concrete Priority List

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 🔴 P0 | Get ONE high-volume source working end-to-end (VRM or a new one) | Large | Critical |
| 🔴 P0 | Add enrichment step (at minimum: rent estimates for county data) | Medium | High |
| 🔴 P0 | Add geocoding + parcel number dedup (fallback to address hash) | Medium | High |
| 🟡 P1 | WATCHLIST stage for borderline screening failures | Small | Medium |
| 🟡 P1 | Source health monitoring dashboard | Medium | Medium |
| 🟡 P1 | Quality confidence score per source data point | Small | Low |
| 🟢 P2 | Portfolio discount / bundle pricing logic | Medium | Medium |
| 🟢 P2 | Automated re-evaluation of watchlisted properties | Medium | Medium |
| 🟢 P2 | Full debt-service model in underwriting (not just all-cash) | Medium | Medium |

---

## Overall Verdict

**Score: 5/10** — The architecture is correct. The dedup engine is
production-quality. The pipeline chaining (discover → screen → underwrite →
offer) is the right flow.

But the pipeline is **starving for data**. Seven sources are registered, six
return empty. The enrichment layer (the most valuable part of a discovery
system) hasn't been built yet. And the dedup is address-only, which won't
handle the legal descriptions that county data comes with.

**The one thing that would move this from 5 to 7:** Make ONE source work
end-to-end with real data flowing, then add a basic enrichment step (rent
estimates from a free API). A pipeline that actually finds and screens 50
properties per day is infinitely more valuable than one with perfect
architecture that finds zero.
