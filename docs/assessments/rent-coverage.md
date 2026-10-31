# Rent coverage: Dallas, TX (county FIPS 48113)

Properties measured: 2 (VrmProperty rows for the market)

| Source | Properties with a rent | Notes |
|---|---|---|
| VRM projected rent | 2/2 (100%) | stored on the row at scrape time |
| HUD FMR | 2/2 (100%) | via the screening rent chain (hud_fmr_rent); 40th percentile floor |
| Rentcast (ZIP market stats) | 2/2 (100%) | median rent by bedrooms |
| Rentometer | not measured | no adapter in the codebase |
| Any source (VRM or HUD) | 2/2 (100%) | NFR-1 target: 90% |

## HUD FMR vs Rentcast

| ZIP | Beds | HUD FMR | Via | Rentcast median | HUD below Rentcast |
|---|---|---|---|---|---|
| 75201 | 3 | 3650 | screening | 5067 | 28.0% |
| 75204 | 3 | 3490 | screening | 3900 | 10.5% |

Paired ZIPs: 2. HUD below Rentcast by median 19.2%, range 10.5% to 28.0%.

## Findings (2026-10-30)

- **HUD FMR works for Dallas and is ZIP-level.** Dallas is a HUD Small Area FMR market: the FY2026 response carries 261 rows, one per ZIP plus a metro row (3BR metro $2,431; 3BR 75201 $3,650, 75204 $3,490).
- **HUD sits 10.5% to 28.0% below Rentcast's ZIP median** (median gap 19.2%, 2 ZIPs). Some of that is by design: FMR is the 40th percentile, so it should sit below a median. The Rentcast figure is the median across all property types for that bedroom count (75201 is downtown, heavy on apartments and condos), not single-family houses, so it overstates what a house screens against. Two ZIPs is a thin sample.
- **Fee for that gap:** $0 on the Developer plan (50 requests a month). One ZIP lookup costs one request.
- **Fixed (G1.8):** the screening HUD step now passes the county FIPS (from the market's GrowthArea), and the client maps it to the entity id and picks the ZIP row. The HUD row above is measured through `hud_fmr_rent`, the screening rent chain's HUD step, not raw HUD calls. Limit: New England county-subdivision entity ids are not supported.
- The seeded market holds two fixture VRM rows; VRM coverage of 100% is trivially small and its placeholder rents are not compared.

## Fee (Rentcast, third-party listing, verify on the pricing page)

| Plan | Monthly | Included requests | Overage |
|---|---|---|---|
| Developer | $0 | 50 | $0.20 |
| Foundation | $74 | 1,000 | $0.06 |
| Growth | $199 | 5,000 | $0.03 |

[Rentcast billing and pricing](https://developers.rentcast.io/reference/billing-and-pricing) confirms the plan structure and the 50-request free tier; tier prices come from a third-party listing. `core/integrations/market/rents.py` assumes 100 calls a day on the free tier (`RENTCAST_DAILY_BUDGET`); that looks wrong and should be fixed in L1.

## Recommendation on FR-1 (Rentcast adapter)

**Build L1, as an optional adapter behind the key, with HUD FMR (ZIP-level) as the fallback.** The measured gap (median 19.2%) crosses the 15% rule this report proposed, and the fee is $0 at investor-screening volumes. Confidence is moderate, not high: two ZIPs, an all-property-types Rentcast median, and a floor-vs-median comparison. Before L1 is built, L1 should compare Rentcast's per-address estimate (not ZIP stats) against HUD on 10 or more real single-family listings across several ZIPs. The 15% threshold was a proposal and is for the human to confirm.
