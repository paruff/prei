# Change Impact Map — prei

> Update whenever a model, service signature, or KPI function changes.

## Model Changes (core/models.py)

|If you change…             |You must also update…                                                    |
|---------------------------|-------------------------------------------------------------------------|
|`Property` model fields    |`core/serializers.py`, relevant views, `docs/API_SURFACE.md`, migration  |
|`InvestmentAnalysis` model |`core/services/portfolio.py`, `core/serializers.py`, templates, migration|
|`Transaction` model        |`core/services/portfolio.py`, `core/serializers.py`, migration           |
|`RentalIncome` model       |Financial KPI functions that use rental income, serializers, migration   |
|`OperatingExpense` model   |NOI calculation in `finance/utils.py`, serializers, migration            |
|Any model with a ForeignKey|Check `core/api_views.py` for `select_related` updates                   |

## Service Changes (core/services/)

|If you change…                              |You must also update…                                                                          |
|--------------------------------------------|-----------------------------------------------------------------------------------------------|
|`portfolio.py` function signatures          |`core/api_views.py` calls, `docs/API_SURFACE.md`                                               |
|`cma.py` function signatures                |`core/api_views.py` calls, `docs/API_SURFACE.md`                                               |
|`market_data.refresh_market_snapshot` logic |`core/tests/test_neighborhood_insights.py`, `docs/API_SURFACE.md`                              |
|`market_data.py` adapter imports            |`core/integrations/market/` (comps, rents, crime, schools), `core/tests/test_neighborhood_insights.py`|

## Finance Utils Changes (investor_app/finance/utils.py)

|If you change…                                       |You must also update…                                                                                          |
|-----------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
|`calculate_noi` signature or logic                   |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|`calculate_cap_rate` signature or logic              |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|`calculate_cash_on_cash` signature or logic          |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|`calculate_irr` signature, logic, or accepted types  |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|Internal `irr()` helper                              |`calculate_irr` (its only caller), `tests/test_finance_utils.py`                                               |
|`one_percent_rule` signature or logic                |`tests/test_underwriting_score.py`, `docs/API_SURFACE.md`                                                      |
|`gross_rent_multiplier` signature or logic           |`tests/test_underwriting_score.py`, `docs/API_SURFACE.md`                                                      |
|`score_listing_v2` signature or logic                |`tests/test_underwriting_score.py`, `docs/API_SURFACE.md`; callers must supply `local_market_cap_rate` from `MarketSnapshot` at the service layer |
|`project_annual_cash_flows` signature or logic       |`tests/test_hold_period.py`, `docs/API_SURFACE.md`                                                             |
|`project_property_value` signature or logic          |`tests/test_hold_period.py`, `docs/API_SURFACE.md`                                                             |
|`net_sale_proceeds` signature or logic               |`tests/test_hold_period.py`, `docs/API_SURFACE.md`                                                             |
|`total_return_summary` signature or logic            |`tests/test_hold_period.py`, `docs/API_SURFACE.md`                                                             |
|Any KPI function signature                           |`core/services/` callers, `docs/API_SURFACE.md`                                                                |
|KPI formula/logic                                    |All tests for that function — especially boundary tests                                                        |

## Test Module Changes (investor_app/tests/)

|If you change…                                         |You must also update…                                             |
|-------------------------------------------------------|------------------------------------------------------------------|
|`investor_app/tests/test_finance_utils.py` test cases  |Verify matching coverage in `tests/test_finance_utils.py`         |
|Add new `calculate_*` function to `finance/utils.py`   |Add tests in both `investor_app/tests/` and `tests/` test suites  |

## Integration Changes (core/integrations/)

|If you change…                    |You must also update…                                                                        |
|----------------------------------|---------------------------------------------------------------------------------------------|
|ATTOM adapter response shape or public methods|`core/integrations/sources/attom_adapter.py`, `core/tests/test_attom_adapter.py`, `docs/API_SURFACE.md`, and any service consuming it |
|HUD adapter scrape/parsing logic  |`core/integrations/sources/hud_scraper.py`, `core/tests/test_hud_scraper.py`, management commands, `docs/API_SURFACE.md` |
|Market data interface             |`core/integrations/market/` wrappers + services consuming them                              |
|`market/comps.py` return shape    |`core/services/market_data.py` (price_trend calc), `core/tests/test_neighborhood_insights.py`|
|`market/rents.py` return type     |`core/services/market_data.py` (rent_index field), `core/tests/test_neighborhood_insights.py`|
|`market/crime.py` return type     |`core/services/market_data.py` (crime_score field), `core/tests/test_neighborhood_insights.py`|
|`market/schools.py` return type   |`core/services/market_data.py` (school_rating field), `core/tests/test_neighborhood_insights.py`|

## Config / Environment Changes

|If you change…            |You must also update…                           |
|--------------------------|------------------------------------------------|
|Environment variable names|`.env.example`, `docs/RUNBOOKS.md`, CI workflows|
|Django settings keys      |All code reading them, `.env.example`           |
|Celery task names         |Any callers using `.delay()` or `.apply_async()`|
