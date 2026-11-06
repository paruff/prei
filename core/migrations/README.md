# core/migrations

## Overview
Auto-generated Django migrations for the `core` app, `0001_initial` to `0055_create_cache_table`. Do not hand-edit; schema changes need approval (see the `migration-safety` skill). Summarised by schema history, not per file.

## Interface (schema history)
- 0001-0010: base schema, Listing, GrowthArea, ForeclosureProperty, alerts/watchlist/notification preferences, MarketSnapshot (and indicators), SavedSearch, AuditLog, Team/PropertyNote/SharedProperty, InvestmentAnalysis exit fields.
- 0011-0023: VrmProperty (and finance fields), PropertyShare, Property bedrooms/bathrooms, MarketSnapshot fetched_at/DataSource, UserProfile, UserInvestmentTargets, MonthlyActuals, unique-constraint conversion, GrowthArea tweaks.
- 0024-0032: PipelineAsset, UserScreeningPreferences, pipeline v2 and PIPE-7/PIPE-10 migrations, GrowthArea landlord/population scores, PropertySource and discovery models; data seeds for property sources and Fannie Mae activation.
- 0033-0041: DISC-0 source models (HudProperty, UsdaProperty, CountyForeclosureNotice), HUD REO fields, ATTOM source seed, USDA removed status, GrowthArea enhancements, UserProfile onboarding, county FIPS and FMR fields.
- 0042-0055: GrowthArea rent growth, pipeline location fields and indexes, DataSourceHealth, consecutive-errors/version, CapExItem, FinancingScenario (0049 merges the two 0048 branches), MarketIndicator, PipelineProperty expense/underwriting fields, month normalisation, cache table.
- Data migrations (RunPython): 0031, 0032, 0036, 0054.

## Invariants
- Linear history; 0049 is the merge of two 0048 leaves.
- Currency fields are Decimal.

## Side Effects
- Applying them alters the database schema; 0031/0032/0036/0054 modify rows; 0055 creates the DB cache table.

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)
