# Design: DISC-3 — Add HUD and USDA to Pipeline Screening

## Impacted Components

| Component | Change |
|---|---|
| `core/services/screening.py` | Add source model detection, `kill_reason`/`yield_evaluated`/`yield_note` to ScreeningResult |
| `core/tests/test_screening.py` | **Append** — 4 acceptance tests for HUD/USDA screening |

## Approach

### Source Model Detection

When `screen_property()` receives a HudProperty or UsdaProperty as its first
argument (instead of a PipelineProperty), detect it via duck typing and treat
it as both the source_record and the data source for hard-kill attributes.

Key mappings:

| HudProperty attr | PipelineProperty equivalent |
|---|---|
| `asking_price or list_price` | `price` |
| `bedrooms` | `beds` |
| `state` | (via source_record) |
| `city` | (via source_record) |
| `property_type` | (via source_record) |

### ScreeningResult Extensions

```python
@property
def kill_reason(self) -> str | None:
    return self.hard_failures[0] if self.hard_failures else None

@property
def yield_evaluated(self) -> bool:
    return "Gross yield" in str(self.passes) or "Gross yield" in str(self.soft_failures)

@property
def yield_note(self) -> str:
    for msg in self.passes + self.soft_failures:
        if "yield" in msg.lower():
            return "no_rent_estimate" if "skipped" in msg.lower() else "evaluated"
    return ""
```

### Changes to screen_property()

1. Detect if first arg is a source model (has `_state` or specific fields)
2. If source model: treat as `source_record`, derive price/beds from it
3. Existing hard-kill flow works via getattr on source_record
4. Existing yield/PTR skip works (no rent data → skipped)

## Tests

| Test | Verifies |
|---|---|
| `test_hud_property_fails_state_kill` | HudProperty in non-target state → hard-killed, `kill_reason == 'state_not_target'` |
| `test_hud_property_yield_skipped_no_rent` | HUD yield → `yield_evaluated is False`, `yield_note == 'no_rent_estimate'` |
| `test_usda_property_fails_state_kill` | UsdaProperty same behavior |
| `test_usda_property_yield_skipped_no_rent` | USDA yield same behavior |
