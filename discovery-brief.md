---
date: 2026-07-06
persona: passive-investor
jtbd: "When I am beginning my search for an investment property, I want to identify geographic areas with the strongest growth fundamentals (population, employment, income, housing demand), so I can focus my property search on markets most likely to appreciate and generate positive cash flow."
riskiest_assumption: "We assume that Census ACS 5-year data + BLS employment trends + a simple weighted composite score is sufficient to identify the best residential real estate investment areas. What if the real leading indicators are different (zoning/construction pipelines, school quality, crime trends, job-creation composition, infrastructure investment, supply constraints)? What if the composite_score weighting (0.25 pop, 0.35 emp, 0.25 income, 0.15 housing demand) is arbitrary and misleading?"
acceptance_criterion: "Given the Growth Area Explorer page is loaded with Census and BLS API keys configured, when I select a state and click 'Analyze State', then I see a ranked table of cities within that state sorted by composite growth score, with population growth, employment growth, income growth, and housing demand metrics visible, and the data persists in the GrowthArea table for reuse."
dora_ai_capability: "Cap6: User-centric focus"
dora_core_capability: "N/A — end-user product feature, not DevOps pipeline"
metric: "User-task-completion (can user identify top investment areas and proceed to property search within 3 minutes)"
measurement_source: "Manual observation / session recording"
baseline: "Current: page shows no data (GrowthArea count = 0, MarketSnapshot count = 0). User cannot complete the task at all."
prior_art: "Existing implementation at /growth-explorer/ has the technical plumbing (Census+BLS API calls, model, scoring) but: (1) DB is empty, (2) methodology may need rethinking, (3) no fallback/error UX for API failure"
status: "in-discovery"
---

# Discovery Brief: Growth Area Investment Finder

## Job to Be Done

When I am beginning my search for an investment property, I want to identify geographic areas with the strongest growth fundamentals (population, employment, income, housing demand), so I can focus my property search on markets most likely to appreciate and generate positive cash flow.

## Riskiest Assumption

We assume that Census ACS 5-year data + BLS employment trends + a simple weighted composite score (pop=0.25, emp=0.35, income=0.25, housing=0.15) is sufficient to identify the best residential real estate investment areas.

**Challenges to this assumption:**
1. **The weightings are arbitrary.** There's no empirical or theoretical basis for 0.35 on employment vs 0.25 on population. Are these even the right factors?
2. **Missing factors:** School quality, crime rates, zoning/construction pipeline, job-composition quality (e.g., tech vs retail vs manufacturing), infrastructure investment, property tax trends, landlord-friendliness regulation, climate risk.
3. **Geographic granularity mismatch:** Census "places" are cities, but real estate is hyper-local (neighborhood/zip code). A city like Los Angeles has wildly different sub-markets.
4. **Data timeliness:** ACS 5-year data (2022 vintage) is already 4 years old. BLS has similar lag. Growth trends may have shifted post-COVID.
5. **Correlation ≠ causation:** A city with high population growth doesn't necessarily beat the market for buy-and-hold investors. Supply constraints and price-to-rent ratios matter.

## Acceptance Criterion

Given the Growth Area Explorer page is loaded with Census and BLS API keys configured, when I select a state and click 'Analyze State', then I see a ranked table of cities within that state sorted by composite growth score, with population growth, employment growth, income growth, and housing demand metrics visible, and the data persists in the GrowthArea table for reuse.

## DORA Outcome Target

This feature is end-user facing (not DevOps), so DORA delivery metrics don't directly apply. The relevant DORA AI capability is **Capability 6 (User-centric focus)** — ensuring we solve the real user problem before investing in implementation.

**Success metric:** User can go from blank page to a list of ranked investment areas in < 3 minutes, and click through to browse foreclosures in their top-ranked area.

**Current baseline:** Failure — user sees no data at all (0 records in GrowthArea and MarketSnapshot). The task is impossible.

## Prior Art

### Existing in this repo
| Artifact | Status |
|---|---|
| `GrowthArea` model (core/models.py:643) | ✅ Exists, 0 rows in DB |
| `growth_explorer` view (core/views.py:706) | ✅ POST flow calls Census + BLS APIs |
| `growth_areas` view (core/views.py:679) | ✅ Reads GrowthArea, falls back to MarketSnapshot |
| `growth_explorer.html` template | ✅ Full UI with form, results table, loading state |
| `growth_areas.html` template | ✅ Simpler table (backup) |
| `populate_growth_areas` management command | ✅ Pre-seeds 73 major cities |
| Census/BLS integration code | ✅ `core/integrations/market/census.py`, `bls.py` |
| API endpoint `/api/v1/real-estate/growth-areas` | ✅ Returns growth areas filtered by state |
| Tests | ✅ `test_growth_explorer.py`, `test_growth_areas_integration.py`, `test_api_growth_areas.py` |
| Composite score logic | ✅ `GrowthArea.composite_score` @property (model.py:674) |

