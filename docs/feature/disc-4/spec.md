# Specification: DISC-4 — HUD/USDA Property List & Detail Views

## Problem Statement

HUD and USDA properties are now ingested into HudProperty and UsdaProperty
models, and they can be screened via the pipeline service. However, there are
no dedicated views to browse or inspect these properties, and no "Add to
Pipeline" button to move them into the user's pipeline.

VRM properties already have `vrm_properties_list` and detail views with an
"Add to Pipeline" button. HUD and USDA need equivalent views.

## Scope

| In scope | Out of scope |
|---|---|
| `hud_property_list` view | Filtering beyond state/ZIP (future) |
| `hud_property_detail` view | Batch screening from list view |
| `usda_property_list` view | Pagination (beyond basic queryset) |
| `usda_property_detail` view | Complex template styling |
| Extend `pipeline_add_from_source` for HUD/USDA |  |
| `create_from_hud()` / `create_from_usda()` service functions |  |
| List and detail templates |  |

## Dependencies

- DISC-1 (HudProperty model with asking_price)
- DISC-2 (UsdaProperty model — status choices)
- DISC-3 (screening support for HUD/USDA)

## Acceptance Criteria

| # | Criterion | test_type |
|---|---|---|
| AC1 | hud_property_list view returns 200 | unit |
| AC2 | "Add to Pipeline" POST creates PipelineProperty with source_type='hud' | unit |
| AC3 | usda_property_list view returns 200 | unit |
| AC4 | "Add to Pipeline" POST creates PipelineProperty with source_type='usda' | unit |
