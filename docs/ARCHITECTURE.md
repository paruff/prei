# Architecture — prei

> DORA 2025 (ARCH-01): Loosely coupled architecture is a prerequisite for AI benefit.
> These boundaries are enforced by code review. Add linting rules as the codebase grows.

-----

## Layer Definitions

```
core/models.py        → Django ORM models only. Field definitions, __str__, Meta.
                        No business logic. No external calls.

core/services/        → Business logic services.
                        (scoring.py = underwriting score v2,
                         brrrr.py = BRRRR analysis,
                         projections.py = hold-period projections,
                         market_scoring.py = ZIP market intelligence)
                        Calls models and investor_app/finance/utils. May call integrations via adapter.
                        Never called from templates.

core/api_views.py     → DRF API views. Calls services. Validates via serializers.
                        No financial math inline. No direct model queries.

core/serializers.py   → DRF serializers. Input validation lives here.
                        Decimal parsing and validation for all currency fields.

core/integrations/    → All external API adapters (ATTOM, HUD, market data).
                        Never called directly from views — always via services.
                        sources/ = raw adapters. market/ = domain wrappers.

core/tasks.py         → Background tasks only. Calls services. Never business logic.

investor_app/finance/utils.py → Pure KPI calculation functions.
                        No Django imports. No DB access. No external calls.
                        Decimal in → Decimal out (float only as intermediate for numpy).

templates/            → HTML rendering only. No business logic. No raw queries.

static/css/           → Design system tokens and component styles.
                        tokens.css = CSS custom properties (colors, spacing, typography).
                        base.css = component classes (card, kpi-grid, table, form, verdict, etc.).
                        No Bootstrap. No third-party CSS frameworks.

core/forms.py         → Django form classes with styled widget base classes.
                        StyledNumberInput, StyledTextInput, StyledSelect auto-apply
                        CSS classes from the design system.
```

## Dependency Diagram

```
api_views → serializers (validation)
api_views → services → models
                     → investor_app/finance/utils (KPI calculations)
                     → integrations/ (external data)
tasks → services
templates ← views (context only)
templates → components/ (reusable partials: verdict_badge, score_bar, kpi_card, empty_state)
```

## Client-Side Architecture

### BRRRR Calculator

The BRRRR calculator (`templates/brrrr_calculator.html`) is a **fully client-side JS application**:

- Input fields → JavaScript reads values → computes all metrics in the browser
- No form POST — instant recalculation on any input change
- The Django view (`core/views.py:brrrr_calculator`) simply renders the template
- A server-side engine (`core/services/brrrr.py`) with 25+ tests provides the same math
  for API-driven use cases

### Zero-ARV Guard

If ARV is 0 or empty:
- A prompt is displayed explaining why ARV is required
- The results table is dimmed to `opacity: 0.35`
- No results are shown until ARV is provided

## Concrete File Examples

|Layer       |File                                        |Responsibility                                                 |
|------------|--------------------------------------------|---------------------------------------------------------------|
|Models      |`core/models.py`                            |`Property`, `InvestmentAnalysis`, `UserInvestmentTargets` ORM  |
|Services    |`core/services/scoring.py`                  |`UnderwritingScore` dataclass, `score_listing_v2()`            |
|Services    |`core/services/brrrr.py`                    |`BRRRRAnalysis` dataclass, `calculate_brrrr()`                 |
|Services    |`core/services/projections.py`              |`project_hold_period()`, `YearlyProjection`, `ExitAnalysis`    |
|Services    |`core/services/market_scoring.py`           |`score_market_by_zip()`                                        |
|API Views   |`core/api_views.py`                         |REST endpoints for dashboard, property detail, analysis        |
|Serializers |`core/serializers.py`                       |Request/response validation and serialization                  |
|Integrations|`core/integrations/sources/attom_adapter.py`|ATTOM API client (planned Phase 4)                             |
|Finance     |`investor_app/finance/utils.py`             |Cap rate, CoC, IRR, DSCR, NOI, depreciation, after-tax calc    |
|Forms       |`core/forms.py`                             |`PropertyForm` with `StyledNumberInput`/`StyledTextInput`/`StyledSelect`|
|CSS         |`static/css/tokens.css`                     |Design token custom properties                                 |
|CSS         |`static/css/base.css`                       |Component classes, layout, responsive rules                    |
|Components  |`templates/components/`                     |Reusable partials: `kpi_card.html`, `verdict_badge.html`, etc. |

## Design System Architecture

The frontend uses a **bespoke token-based design system** — no Bootstrap or third-party frameworks:

### Token Layer (`tokens.css`)
```css
:root {
  --color-primary: #4338ca;
  --color-grow-50: #f0fdf4;
  --color-grow-400: #4ade80;
  --color-grow-700: #15803d;
  --sp-4: 16px;
  --text-sm: 14px;
  --radius-md: 8px;
  /* ... 80+ tokens */
}
```

### Component Layer (`base.css`)
Classes like `.card`, `.kpi-grid`, `.data-table`, `.verdict-badge`, `.brrrr-banner` consume tokens.

### Python-Driven Colors
`UnderwritingScore` exposes properties that return CSS class names:
```python
score.coc_color_class   # → "num-good" | "num-warn" | "num-bad"
score.verdict_label     # → "Strong Buy" | "Conditional" | "Pass"
```
Templates reference these directly — no threshold comparisons in HTML.

### Widget Base Classes
`core/forms.py` provides `StyledNumberInput`, `StyledTextInput`, `StyledSelect` that
automatically apply `form-input` and `num` CSS classes. No per-field `attrs` needed.

## What Goes Where — Decision Rules

**New KPI calculation?** → `investor_app/finance/utils.py` as a pure function. Test it there first.

**New external data source?** → New adapter in `core/integrations/sources/`. Wrap with a domain interface in `core/integrations/market/` if it's market data.

**New API endpoint?** → View in `core/api_views.py` + serializer in `core/serializers.py` + service method in `core/services/`.

**New background job?** → Task in `core/tasks.py` calling an existing service. Never put logic in the task itself.

**New model field?** → `core/models.py` + migration + update `docs/CHANGE_IMPACT_MAP.md`.

**New CSS class?** → Use token values from `tokens.css`. Never hardcode colors. If the class is a component, add to `base.css` with a comment section header.

**New form widget?** → Extend `StyledNumberInput` or `StyledTextInput` in `core/forms.py`. Don't add per-field `attrs` in templates.
