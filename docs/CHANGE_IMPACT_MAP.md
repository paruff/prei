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

|If you change…                    |You must also update…                           |
|----------------------------------|------------------------------------------------|
|`portfolio.py` function signatures|`core/api_views.py` calls, `docs/API_SURFACE.md`|
|`cma.py` function signatures      |`core/api_views.py` calls, `docs/API_SURFACE.md`|

## Finance Utils Changes (investor_app/finance/utils.py)

|If you change…                                       |You must also update…                                                                                          |
|-----------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
|`calculate_noi` signature or logic                   |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|`calculate_cap_rate` signature or logic              |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|`calculate_cash_on_cash` signature or logic          |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|`calculate_irr` signature, logic, or accepted types  |`investor_app/tests/test_finance_utils.py`, `tests/test_finance_utils.py`, `docs/API_SURFACE.md`               |
|Internal `irr()` helper                              |`calculate_irr` (its only caller), `tests/test_finance_utils.py`                                               |
|Any KPI function signature                           |`core/services/` callers, `docs/API_SURFACE.md`                                                                |
|KPI formula/logic                                    |All tests for that function — especially boundary tests                                                        |

## Test Module Changes (investor_app/tests/)

|If you change…                                         |You must also update…                                             |
|-------------------------------------------------------|------------------------------------------------------------------|
|`investor_app/tests/test_finance_utils.py` test cases  |Verify matching coverage in `tests/test_finance_utils.py`         |
|Add new `calculate_*` function to `finance/utils.py`   |Add tests in both `investor_app/tests/` and `tests/` test suites  |

## Integration Changes (core/integrations/)

|If you change…              |You must also update…                                                   |
|----------------------------|------------------------------------------------------------------------|
|ATTOM adapter response shape|`core/integrations/sources/attom_adapter.py` + any service consuming it|
|HUD adapter                 |`core/integrations/sources/hud_scraper.py` + management commands       |
|Market data interface       |`core/integrations/market/` wrappers + services consuming them         |

## Config / Environment Changes

|If you change…            |You must also update…                           |
|--------------------------|------------------------------------------------|
|Environment variable names|`.env.example`, `docs/RUNBOOKS.md`, CI workflows|
|Django settings keys      |All code reading them, `.env.example`           |
|Celery task names         |Any callers using `.delay()` or `.apply_async()`|

