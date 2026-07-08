# Specification: DISC-2 — USDA REO Ingestion (data.gov feed)

## Problem Statement

The Discovery page lists USDA Foreclosures as a planned source, and the
UsdaProperty model exists from DISC-0 to store fetched property records.
However, no ingestion pipeline exists to fetch, parse, and persist USDA
Rural Development REO property data into UsdaProperty.

The U.S. Department of Agriculture publishes a Rural Development Resale
Properties feed via data.gov (fixed-width TXT format, not JSON). This
increment builds the management command to ingest that feed.

## Scope — In This Increment

| In scope | Out of scope |
|---|---|
| `ingest_usda_reo` management command | Scheduler/cron setup |
| UsdaProperty model extension (REMOVED status) | Web UI for ingestion |
| Fixed-width TXT parser for USDA data.gov feed | Real-time auction date integration |
| Unit tests with fixture data | HTML web scraper for properties.sc.egov.usda.gov |
| `--dry-run` flag | Data enrichment |

## Dependencies

- DISC-0 (UsdaProperty model) — must be approved and migration applied
- DISC-HG-2 — data.gov USDA feed URL and schema confirmed

## Human Gates

| ID | Gate | Reason |
|---|---|---|
| DISC-HG-2 | USDA feed URL and schema confirmed | The data.gov TXT file (2018 vintage) may be replaced by a modern API; confirm current endpoint before production |

## Acceptance Criteria

| # | Criterion | test_type |
|---|---|---|
| AC1 | `ingest_usda_reo` fetches from USDA data.gov TXT endpoint | unit |
| AC2 | Records are upserted into UsdaProperty using usda_case_number as unique key | unit |
| AC3 | Running twice does not create duplicate UsdaProperty records | unit |
| AC4 | Records missing from latest fetch are marked `status='removed'`, not deleted | unit |
| AC5 | Fixed-width TXT parser extracts correct fields from each line | unit |
| AC6 | Command logs count of added, updated, removed records | unit |
| AC7 | `--dry-run` flag uses fixture data, no real HTTP calls | unit |