### External prior art
- **BiggerPockets** — uses population growth, job growth, rent-to-price ratio, vacancy, landlord-friendly laws, and appreciation history.
- **CBRE / JLL market reports** — use job-creation composition (which sectors), construction pipeline (units under construction vs absorbed), and institutional investment volume.
- **Redfin/Zillow** — use heat maps of price/rent trends, days on market, sale-to-list ratio.
- **ATTOM Data Solutions** — already integrated in this project for property-level data but not leveraged for area-level analysis.

## Key Questions to Resolve in Spec Phase

1. **Growth area vs market snapshot — which is the real source of truth?** DECISION-1 was noted as pending in the Phase 1 spec. GrowthArea is city-level, MarketSnapshot is ZIP-level. The user needs hyper-local data, but GrowthArea has richer growth metrics. Solution: GrowthArea as the analytical engine, then overlay MarketSnapshot ZIP-level rent/price data for granularity.

2. **Is the current scoring methodology valid?** The composite_score uses 4 equally-weighted-ish factors. Should we:
   - Add more factors (school quality, crime, climate risk, regulation)?
   - Use empirically-derived weights?
   - Show multi-dimensional scores instead of a single composite?
   - Let the user adjust weights to their preferences?

3. **What data should prepopulate?** The management command has 73 major cities. Should we expand to more cities, or let the POST-based explorer discover any city in any state?

4. **What's the error UX when APIs fail?** Currently, if Census or BLS API calls fail mid-flight, the user sees a partial or empty result with no clear error message.

5. **How does this flow into the rest of the purchase pipeline?** The discovery → area selection → property search → underwriting pipeline needs to be coherent. Currently, the explorer links to VRM foreclosure browsing, but there's no "save this area to my watchlist" or "compare areas side by side."

## Existing Issues (found by code inspection)

1. **growth_areas.html uses MarketSnapshot fields (zip_code, rent_index, price_trend)** — when MarketSnapshot is empty, this page shows "No market snapshots available." This is the page at `/growth/` (URL), not the main explorer.

2. **growth_explorer view does NOT check if population_growth_rate, employment_growth_rate, or median_income_growth are None before computing composite_score** — if any of these are None, the Decimal math in the `composite_score` property will fail with TypeError (can't multiply None). The tests only exercise the happy path where all values are valid.

3. **ACS_VINTAGE = "2022" is hardcoded** — this is now 4 years old. Needs to be configurable or auto-updating.

4. **The composite_score is a Python @property, not a DB column** — this was flagged in KNOWN_LIMITATIONS.md (LIMIT-04). Sorting happens in Python memory.

5. **`discover_places_in_state` uses place:* wildcard which may time out for large states** — a single API call fetches ALL places, which could be thousands for states like CA or TX, even though only the top 20 are used.

## Recommendations for Spec

1. **Fix the data pipeline first** — run `populate_growth_areas` or investigate why the POST flow doesn't persist data (maybe the Census/BLS API calls are failing silently? The view has no error logging per-place — only "continue" on None).

2. **Validate and harden the scoring** — add None checks in `composite_score`, or handle them in the view before computing.

3. **Investigate what's actually failing** — the Census ACS 2022 vintage API may return errors for certain queries. The API key (provided in .env) may not have the right permissions.

4. **Design the pipeline flow** — wire this area exploration into the full purchase pipeline: area discovery → market deep-dive → property search → underwriting → decision.

5. **Consider user-adjustable scoring weights** — experienced investors have their own criteria; a customizable scorecard could be a differentiator.

## Notes

- The user's exact words: "the current Growth Area Explorer does not seem to get data and/or show the data. I want to explore the best way to find the best area to invest in residential real estate. This is the beginning of the purchase an investment property pipeline."
- This is a methodology question first, a bug-fix second. Don't just fix the code — design the right approach.
- The purchase pipeline from this project's roadmap (specification.md Phase 1) defines: "everything from 'here's a property/market' to 'should I buy it, at what price.'" The Growth Area Explorer is the very first step — "which market should I look at?"
