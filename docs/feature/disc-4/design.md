# Design: DISC-4 — HUD/USDA Property List & Detail Views

## Impacted Components

| Component | Change |
|---|---|
| `core/services/pipeline.py` | Add `create_from_hud()`, `create_from_usda()` |
| `core/views.py` | Extend `pipeline_add_from_source`; add `hud_property_list`, `hud_property_detail`, `usda_property_list`, `usda_property_detail` |
| `core/urls.py` | Add URL patterns for HUD/USDA views |
| `templates/hud_properties/list.html` | **New** |
| `templates/hud_properties/detail.html` | **New** |
| `templates/usda_properties/list.html` | **New** |
| `templates/usda_properties/detail.html` | **New** |
| `core/tests/test_discovery_views.py` | **New** — acceptance tests |

## View Patterns

### hud_property_list
- GET: list HudProperty records with optional state filter
- Context: `hud_properties` queryset, `states` list, `selected_state`
- Template: `hud_properties/list.html`

### hud_property_detail
- GET by pk: single HudProperty record
- Context: `hud_property` instance, `pipeline_add_url`
- Template: `hud_properties/detail.html`
- Includes "Add to Pipeline" form → POST to `pipeline_add_from_source`

### usda_property_list / usda_property_detail
- Same pattern as HUD, substituting UsdaProperty

## Service Functions

### create_from_hud(hud_property, user) → (PipelineProperty, created)
- Maps: `hud_case_number` → `source_id`, `asking_price or list_price` → `price`,
  `bedrooms` → `beds`
- Runs `screen_property(hud_property, criteria)` immediately

### create_from_usda(usda_property, user) → (PipelineProperty, created)
- Same pattern, using `usda_case_number` → `source_id`

## Template Patterns

Both HUD and USDA templates follow the VRM list/detail pattern:
- `list.html`: state filter form, property table, "Add to Pipeline" button per row
- `detail.html`: property card with full details, "Add to Pipeline" form
- "Add to Pipeline" posts to `pipeline_add_from_source` with `source_type` and `source_id`
