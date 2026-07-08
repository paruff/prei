# Specification: DISC-1 — HUD REO Ingestion (data.gov feed)

## Problem Statement

The Discovery page lists HUD Homestore as a planned source, and the
HudProperty model exists from DISC-0 to store fetched property records.
However, no ingestion pipeline exists to fetch, parse, and persist HUD
REO property data into HudProperty.

The U.S. Department of Housing and Urban Development publishes a
Real Estate Owned (REO) properties feed via data.gov. This increment
builds the management command to ingest that feed.

## Scope — In This Increment

| In scope | Out of scope |
|---|---|
| `ingest_hud_reo` management command | Scheduler/cron setup |
| HudProperty model extensions (asking_price, insured_status, REMOVED status) | Web UI for ingestion |
| Unit tests with mock HTTP responses | Live data.gov feed calls (dry-run only) |
| BDD scenario coverage | Admin integration |
| `--dry-run` flag | Data enrichment/enrichment |

## Dependencies

- DISC-0 (HudProperty model) — must be approved and migration applied

## Human Gates

| ID | Gate | Reason |
|---|---|---|
| DISC-HG-1 | Confirm data.gov HUD REO JSON endpoint URL | URL may change; confirm before production use |

## Acceptance Criteria

| # | Criterion | test_type |
|---|---|---|
| AC1 | `ingest_hud_reo` fetches from data.gov HUD REO JSON endpoint | unit |
| AC2 | Records are upserted into HudProperty using hud_case_number as unique key | unit |
| AC3 | Running twice does not create duplicate HudProperty records | unit |
| AC4 | Records missing from latest fetch are marked `status='removed'`, not deleted | unit |
| AC5 | `asking_price` field stores Decimal, not float | unit |
| AC6 | `insured_status` only accepts defined choices (fha_insured, conventional, uninsured, va) | unit |
| AC7 | Command logs count of added, updated, removed records | unit |
| AC8 | `--dry-run` flag performs all logic without network calls or DB writes | unit |
