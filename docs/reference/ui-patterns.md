# UI Patterns Reference

> The components and design-system conventions used across prei's templates.

---

## Design System

prei uses a custom design system — no Bootstrap. Styling comes from two CSS files:

- **`tokens.css`** — CSS custom properties for colors, spacing, typography, radii, and
  shadows. All theme values live here; templates never hardcode hex colors.
- **`base.css`** — base element styles and component classes used by templates.

Templates are Django templates rendering server-side with the standard tag set
(`{% block %}`, `{% url %}`, `{% for %}`, `{% if %}`). All layout uses semantic
elements and CSS classes; **no inline `style=` attributes on layout elements** and no
`!important` (if a responsive rule is broken, fix the template).

## Page Layout

| Class | Used for |
|---|---|
| `.page-header` | Page title + subtitle + nav-right actions |
| `.kpi-grid` | 4-column metric cards (e.g., discovery/screener KPIs) |
| `.card` | Bordered content blocks (settings, detail panels) |
| `.table-wrap` + `.data-table` | Responsive tables with horizontal scroll on small screens |
| `.filter-bar` | Inline form controls above a list (search, selects, sort) |
| `.form-grid-2` | 2-column form layout |
| `.form-actions` | Button groups at the bottom of forms |
| `.message` / `.message-success` / `.message-warning` / `.message-danger` | Django `messages` feedback banners |

## Data Table Patterns

- **Sortable headers** — header links pass `?sort=<field>&order=asc|desc`.
- **Status chips** — `.chip` with modifiers:
  - `.chip-success` — good/passed state (e.g., confidence ≥ 80%, LL-friendly)
  - `.chip-warning` — caution state (e.g., mixed, confidence 50–79%)
  - `.chip-danger` — bad/failed state (e.g., tenant-friendly, confidence < 50%)
  - `.chip-default` — neutral state
  - Chips carry **text + color**, so color is never the only indicator.
- **Expandable rows** — detail rows hidden/expanded with a toggle button; used on the
  Growth Areas list to show per-signal breakdowns.
- **Truncated text** — long addresses/values truncate with a tooltip via `title=`.

## Form Patterns

| Class | Used for |
|---|---|
| `.form-group` | Label + input wrapper |
| `.form-hint` | Helper text under an input |
| `.card-selectable` | Checkbox cards (used in discovery source selection) |
| `.form-grid-2` | Two-column responsive form grid |
| `.form-actions` | Primary/secondary button row |

Forms use standard Django form handling: GET renders the empty form, POST validates and
redirects on success (Post/Redirect/Get). Validation errors render inline.

## Navigation

- **Breadcrumbs / page-sub** — secondary text under the page header describing where
  you are (e.g., "Growth Areas → Explore").
- **Back links** — placed in the header `nav-right` area.
- **Deep linking with query params** — pages preserve filters in the URL so views are
  shareable:
  - Growth Areas: `?growth_area_id=X`
  - Screener: `?growth_area_id=X&passed=1&status=ACTIVE&sort=price&order=desc`
  - Discovery: `?growth_area_id=X`

## Loading States

- **`.kanban-modal-overlay` / `.kanban-hidden`** — modal overlay for kanban actions;
  hidden class toggles visibility.
- **Inline loading messages** — Django `messages.info` for background work (e.g., VRM
  scrape started; refresh in a minute).
- Background collection runs in threads under a 30s Gunicorn worker timeout — the UI
  tells you to refresh rather than blocking.

## Empty States

- **`.empty-state`** with:
  - `.empty-state-icon` (decorative, `aria-hidden="true"`)
  - title + body text
  - an optional CTA button
- The empty state carries `role="status"` so screen readers announce it.

## Accessibility

- Semantic HTML: `<table>` for tabular data, `<form>`/`<label>` for inputs,
  `<button>` for actions, `<a>` for links.
- `aria-hidden="true"` on decorative icons; `role="status"` on status regions.
- Focus-visible styles on all interactive elements.
- Color is never the sole indicator — chips pair color with text labels; warning
  messages pair color with text.

## Related

- [Investor Workflow](../explanation/investor-workflow.md) — how these pages connect
- [Data Sources & API Keys](../reference/data-sources.md) — env vars that drive UI state
- [Financial KPIs](../reference/financial-kpis.md) — metric definitions shown in tables
