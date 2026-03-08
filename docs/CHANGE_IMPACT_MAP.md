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

## Finance Utils Changes (finance/utils.py)

|If you change…            |You must also update…                                  |
|--------------------------|-------------------------------------------------------|
|Any KPI function signature|`core/services/` callers, `docs/API_SURFACE.md`        |
|KPI formula/logic         |All tests for that function — especially boundary tests|

## Integration Changes (core/integrations/)

|If you change…              |You must also update…                                                  |
|----------------------------|-----------------------------------------------------------------------|
|ATTOM adapter response shape|`core/integrations/sources/attom_adapter.py` + any service consuming it|
|HUD adapter                 |`core/integrations/sources/hud_scraper.py` + management commands       |
|Market data interface       |`core/integrations/market/` wrappers + services consuming them         |

## Config / Environment Changes

|If you change…            |You must also update…                           |
|--------------------------|------------------------------------------------|
|Environment variable names|`.env.example`, `docs/RUNBOOKS.md`, CI workflows|
|Django settings keys      |All code reading them, `.env.example`           |
|Celery task names         |Any callers using `.delay()` or `.apply_async()`|
