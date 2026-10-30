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
- **Rentcast**: no `RENTCAST_API_KEY` in `.env`. The free tier (100 calls/day) is enough for a 25-property sample.
- **Rentometer**: no adapter exists; out of scope until the other two are measured.
- The seeded Dallas market holds two fixture VRM rows. VRM coverage of 100% is real but trivially small; run on a market seeded from live VRM data for a meaningful NFR-1 number.

## Recommendation on FR-1 (Rentcast adapter)

**Undecided; do not build L1 yet.** Nothing here shows HUD FMR is too coarse, and nothing shows it is adequate. Once both credentials are set, run `make docker-rent-report` against a live-seeded market and decide with this rule: if HUD FMR sits more than ~15% below Rentcast at the median, or HUD plus VRM covers under 90% of properties, build L1 (Rentcast adapter); otherwise defer FR-1. The 15% threshold is a proposal for the human to confirm.
