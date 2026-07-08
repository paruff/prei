# Specification: DISC-0 — Source Data Models for Discovery Sources

## Problem Statement

The Discovery page lists HUD Homestore, USDA Foreclosures, and County
Foreclosure Notices as planned sources. Users can submit DiscoveryRequest
records for them, but no data models exist to store fetched property records
from these sources.

Each source has unique identifiers and fields that don't fit neatly into
the existing VrmProperty (VA-specific) or ForeclosureProperty (generic
foreclosure) models. New source-specific models are needed.

## Scope — In This Increment

| In scope | Out of scope |
|---|---|
| `HudProperty` model | Scrapers or ingestion logic |
| `UsdaProperty` model | Pipeline integration (future task) |
| `CountyForeclosureNotice` model | Admin UI or views |
| Generated migration (NOT run — attach for review) | Data seeding |

## Acceptance Criteria

| # | Criterion | test_type |
|---|---|---|
| AC1 | HudProperty model has all required fields (address, hud_case_number, price, beds, baths, sqft, status, URL, timestamps) | unit |
| AC2 | UsdaProperty model has all required fields (address, usda_case_number, price, beds, baths, sqft, status, URL, timestamps) | unit |
| AC3 | CountyForeclosureNotice model has all required fields (case_number, borrower, lender, address, document_type, filing_date, sale_date, county, state) | unit |
| AC4 | Migration file is generated and attached for review (not run) | integration |
| AC5 | All fields use Decimal for currency, never float (AGENTS.md rule 3) | unit |
| AC6 | Each model has a unique identifier field appropriate to its source | unit |
| AC7 | Timestamps (created_at, updated_at) are present on all three models | unit |
