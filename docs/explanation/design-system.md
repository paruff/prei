# Design System — prei

> **Why a custom design system?** prei is a financial tool where color communicates investment
> quality (good/warn/bad). Bootstrap's utility-first approach would scatter threshold logic
> across templates. A declarative, token-driven system keeps decision logic in Python and
> presentation in CSS.

---

## Tokens

All design tokens live in `static/css/tokens.css` as CSS custom properties on `:root`.

### Color Palette

| Token | Purpose |
|---|---|
| `--color-primary` | Primary action color (indigo) |
| `--color-grow-50` / `--color-grow-400` / `--color-grow-700` | Good / strong metrics (green scale) |
| `--color-caution-50` / `--color-caution-400` / `--color-caution-700` | Warning metrics (amber scale) |
| `--color-risk-50` / `--color-risk-400` / `--color-risk-700` | Bad / failing metrics (red scale) |
| `--color-verdict-a-bg` / `--color-verdict-a-text` | "Strong Buy" badge |
| `--color-verdict-b-bg` / `--color-verdict-b-text` | "Conditional" badge |
| `--color-verdict-c-bg` / `--color-verdict-c-text` | "Pass" badge |
| `--color-neutral-50` through `--color-neutral-900` | Neutral / text colors |

### Surfaces & Borders

| Token | Purpose |
|---|---|
| `--surface-page` | Page background (white / dark gray in dark mode) |
| `--surface-card` | Card background |
| `--surface-secondary` | Secondary surface (KPI cards, hover states) |
| `--border-default` | Standard border (1px solid) |
| `--border-subtle` | Subtle divider |

### Typography & Spacing

| Token | Value |
|---|---|
| `--font-sans` | `Inter, -apple-system, sans-serif` |
| `--font-mono` | `JetBrains Mono, monospace` |
| `--text-xs` / `--text-sm` / `--text-base` / `--text-lg` / `--text-xl` | 12 / 14 / 16 / 18 / 22 px |
| `--weight-regular` / `--weight-medium` / `--weight-semibold` | 400 / 500 / 600 |
| `--sp-1` through `--sp-8` | 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 px |
| `--radius-sm` / `--radius-md` / `--radius-lg` / `--radius-pill` | 4 / 8 / 12 / 9999 px |
| `--nav-height` | 56 px |

---

## Component Library

### Cards
```html
<div class="card">
  <h2 class="card-title">Section Title</h2>
  <!-- content -->
</div>
```

### KPI Grid
```html
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Cash-on-Cash</div>
    <div class="kpi-value num-good">8.5%</div>
    <div class="kpi-sub">Target: 6%</div>
  </div>
</div>
```

### Buttons
```html
<button class="btn">Default</button>
<button class="btn btn-primary">Primary</button>
<button class="btn btn-danger">Delete</button>
```

### Forms
```html
<div class="form-group">
  <label class="form-label">Purchase Price</label>
  <input class="form-input" type="text" ...>
  <div class="form-hint">Include closing costs</div>
  <div class="form-error">Required field</div>
</div>
```

Grid variants:
- `.form-grid-2` — 2-column grid
- `.form-grid-3` — 3-column grid
- `.form-grid-2-1` — 2fr + 1fr
- `.form-grid-2-1-1` — 2fr + 1fr + 1fr

### Verdict Badge
```html
{% include "components/verdict_badge.html" with verdict="Strong Buy" %}
```

Always use the `{% include %}` pattern — never hardcode badge markup.

### Score Bar
```html
{% include "components/score_bar.html" with score=score_obj %}
```

### Data Table
```html
<div class="table-wrap">
  <table class="data-table">
    <thead><tr><th>Metric</th><th class="col-right">Value</th></tr></thead>
    <tbody>...</tbody>
  </table>
</div>
```

### Tabs
```html
<div class="tab-bar">
  <button class="tab-btn is-active" data-tab="overview">Overview</button>
  <button class="tab-btn" data-tab="details">Details</button>
</div>
<div id="tab-overview">...</div>
<div id="tab-details" hidden>...</div>
```
Tab switching uses `panel.hidden` — not `style.display`.

### BRRRR Verdict Banner
```html
<div class="brrrr-banner is-full-cycle">
  <div class="brrrr-banner-label">Full Cycle</div>
  <div class="brrrr-banner-sub">You recycled 100% of your capital</div>
</div>
```
Classes: `.is-full-cycle`, `.is-partial`, `.is-trap`.

### Empty State
```html
{% include "components/empty_state.html" with title="No properties" body="Add your first property" %}
```

---

## Python-Driven Color Classes

Never compare thresholds in templates. The `UnderwritingScore` dataclass exposes properties
that return the correct CSS class:

```python
score.coc_color_class   # → "num-good" | "num-warn" | "num-bad"
score.cap_rate_color_class  # → "num-good" | "num-warn"
score.dscr_color_class  # → "num-good" | "num-bad"
score.grm_color_class   # → "num-good" | "num-warn" | "num-bad"
score.verdict_label     # → "Strong Buy" | "Conditional" | "Pass"
```

Template usage:
```html
<span class="{{ score.coc_color_class }}">{{ score.cash_on_cash }}</span>
```

---

## Form Widgets

Widget base classes in `core/forms.py` auto-apply CSS classes:

- `StyledNumberInput` — applies `form-input num` (tabular-nums)
- `StyledTextInput` — applies `form-input`
- `StyledSelect` — applies `form-input`

No per-field `attrs` in templates. Widgets handle it.

---

## Responsive Breakpoints

| Breakpoint | Changes |
|---|---|
| ≤ 640 px | KPI grid → 2 columns; layout-2col → 1 column; form grids → 1 column; nav links hidden (hamburger visible); page header stacks; `.col-hide-mobile` hidden |
| ≤ 400 px | KPI grid → 1 column |

Rules:
- No `!important` in CSS. If a responsive rule is broken, fix the template or the source order.
- No inline `style=` on layout elements. Exceptions:
  - `table.style.opacity` in dashboard JS (BRRRR zero-ARV guard)
  - `width:score%` in `score_bar.html`
  - PDF export inline styles (`exports/deal_summary.html`)

---

## Dark Mode

The `tokens.css` file includes a `prefers-color-scheme: dark` media query that swaps all
token values. The component CSS uses tokens only — no hardcoded colors — so dark mode
works automatically for every component.

---

## File Locations

| File | Contents |
|---|---|
| `static/css/tokens.css` | All CSS custom properties (tokens) |
| `static/css/base.css` | Component styles, layout, responsive rules |
| `core/forms.py` | Widget base classes (`StyledNumberInput`, etc.) |
| `core/services/scoring.py` | `UnderwritingScore` with color-class properties |
| `templates/components/` | Reusable template partials |
