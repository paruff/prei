# core

## Overview
The single Django app of prei. It holds the ORM models, the service layer (finance, screening, pipeline,
discovery), external-data integrations, HTML views, the REST API, and export, form and template helpers.
The Django project package (settings, root URLs) lives in `investor_app/`.

## Interface
Direct modules:
- `admin.py`: `PropertyAdmin`, `ListingAdmin`, `PipelineAssetAdmin`, `DiscoveryRequestAdmin` and other ModelAdmins.
- `apps.py`: `CoreConfig`.
- `urls.py`, `api_urls.py` (`app_name = "api"`): HTML and REST routes.
- `api_views.py`: DRF views and function views, e.g. `ListingListView`, `PortfolioAnalyticsView`, `growth_areas_list`,
  `foreclosures_list`, `watchlist_view`, `alerts_view`, `notifications_view`, the `export_*` endpoints, `health_check`,
  `VrmPropertyListAPI`; throttles `CalculationRateThrottle`, `ListingPagination`.
- `serializers.py`: `GrowthMetricsSerializer`, `GrowthAreaSerializer`, `ForeclosurePropertySerializer` and related.
- `forms.py`: `PropertyForm`, `RentalIncomeForm`, `OperatingExpenseForm`, `CapExItemForm`, `InvestmentTargetsForm`,
  `StyledNumberInput`, `PercentField`.
- `validators.py`: `validate_state_code`, `validate_min_growth_score`, `validate_location_parameter`,
  `validate_foreclosure_stages`, `validate_property_types`, `validate_positive_integer`, `validate_positive_decimal`.
- `decorators.py`: `is_rate_limited`, `rate_limit`.
- `middleware.py`: `RequestTimingMiddleware`, `SecurityHeadersMiddleware`.
- `context_processors.py`: `version`.
- `export_helpers.py`: `parse_and_filter_location`, `apply_foreclosure_filters`.
- `views_portfolio.py`: `MonthlyActualsForm`, `portfolio_dashboard`, `portfolio_actuals_add`.

Subpackages:
- [data](./data/README.md): static city/county/FIPS lookups.
- [export_services](./export_services/README.md): CSV, JSON and PDF export services.
- [integrations](./integrations/README.md): external data adapters and scrapers.
- [management](./management/README.md): `manage.py` commands.
- [migrations](./migrations/README.md): schema history.
- [models](./models/README.md): ORM models.
- [services](./services/README.md): business logic and finance math.
- [templatetags](./templatetags/README.md): template filters.
- [views](./views/README.md): HTML view functions.

## Invariants
- `validators.py` functions validate request input at the API boundary; `api_views.py` imports them.
- Per `AGENTS.md`: money is `Decimal`, finance math lives in services/utils, and views make no external API calls.
- Model, auth and migration changes need human approval (`AGENTS.md`).

## Side Effects
- `middleware.py` and `decorators.py` touch the request/response cycle and, for `is_rate_limited`, the cache.
- `context_processors.py` reads version and git metadata from disk.
- `api_views.py` exports and VRM endpoints read and write the database.

## Verification
- Run: `.venv/bin/python -m pytest tests/ core/tests/` (see `pytest.ini`; the full suite takes ~10 min).
