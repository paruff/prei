# Architecture — prei

> DORA 2025 (ARCH-01): Loosely coupled architecture is a prerequisite for AI benefit.
> These boundaries are enforced by code review. Add linting rules as the codebase grows.

-----

## Layer Definitions

```
core/models.py        → Django ORM models only. Field definitions, __str__, Meta.
                        No business logic. No external calls.

core/services/        → Business logic services.
                        (cma.py = Comparative Market Analysis, portfolio.py = portfolio KPIs)
                        Calls models and finance/utils. May call integrations via adapter.
                        Never called from templates.

core/api_views.py     → DRF API views. Calls services. Validates via serializers.
                        No financial math inline. No direct model queries.

core/serializers.py   → DRF serializers. Input validation lives here.
                        Decimal parsing and validation for all currency fields.

core/integrations/    → All external API adapters (ATTOM, HUD, market data).
                        Never called directly from views — always via services.
                        sources/ = raw adapters. market/ = domain wrappers.

core/tasks.py         → Celery async tasks only. Calls services. Never business logic.

finance/utils.py      → Pure KPI calculation functions.
                        No Django imports. No DB access. No external calls.
                        Decimal in → Decimal out (float only as intermediate for numpy).

templates/            → HTML rendering only. No business logic. No raw queries.
```

## Dependency Diagram

```
api_views → serializers (validation)
api_views → services → models
                     → finance/utils (KPI calculations)
                     → integrations/ (external data)
tasks → services
templates ← views (context only)
```

## Concrete File Examples

|Layer       |File                                        |Responsibility                                                 |
|------------|--------------------------------------------|---------------------------------------------------------------|
|Models      |`core/models.py`                            |`Property`, `InvestmentAnalysis`, `Transaction` ORM definitions|
|Services    |`core/services/cma.py`                      |Comparative market analysis calculations                       |
|Services    |`core/services/portfolio.py`                |Portfolio-level KPI aggregation                                |
|API Views   |`core/api_views.py`                         |REST endpoints for dashboard, property detail, analysis        |
|Serializers |`core/serializers.py`                       |Request/response validation and serialization                  |
|Integrations|`core/integrations/sources/attom_adapter.py`|ATTOM API client                                               |
|Finance     |`finance/utils.py`                          |Cap rate, CoC, IRR, DSCR, NOI calculations                     |
|Tasks       |`core/tasks.py`                             |Celery tasks for data fetching, alert processing               |

## What Goes Where — Decision Rules

**New KPI calculation?** → `finance/utils.py` as a pure function. Test it there first.

**New external data source?** → New adapter in `core/integrations/sources/`. Wrap with a domain interface in `core/integrations/market/` if it’s market data.

**New API endpoint?** → View in `core/api_views.py` + serializer in `core/serializers.py` + service method in `core/services/`.

**New background job?** → Task in `core/tasks.py` calling an existing service. Never put logic in the task itself.

**New model field?** → `core/models.py` + migration + update `docs/CHANGE_IMPACT_MAP.md`.
