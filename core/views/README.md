# core.views

## Overview
Django view functions grouped by feature area. `__init__.py` re-exports every view (`from .module import name as name`) so URL confs can use `core.views.<name>`.

## Interface
- `dashboards.py`: `dashboard`, `onboard`, `pipeline_dashboard`, `portfolio_dashboard`, `market_dashboard`, `update_market_indicators`.
- `properties.py`: `property_list`, `property_compare`, `property_detail`, `financing_comparison`, `property_add`, `property_edit`, `capex_item_edit`, `property_delete`, `property_add_income`, `property_add_expense`, `property_share`.
- `pipeline.py`: `pipeline_list`, `pipeline_kanban`, `pipeline_review_queue`, `pipeline_review_csv`, `pipeline_advance_stage`, `pipeline_advance`, `pipeline_kill`, `pipeline_hold`, `pipeline_reactivate`, `pipeline_detail`, `pipeline_add_from_source`, `pipeline_offer_create`, `pipeline_dd_checklist`, `pipeline_renovation`, `pipeline_closing_create`.
- `leasing.py`: `leasing_list`, `leasing_kanban`, `leasing_add`, `leasing_detail`, `leasing_showing`, `leasing_application`, `leasing_screening`, `leasing_lease`, `leasing_move_in`, `leasing_stabilize`.
- `screening.py`: `pipeline_screener`, `screener_filter`, `pipeline_screening_settings`, `screening_preview`.
- `discovery.py`: `search_listings`, `analyze_property`, `report_listing`, `report_property`, `vrm_properties_list`, `property_discovery`, `hud_property_list`, `hud_property_detail`, `usda_property_list`, `usda_property_detail`.
- `growth.py`: `growth_areas`, `growth_areas_export_csv`, `growth_explorer`.
- `markets.py`: `investment_targets_edit`, `MarketRefreshView`, `markets_list`, `brrrr_calculator`, `sell_index`.
- `exports.py`: `export_pdf`, `_generate_pdf`.
- `system.py`: `home`, `health_check`, `system_status`, `refresh_all_sources`, `health_json`.
- `permissions.py`: `ROLE_RANK` (`client`=1, `team`=2, `owner`=3), `AuthenticatedUser` protocol, `is_owner_or_shared`.
- `constants.py`: `US_STATES`.

## Invariants
- Every module except `permissions.py`, `constants.py` and `__init__.py` references `login_required`/`LoginRequiredMixin`; `home` and `health_check` in `system.py` should be checked individually before assuming they are protected.
- Role ordering for property access is defined solely by `ROLE_RANK` in `permissions.py`.
- Project rule: no external API calls and no finance math in views; delegate to services/utils.

## Side Effects
- `exports.py`: `_generate_pdf` launches headless Chromium via `playwright.sync_api.sync_playwright`.
- `markets.py` (`MarketRefreshView`) and `system.py` (`refresh_all_sources`) invoke Django management commands via `call_command`, which refresh data sources.
- Views read and write ORM models from [../models](../models/README.md); template filters come from [../templatetags](../templatetags/README.md).

## Verification
- Run: `.venv/bin/python -m pytest tests/` (pytest.ini; pass specific paths for speed). PDF export tests need `.venv/bin/python -m playwright install chromium-headless-shell`.
