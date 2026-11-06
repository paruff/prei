# core.models

## Overview
Django ORM models for prei, split by domain and re-exported through `core.models` (`__init__.py` star-imports each module; import order is significant because later modules depend on earlier ones).

## Interface
- `property.py`: `Property`, `RentalIncome`, `OperatingExpense`, `Transaction`, `CapExItem`, `InvestmentAnalysis`, `MonthlyActuals`, `FinancingScenario`.
- `base.py`: `Team`, `TeamMember`, `PropertyNote`, `SharedProperty`, `PropertyShare`, `AuditLog`, `UserProfile`.
- `pipeline.py`: `PipelineAsset`, `PipelineProperty`, `ForeclosureProperty`, `ScreeningCriteria`, `ScreeningCriteriaVersion`, `OfferRecord`, `DueDiligenceChecklist`, `ClosingRecord`, `RenovationRecord`, `LeasingPipelineProperty`, `UserScreeningPreferences`, `UserInvestmentTargets`, `PropertySource`, `DiscoveryRequest`, `DataSourceHealth`.
- `sources.py`: `VrmProperty` (+ `VrmPropertyProfitableManager`), `HudProperty`, `UsdaProperty`, `CountyForeclosureNotice`.
- `growth.py`: `MarketIndicatorType`, `MarketIndicator`, `compute_net_migration`, `Listing`, `MarketSnapshot`, `SavedSearch`, `GrowthArea`.
- `notifications.py`: `UserWatchlist`, `AuctionAlert`, `NotificationPreference`, `Notification`.

## Invariants
- Load order in `__init__.py`: sources, growth, notifications, property, then base and pipeline (which depend on `Property`). Keep new imports consistent with this.
- Uniqueness: `TeamMember` `unique_team_user` (team, user); `CapExItem` (prop, component_type); `MonthlyActuals` (prop, month); `FinancingScenario` (prop, loan_type); `MarketIndicator` (metro_area, indicator_type, date_recorded). Other `UniqueConstraint`s exist in `base.py` (SharedProperty/PropertyShare), `growth.py`, `notifications.py`, `pipeline.py`.
- `VrmProperty` uses explicit `db_table = "vrm_property"` (`sources.py`).
- Project rule: currency uses Decimal fields, never floats; finance math belongs in services/utils, not models.
- Model changes require migrations, which need human approval (AGENTS.md).

## Side Effects
- Models define database schema; changes affect migrations in `core/migrations`.
- Only `compute_net_migration` (`growth.py`) is a plain function; no network calls are made from this package.

## Verification
- Run: `.venv/bin/python -m pytest tests/` (pytest.ini; pass specific paths for speed)
