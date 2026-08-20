# Audit: Growth Areas + Discovery Pipeline — Data Flow, UI/UX, Gap Analysis

> **Date:** 2026-07-08
> **Goal:** Find the right place to invest → gather property data → screen → find better deals

## 1. Architecture: Two Worlds That Don't Talk

The app has two major subsystems that should form a single pipeline:

```
┌─────────────────────────────────────────────────────┐
│  Growth Area Explorer (Django views)                 │
│  growth_explorer / growth_areas                      │
│  ────────────────────────────────────                │
│  Answers: WHERE to invest?                           │
│  Data: Census ACS + FRED → GrowthArea model          │
│  Output: Ranked list of cities by composite score    │
│  UI: State picker → loading overlay → results table  │
└─────────────────────────────────────────────────────┘
              │
              │  ⚠️  NO BRIDGE EXISTS
              │     User clicks "View Foreclosures" → VRM listing page
              │     No pipeline connection at all
              ↓
┌─────────────────────────────────────────────────────┐
│  Pipeline Engine (prei/pipeline/)                    │
│  discovery → screening → underwriting → offer        │
│  ────────────────────────────────────                │
│  Answers: WHAT properties are good deals?            │
│  Data: Raw listings → DiscoverySanitizer → Pipeline  │
│  Output: Scored properties at each pipeline stage    │
│  UI: None — API/CLI only                            │
└─────────────────────────────────────────────────────┘
```

**Critical gap:** The Growth Area Explorer tells you *where* to invest (e.g., "Dallas scored 92/100"). But there is **no mechanism** to then pipe Dallas properties through the discovery pipeline for deal-level analysis. The "View Foreclosures" link on the Growth Explorer results table takes you to a raw VRM listing page — bypassing the pipeline entirely.

---

## 2. Data Flow Audit

### 2.1 Growth Area → Pipeline (the missing bridge)

| What should happen | What actually happens | Gap |
|---|---|---|
| Select promising area → fetch properties in that area via discovery sources | Click "View Foreclosures" → go to VRM listings page (no pipeline processing) | **Critical** |
| Properties from fannie_mae, hud, county sources discovered for selected state/city | No discovery sources are wired to the growth explorer at all | **Critical** |
| Discovered properties auto-screened against investor thresholds | User manually browses VRM listings with no filtering | **High** |
| Screening results show passing/failing counts per area | No screening results shown anywhere | **High** |

### 2.2 Existing VRM Foreclosure Page

The `vrm_properties_list` view shows raw foreclosure data from VRM — not pipeline-processed. It has:
- ✅ Paginated list with filters (state, vendee eligible)
- ✅ Property detail pages
- ✅ BRRRR calculator integration
- ❌ No screening/filtering by yield, PTR, beds, baths
- ❌ No discovery pipeline integration
- ❌ No "Advanced to pipeline" button

### 2.3 Data Source Coverage

| Source | Exists? | Wired to Growth? | Wired to Pipeline? | Notes |
|---|---|---|---|---|
| Census ACS | ✅ | ✅ | ❌ | Growth metrics work well |
| FRED employment | ✅ | ✅ | ❌ | State-level only |
| Fannie Mae | ✅ (stub) | ❌ | ❌ | Placeholder; needs scraper |
| HUD Homestore | ✅ (stub) | ❌ | ❌ | Placeholder; needs scraper |
| VA Foreclosures | ✅ (stub) | ❌ | ❌ | Placeholder; needs scraper |
| USDA Foreclosures | ✅ (stub) | ❌ | ❌ | Placeholder; needs scraper |
| County records | ✅ (stub) | ❌ | ❌ | 50+ counties listed; needs per-county scrapers |
| VRM Foreclosures | ✅ | ❌ | ❌ | Raw data; no pipeline processing |

---

## 3. UI/UX Audit

### 3.1 Growth Area Explorer (growth_explorer.html)

| Element | Status | Notes |
|---|---|---|
| State picker | ✅ | Clean dropdown |
| API key detection | ✅ | FRED optional; Census required |
| Loading overlay | ✅ | 5-stage progress with elapsed timer |
| Results table | 🟡 | Shows 10 cities ranked by composite score |
| "View Foreclosures" link | 🟡 | Links to VRM — should link to pipeline |
| No "Analyze Properties" button | ❌ **Missing** | User can't trigger pipeline from here |
| No screening threshold config | ❌ **Missing** | Default 7% yield / 15× PTR hardcoded |
| Design compliance | ✅ | Bootstrap removed; uses project tokens |

