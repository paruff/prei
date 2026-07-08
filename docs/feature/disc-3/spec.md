# Specification: DISC-3 — Add HUD and USDA to Pipeline Screening

## Problem Statement

The screening service (`screen_property`) evaluates PipelineProperty records
against user-defined ScreeningCriteria. Currently it only fully supports
VrmProperty (with rent data) and ForeclosureProperty (without rent data).
HudProperty and UsdaProperty sources from DISC-1/DISC-2 are not recognized
as valid source types, so they fall through without proper hard-kill or
soft-criteria handling.

HUD/USDA properties have known prices and property types — hard-kill criteria
(price floor/ceiling, property type, state) should apply directly. Yield-based
criteria require a rent estimate and should be flagged as "not evaluable — no
rent estimate" rather than silently skipped.

## Scope

| In scope | Out of scope |
|---|---|
| Recognize HudProperty as valid source type | Rentcast integration for rent estimates |
| Recognize UsdaProperty as valid source type | USDA REMOVED status (DISC-2) |
| Hard-kill criteria: state, price, property type | BDD scenarios |
| Yield/PTR → flagged "no rent estimate" |  |
| `kill_reason` property on ScreeningResult |  |
| `yield_evaluated` / `yield_note` on ScreeningResult |  |

## Dependencies

- DISC-1 (HudProperty with asking_price, insured_status)
- DISC-0 (UsdaProperty model exists)

## Acceptance Criteria

| # | Criterion | test_type |
|---|---|---|
| AC1 | HudProperty in non-target state is hard-killed with state_not_target reason | unit |
| AC2 | HudProperty yield screening yields `yield_evaluated=False, yield_note=no_rent_estimate` | unit |
| AC3 | UsdaProperty in non-target state is hard-killed | unit |
| AC4 | UsdaProperty yield screening is skipped with no-rent-estimate note | unit |
