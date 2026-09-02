# Plan — split `core/views/__init__.py`

Addresses **H6** from the production audit. Not yet executed: this is the shape
for review before a 4,315-line move.

**Goal:** turn `core/views/__init__.py` (4,315 lines, 78 top-level symbols) into
a set of domain modules under the `core/views/` package that already exists,
without changing behavior or breaking a single test.

**Why it is worth doing:** together with `core/api_views.py` (2,458 lines) this
file is ~17% of non-test Python, against a house guideline of 800 lines. A
package `__init__` holding four thousand lines of view logic is also the least
discoverable place for it — `core/services/` and `core/models/` are already
split this way, so this is bringing one straggler in line, not inventing a
pattern.

---

## The constraint that dictates the approach

36 test patch targets address symbols through `core.views`:

| Patch target | Count |
| --- | --- |
| `core.views.discover_places_in_state` | 13 |
| `core.views.fetch_place_growth_metrics` | 11 |
| `core.views.fetch_housing_demand_index` | 11 |
| `core.views._generate_pdf` | 1 |

`core/urls.py` also does `from . import views` and then `views.home`,
`views.onboard`, … for every route.

So `core/views/__init__.py` **must keep re-exporting every public name**, and
must keep importing the three integration functions into its own namespace so
`@patch("core.views.fetch_place_growth_metrics")` still resolves. A split that
moves symbols without re-exporting breaks 36 tests and every URL route.

This is why the plan ends with `__init__.py` as a re-export shim rather than an
empty file.

---

## Target structure

| New module | Source lines | Symbols |
| --- | --- | --- |
| `core/views/permissions.py` | 90–158 | `AuthenticatedUser`, `_get_property_role`, `is_owner_or_shared`, `_is_client_only_user` |
| `core/views/system.py` | 159–391 | `home`, `health_check`, `system_status`, `refresh_all_sources`, `health_json` |
| `core/views/dashboards.py` | 392–524, 1484–1618 | `dashboard`, `onboard`, `pipeline_dashboard`, `portfolio_dashboard`, `market_dashboard`, `update_market_indicators` |
| `core/views/properties.py` | 525–1029 | `property_list`, `_parse_compare_ids`, `property_compare`, `property_detail`, `financing_comparison`, `property_add`, `property_edit`, `capex_item_edit`, `property_delete`, `property_add_income`, `property_add_expense`, `property_share` |
| `core/views/growth.py` | 1030–1483 | `growth_areas`, `growth_areas_export_csv`, `growth_explorer` |
| `core/views/pipeline.py` | 1619–2202, 2595–2823 | `pipeline_list` … `pipeline_detail`, `pipeline_add_from_source`, `pipeline_offer_create`, `pipeline_dd_checklist`, `pipeline_renovation`, `pipeline_closing_create` |
| `core/views/screening.py` | 2203–2594 | `pipeline_screener`, `screener_filter`, `pipeline_screening_settings`, `screening_preview` |
| `core/views/leasing.py` | 2824–3215 | the eleven `leasing_*` views |
| `core/views/exports.py` | 3419–3638 | `_get_financing_value`, `_format_financing_value`, `_generate_pdf`, `export_pdf` |
| `core/views/markets.py` | 3717–3874 | `investment_targets_edit`, `MarketRefreshView`, `markets_list`, `brrrr_calculator`, `sell_index` |
| `core/views/discovery.py` | 3216–3418, 3639–3716, 3875–4322 | `search_listings`, `analyze_property`, `report_listing`, `report_property`, `vrm_properties_list`, `property_discovery`, `hud_property_list`, `hud_property_detail`, `usda_property_list`, `usda_property_detail` |

`pipeline` is split at `screening` deliberately: the screener carries its own
settings and preview flow and is the one part of the pipeline group a reader can
hold separately. Without that cut `pipeline.py` lands near 1,200 lines and
simply reproduces the problem at smaller scale.

---

## Order of work

One module per commit, largest blast radius last. After each: run the full
suite, commit, move on. Never two modules in one commit — if a re-export is
missed, the failing test should name the module that caused it.

1. `permissions.py` — no Django view surface, safest first move, and every
   other module imports from it
2. `system.py`
3. `markets.py`
4. `exports.py` — carries the one `_generate_pdf` patch target
5. `leasing.py`
6. `screening.py`
7. `properties.py`
8. `dashboards.py`
9. `discovery.py`
10. `growth.py` — carries 35 of the 36 patch targets, so it goes last, when the
    re-export pattern is already proven by nine prior moves

## Per-module recipe

```bash
# 1. Move the symbols verbatim. No refactoring during the move — a behavior
#    change hidden inside a 400-line diff is unreviewable.
# 2. Add the imports that module needs at its top.
# 3. Re-export from core/views/__init__.py:
#      from .growth import growth_areas, growth_areas_export_csv, growth_explorer
# 4. Keep integration imports in __init__.py so patch targets still resolve:
#      from core.integrations.market.census import fetch_place_growth_metrics
# 5. Verify, then commit.
DJANGO_SETTINGS_MODULE=investor_app.settings_test \
  python -m pytest tests/ core/tests/ -m "unit or integration" -q
python manage.py check
ruff check . && ruff format --check .
```

## Definition of done

- `core/views/__init__.py` contains imports and `__all__` only
- No module over 800 lines
- All 36 `core.views.*` patch targets still resolve
- `manage.py check` clean, ruff clean, full unit + integration suite green
- Zero behavior diff: no signature, template, context key, or route changed

## Explicitly not in scope

- Splitting `core/api_views.py` (2,458 lines) — same treatment, separate plan
- Any refactoring of the view logic itself
- Rebalancing the test pyramid (H5); tracked separately
