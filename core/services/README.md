# core/services

## Overview
Service layer for prei analytics and workflow. Per project rules, finance math lives here (Decimal-based) and views must not call external APIs directly. Modules are flat and grouped by concern below; discovery adapters live in [./sources/README.md](./sources/README.md).

## Interface
Package exports (`__init__.py`): `compute_noi`, `compute_noi_for_user`, `compute_noi_from_amounts`, `compute_portfolio_summary`.

**Underwriting and finance math**
- `underwriting.py`: `UnderwritingInput`, `UnderwritingMetrics`, `gross_potential_rent`, `effective_gross_income`, `total_operating_expenses`, `net_operating_income`, `cash_on_cash_yield`, `max_allowable_offer`, `solve_underwriting`.
- `offer.py`: `OfferStrategy`, `OfferInput`, `OfferMetrics`, `solve_offer`.
- `brrrr.py`: `BRRRRAnalysis`, `calculate_brrrr`, `analyze_brrrr_deal`, `DSCR_LENDER_THRESHOLD`.
- `capex.py`: `CapExItem`, `DEFAULT_CAPEX_ITEMS`, `get_default_capex_items_for_age`, `calculate_capex_reserve`, `calculate_capex_reserve_for_property`.
- `projections.py`: `YearlyProjection`, `ExitAnalysis`, `project_hold_period`.
- `exit_strategy.py`: `ExitStrategyResult`, `model_exit_strategies`, `exit_strategy_table`.
- `sensitivity.py`: `sensitivity_analysis_table`.
- `financing_comparison.py`: `ScenarioResult`, `get_or_create_default_scenarios`, `calculate_scenario_result`, `compare_scenarios`, `get_best_scenario`.
- `property_service.py`: `compute_noi`, `compute_noi_for_user`, `compute_noi_from_amounts`.
- `cma.py`: `price_per_sqft`, `find_undervalued`, `estimate_listing_kpis`, `estimate_kpis`.

**Scoring and screening**
- `scoring.py`: `UnderwritingScore`, `score_listing_v2`, `score_listing`, `score_listing_v1_deprecated`.
- `screening.py`: `ScreeningThresholds`, `ScreeningResult`, `gross_yield`, `price_to_rent_ratio`, `compute_screening_metrics`, `evaluate_screening_stage`, `screen_batch`, `hud_fmr_rent`, `get_or_create_criteria`, `screen_property`.
- `market_scoring.py`: `score_market`, `update_market_scores`, `calculate_price_to_rent_ratio`, `score_market_by_zip`, `score_market_compat`.
- `market_data.py`: `refresh_market_snapshot`.
- `landlord_data.py`: `STATE_LANDLORD_FRIENDLINESS`, `get_state_landlord_score`.
- `recommendations.py`: `recommend_listings`, `explain_recommendation`.

**Pipeline and discovery**
- `pipeline.py`: `STAGE_ORDER`, `STAGE_TIMESTAMP_FIELD`, `advance_stage`, `kill_property`, `hold_property`, `reactivate_property`, `get_source_record`, `create_from_vrm|foreclosure|hud|usda|county_notice`, `expense_estimates`, `convert_to_property_record`, `underwriting_summary`.
- `leasing.py`: `LEASING_STAGE_ORDER`, `advance_stage`, `mark_filled`, `put_on_hold`.
- `discovery.py`: `CanonicalPropertyPayload`, `DiscoverySanitizer`.
- `discovery_processor.py`: `process_discovery_batch` (stats only), `process_discovery` (persists).
- `ingestion.py`: `ingest_hud_reo`, `ingest_usda_reo`, `ingest_tx_counties`, `ingest_sheriff_sales`, `get_hud_dollar_homes`.
- `sources/`: [./sources/README.md](./sources/README.md) - `DiscoverySource` adapters and registry.

**Portfolio, collaboration, notifications**
- `portfolio.py`: `PortfolioCashflow`, `compute_portfolio_cashflow`, `monthly_income_series`, `portfolio_trend_summary`, `aggregate_portfolio`, `compute_portfolio_summary`, `compute_portfolio_performance`, variance/flag helpers (`calculate_coc_variance`, `calculate_vacancy_variance`, `calculate_expense_variance`, `calculate_ytd_cashflow`, `check_flag_for_attention`), `AcquiredPosition`, `acquired_position`.
- `collaboration.py`: `share_property_with_team`, `add_note`, `get_team_properties`.
- `notifications.py`: `notify_pipeline_match`.
- `saved_search_notifications.py`: `get_saved_search_matches`, `create_notification_for_match`, `check_listings_against_saved_searches`, `fetch_new_listings`.
- `audit.py`: `log_action`.

## Invariants
- Pipeline stage order is `STAGE_ORDER` (DISCOVERED ... STABILIZED); `advance_stage` raises `ValueError` past STABILIZED or on unknown stage (`pipeline.py`). Leasing has its own `LEASING_STAGE_ORDER` and the same guards (`leasing.py`).
- Money is `Decimal`; `screening.py` threshold evaluator is float-based and transient (no persistence).
- Input guards raise `ValueError`: `project_hold_period` (hold_years 1-50), `OfferInput` (mao > 0, rehab_budget >= 0, desired_equity in [0,1], competition_multiplier in [0.5,2.0]), `calculate_price_to_rent_ratio` (price and rent > 0), `monthly_income_series` (months positive), `compute_noi` (insufficient data).
- `compute_noi_for_user` skips properties lacking data with a warning rather than failing.
- Defaults come from `settings.FINANCE_DEFAULTS` (`cma.py`, `brrrr.py`).

## Side Effects
- DB writes: `AuditLog` (`log_action`), `PropertyNote`/`SharedProperty` (`collaboration.py`), `Notification`/`NotificationPreference` (`notifications.py`, `saved_search_notifications.py`), `InvestmentAnalysis` (`property_service.py`, `scoring.py`), `FinancingScenario` (`financing_comparison.py`), `ScreeningCriteria` get-or-create, `PipelineProperty` create/save (`pipeline.py`, `leasing.py`, `discovery_processor.process_discovery`), `MarketSnapshot.market_score` (`market_scoring.update_market_scores`), `HudProperty` upserts (`ingestion.py`).
- Network: `ingestion.py` (`requests.get` to HUD/USDA/county feeds), `market_data.py` (market adapters, API keys read via `os.getenv`).
- Logging in most modules; `recommend_listings` logs exceptions via `logger.exception`.

## Verification
- Run: `.venv/bin/python -m pytest tests/test_screening.py tests/test_pipeline.py tests/test_discovery.py tests/test_financing_comparison.py tests/test_capex.py` (config in `pytest.ini`)
