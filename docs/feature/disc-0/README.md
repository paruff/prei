# docs/feature/disc-0

## Overview
Archived DISC-0 record: source data models for discovery sources (HudProperty, UsdaProperty, CountyForeclosureNotice). No scrapers, pipeline integration or UI in scope.

## Interface
- spec.md, design.md, tasks.json: requirements, model designs, task list.
- DISC-0_migration.py: reference copy of `core/migrations/0033_disc_0_source_models.py` (depends on `0032_activate_fannie_mae_source`). Not applied from here.

## Invariants
- Currency fields are Decimal.
- Models follow the VrmProperty / ForeclosureProperty patterns.

## Side Effects
- None; documentation and a reference migration only.

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)
