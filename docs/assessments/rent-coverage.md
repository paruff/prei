# Rent coverage: Dallas, TX (county FIPS 48113)

Properties measured: 2 (VrmProperty rows for the market)

| Source | Properties with a rent | Notes |
|---|---|---|
| VRM projected rent | 2/2 (100%) | stored on the row at scrape time |
| HUD FMR (county, by bedrooms) | 0/2 (0%) | rent floor (40th percentile), not market rent |
| Rentcast | not measured | RENTCAST_API_KEY not set |
| Rentometer | not measured | no adapter in the codebase |
| Any source (VRM or HUD) | 2/2 (100%) | NFR-1 target: 90% |

## HUD FMR vs Rentcast

No paired samples: set RENTCAST_API_KEY and re-run.

## Why HUD and Rentcast are not measured (2026-10-30)

- **HUD FMR**: the configured token is rejected for FMR (`listCounties` and `fmr/data` return nothing). The HUD message says the token was created without the FAIR MARKET RENT dataset selected. A new token with that dataset is needed.
- **Rentcast**: no `RENTCAST_API_KEY` in `.env`. The free tier (50 requests a month) is enough for a 10-property sample.
- **Rentometer**: no adapter exists; out of scope until the other two are measured.
- The seeded Dallas market holds two fixture VRM rows. VRM coverage of 100% is real but trivially small; run on a market seeded from live VRM data for a meaningful NFR-1 number.

## Fee (Rentcast, third-party listing, verify on the pricing page)

| Plan | Monthly | Included requests | Overage |
|---|---|---|---|
| Developer | $0 | 50 | $0.20 |
| Foundation | $74 | 1,000 | $0.06 |
| Growth | $199 | 5,000 | $0.03 |

Source: [Rentcast billing and pricing](https://developers.rentcast.io/reference/billing-and-pricing) confirms the plan structure and the 50-request free tier; the tier prices above come from a third-party listing. `core/integrations/market/rents.py` assumes 100 calls a day on the free tier (`RENTCAST_DAILY_BUDGET`); that looks wrong and should be fixed in L1.

## HUD FMR quality (by definition, not measured here)

HUD FMR is the 40th percentile of gross rents for standard units, set at county or metro level. It is a floor, so it understates market rent by design. `get_rent_estimate` also does not use ZIP-level Small Area FMRs yet.

## Recommendation on FR-1 (Rentcast adapter)

**Build L1, as an optional adapter behind the key, with HUD FMR kept as the fallback.** For a single investor screening a few properties a month, the fee is $0 to $74 a month. A 40th-percentile county floor will bias yield and price-to-rent low for every screen. This is reasoning from fee and HUD's definition, **not a measurement**: the HUD-vs-Rentcast gap (median and range) is still unmeasured because of the credentials above. Once they are set, re-run `make docker-rent-report` and confirm. If HUD FMR turns out to sit within about 15% of Rentcast at the median and HUD plus VRM covers 90% or more, drop L1. The 15% threshold is a proposal for the human to confirm.