### 3.2 Growth Areas (growth_areas.html)

| Element | Status | Notes |
|---|---|---|
| Paginated results | ✅ | 25 per page with navigation |
| CSV export | ✅ | Full data export |
| "Analyze New State" button | ✅ | Opens growth_explorer |
| No pipeline integration | ❌ **Missing** | Can't drill into a city's properties |

### 3.3 Discovery Pipeline UI

| Element | Status | Notes |
|---|---|---|
| Any UI at all | ❌ **Missing** | Pipeline is API/CLI only |
| Dashboard showing pipeline stages | ❌ **Missing** | StateAggregator exists but no UI |
| Property detail in pipeline | ❌ **Missing** | No way to view a pipeline-tracked property |
| Screening results table | ❌ **Missing** | BatchScreeningProcessor has analytics but no display |

---

## 4. Blind Spots (What You're Missing)

### 4.1 The "Right Place to Invest" Problem

| Blind Spot | Impact | Fix |
|---|---|---|
| Only 10 places per state | Small cities with fast growth are excluded | Increase to 20; add metro area option |
| Population growth is 5-year only | May miss recent acceleration | Add 1-year ACS option |
| Employment is state-level only | Misses city-level job markets (Austin vs El Paso) | Use county-level BLS QCEW data |
| No rental market data | Can't distinguish investor demand from population growth | Add Zillow/Redfin rental data or Census gross rent |
| No inventory data | Supply-constraint index uses housing units, not active listings | Pull active listing count from MLS/Redfin API |

### 4.2 The "Gather Property Data" Problem

| Blind Spot | Impact | Fix |
|---|---|---|
| Discovery sources are all stubs | Zero properties discovered from external sources | Implement at least 1 real scraper (county records preferred) |
| No geographic bridge | Growth Explorer finds areas but can't query properties there | Wire discovered areas into discovery source `state=` + `county=` params |
| No batch ingestion UI | Can't manually upload a CSV/JSON file of properties | Add upload page using DiscoveryProcessor |
| VRM data bypasses pipeline | "View Foreclosures" shows raw data | Route VRM properties through DiscoverySanitizer first |

### 4.3 The "Find Better Deals" Problem

| Blind Spot | Impact | Fix |
|---|---|---|
| Screening thresholds not configurable by user | Can't adjust yield threshold per market | Add user settings for screening config |
| No deal comparison | Can't compare 2 properties side-by-side | Pipeline detail view with comparison |
| Underwriting results not surfaced | NOI/cap/MAO computed but never shown | Add pipeline dashboard |
| Offer strategy not exposed | Offer handler exists (API only) | Add offer recommendation to property view |
| No historical tracking | Can't see which deals advanced vs killed over time | Add pipeline timeline view |

---

## 5. Concrete Next Steps (Prioritized)

### 🔴 P0 — Build the bridge (Growth Area → Pipeline)
1. Add a "Discover Properties" button on the growth explorer results table
2. When clicked: pipe the selected state/city to `discover_from_all()` and `DiscoveryProcessor.process_batch()`
3. Show a screening results summary: "350 properties discovered, 120 passed screening"

### 🔴 P0 — Implement one real data source
4. Pick the most accessible county with a JSON API/CSV feed and implement the scraper
5. Alternatively: add a CSV/JSON file upload page for manual property ingestion

### 🟡 P1 — Pipeline dashboard
6. A `/pipeline/` page showing `StateAggregator.summary()` — pipeline stage distribution
7. A "Screening Results" table showing which properties passed/failed and why

### 🟡 P1 — Configurable screening
8. User can set their own `min_gross_yield` and `max_price_to_rent_ratio`
9. Saved per user as `UserScreeningPreferences` model

### 🟢 P2 — Underwriting visibility
10. Show NOI, cap rate, MAO on property detail after underwriting
11. Offer recommendation based on strategy

### 🟢 P2 — VRM → Pipeline integration
12. Route VRM properties through `DiscoverySanitizer` before display
13. Add "Run Pipeline" action on VRM property detail page

---

## 6. Test Coverage Summary

| Layer | Pipeline | Growth/Django |
|-------|----------|---------------|
| Unit | 332 tests | 41 tests (growth_metrics) |
| Integration | 42 tests | ~2 tests (growth_areas_integration) |
| E2E | 11 tests | 0 |
| BDD/Acceptance | 0 | 1 feature (property_analysis) |
| **Total** | **385** | **44** |
