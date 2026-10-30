# Rent coverage: Dallas, TX (county FIPS 48113)

Properties measured: 2 (VrmProperty rows for the market)

| Source | Properties with a rent | Notes |
|---|---|---|
| VRM projected rent | 2/2 (100%) | stored on the row at scrape time |
| HUD FMR | 2/2 (100%) | FY2026; 2 at ZIP level (Small Area FMR), rest metro level; 40th percentile floor |
| Rentcast | not measured | 75201: 403 billing/subscription-inactive; 75204: 403 billing/subscription-inactive |
| Rentometer | not measured | no adapter in the codebase |
| Any source (VRM or HUD) | 2/2 (100%) | NFR-1 target: 90% |

## HUD FMR vs Rentcast

| ZIP | Beds | HUD FMR | Level | Rentcast median | HUD below Rentcast |
|---|---|---|---|---|---|
| 75201 | 3 | 3650 | 75201 | n/a | n/a |
| 75204 | 3 | 3490 | 75204 | n/a | n/a |

No paired samples (see the Rentcast row above).

## Findings (2026-10-30)

- **HUD FMR works for Dallas and is ZIP-level.** Dallas is a HUD Small Area FMR market: the FY2026 response carries 261 rows, one per ZIP plus a metro row (3BR metro $2,431; 3BR 75201 $3,650, 75204 $3,490). So the "county-level floor is too coarse" worry does not hold for this market. It may for markets HUD publishes only at metro or county level.
- **The existing HUD client breaks on Small Area markets.** `FMRClient.get_county_data` assumes `basicdata` is a dict; for Dallas it is a list, so `fetch_fmr_data` raises `AttributeError`. It also looks up by 5-digit FIPS (HTTP 400); HUD wants the entity id (`4811399999`). `scripts/rent_coverage.py` works around both; the client needs its own fix (a G1.3-style row).
- **Rentcast is not measured.** The key is valid but its API subscription is inactive (`403 billing/subscription-inactive`). Activate the free Developer plan at https://app.rentcast.io/app/api, then re-run. The per-address estimate endpoint 404s on the fixture rows (fake addresses), so the script compares against Rentcast ZIP market statistics instead; the response shape (`rentalData.detailedByBedrooms`) is taken from Rentcast's docs and is unverified until the subscription is active.
- The seeded market holds two fixture VRM rows; VRM coverage of 100% is trivially small. Their projected rents are placeholders and are not compared with HUD.

## Fee (Rentcast, third-party listing, verify on the pricing page)

| Plan | Monthly | Included requests | Overage |
|---|---|---|---|
| Developer | $0 | 50 | $0.20 |
| Foundation | $74 | 1,000 | $0.06 |
| Growth | $199 | 5,000 | $0.03 |

[Rentcast billing and pricing](https://developers.rentcast.io/reference/billing-and-pricing) confirms the plan structure and the 50-request free tier; tier prices come from a third-party listing. `core/integrations/market/rents.py` assumes 100 calls a day on the free tier (`RENTCAST_DAILY_BUDGET`); that looks wrong and should be fixed in L1.

## Recommendation on FR-1 (Rentcast adapter)

**Still undecided; the HUD-vs-Rentcast gap is the number that decides it, and it needs the Rentcast subscription.** What is known: HUD FMR covers 100% of the seeded Dallas properties at ZIP level for $0, and is a 40th-percentile floor by definition, so it understates market rent. Rentcast would cost $0 to $74 a month. Decision rule: build L1 if HUD sits more than ~15% below Rentcast at the median, or if HUD plus VRM covers under 90% of properties in a market without Small Area FMR; otherwise defer FR-1. The 15% threshold is a proposal for the human to confirm.
