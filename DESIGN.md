---
version: alpha
name: prei
description: Calm, data-dense underwriting UI for buy-and-hold investors. Light mode only. Values mirror static/css/tokens.css.
colors:
  primary: "#1D9E75"
  on-primary: "#FFFFFF"
  secondary: "{colors.neutral-500}"
  neutral: "{colors.surface-page}"
  surface: "{colors.surface-card}"
  on-surface: "{colors.neutral-900}"
  error: "{colors.risk-700}"
  success: "{colors.grow-700}"
  warning: "{colors.caution-700}"
  primary-bg: "#E1F5EE"
  primary-text: "#0F6E56"
  grow-50: "#E1F5EE"
  grow-100: "#9FE1CB"
  grow-400: "#1D9E75"
  grow-700: "#0F6E56"
  grow-900: "#04342C"
  caution-50: "#FAEEDA"
  caution-100: "#FAC775"
  caution-400: "#EF9F27"
  caution-700: "#854F0B"
  risk-50: "#FCEBEB"
  risk-100: "#F7C1C1"
  risk-400: "#E24B4A"
  risk-700: "#A32D2D"
  neutral-50: "#F1EFE8"
  neutral-100: "#D3D1C7"
  neutral-200: "#B4B2A9"
  neutral-500: "#5F5E5A"
  neutral-700: "#444441"
  neutral-900: "#2C2C2A"
  info-400: "#3B7EC4"
  accent-400: "#8B5CF0"
  surface-page: "#F8F8F6"
  surface-card: "#FFFFFF"
  surface-secondary: "#F1EFE8"
  border: "#E0DED6"
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: 500
    lineHeight: 1.2
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 500
    lineHeight: 1.6
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.6
  title-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: 500
    lineHeight: 1.6
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.6
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1.6
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.6
  caption:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.6
  kpi-value:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: 500
    lineHeight: 1
    fontFeature: '"tnum"'
rounded:
  sm: 6px
  md: 8px
  lg: 12px
  pill: 20px
spacing:
  sp-1: 4px
  sp-2: 8px
  sp-3: 12px
  sp-4: 16px
  sp-5: 20px
  sp-6: 24px
  sp-8: 32px
  page-max-width: 1100px
  nav-height: 52px
components:
  button:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.neutral-900}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 7px 16px
  button-hover:
    backgroundColor: "{colors.surface-secondary}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 7px 16px
  button-primary-hover:
    backgroundColor: "{colors.grow-700}"
  button-danger:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.risk-700}"
    rounded: "{rounded.md}"
  button-danger-hover:
    backgroundColor: "{colors.risk-50}"
  card:
    backgroundColor: "{colors.surface-card}"
    rounded: "{rounded.lg}"
    padding: 20px
  kpi-card:
    backgroundColor: "{colors.surface-secondary}"
    rounded: "{rounded.md}"
    padding: 16px
  input:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.neutral-900}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 7px 12px
  chip:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.neutral-500}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 4px 10px
  chip-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  verdict-a:
    backgroundColor: "{colors.grow-50}"
    textColor: "{colors.grow-700}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 3px 8px
  verdict-b:
    backgroundColor: "{colors.caution-50}"
    textColor: "{colors.caution-700}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 3px 8px
  verdict-c:
    backgroundColor: "{colors.risk-50}"
    textColor: "{colors.risk-700}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 3px 8px
  verdict-moderate:
    backgroundColor: "{colors.primary-bg}"
    textColor: "{colors.primary-text}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
    padding: 3px 8px
  table-header:
    textColor: "{colors.neutral-500}"
    typography: "{typography.label-sm}"
    padding: 8px 12px
  table-cell:
    textColor: "{colors.neutral-900}"
    typography: "{typography.body-md}"
    padding: 12px
---

# prei design system

> Read this before any UI change ([AGENTS.md](AGENTS.md)). The tokens above mirror [`static/css/tokens.css`](static/css/tokens.css), which is what the browser actually loads. If the two disagree, `tokens.css` wins and this file is fixed in the same PR. Component CSS lives in [`static/css/base.css`](static/css/base.css) and [`static/css/pipeline.css`](static/css/pipeline.css); reusable partials in [`templates/components/`](templates/components/).

## Overview

prei is a decision tool for buy-and-hold residential investors, not a marketing site. The UI is calm, flat and data-dense: warm off-white pages, white cards, thin warm-grey borders, and one green accent. Colour carries meaning: green for good or strong, amber for caution, red for risk. Numbers are the content, so they get tabular figures and room to breathe. Copy is practical and jargon-light (see [VISION.md](VISION.md) principles 6 and 7).

Light mode only; there is no dark theme today. Density: high (KPI grids, tables). Motion: minimal, 0.1–0.2s colour and border transitions, no entrance animations.

## Colors

- **Roles:** `primary` (grow green), `secondary` (warm slate `neutral-500`, labels and metadata), `neutral` (page `#F8F8F6`), `surface` (card white), `on-surface` (ink `neutral-900`), `error` / `warning` / `success` (the 700 steps of risk, caution, grow). The palette names below mirror `tokens.css`.
- **Grow green (`primary`, #1D9E75):** the only action colour, used for primary buttons, active chips, focus borders and the "moderate" verdict. Its 50 and 700 steps (`primary-bg`, `primary-text`) give tinted backgrounds and readable text.
- **Grow, caution and risk scales:** semantic only, meaning good, warning and bad metrics. Use the 50 step for backgrounds and the 700 step for text. Verdict badges A, B and C map to grow, caution and risk.
- **Warm neutrals (#F1EFE8 to #2C2C2A):** body text is `neutral-900`, labels and secondary text are `neutral-500`.
- **Surfaces:** page `#F8F8F6`, card `#FFFFFF`, secondary `#F1EFE8` (KPI tiles, hover). Borders are `#E0DED6`: 1px by default, 0.5px for subtle dividers.
- **Info blue (#3B7EC4) and accent violet (#8B5CF0):** defined but rarely used. Don't introduce new uses without updating this file.

Metric colour classes (`num-good`, `num-warn`, `num-bad`) come from Python (`UnderwritingScore.*_color_class` in `core/services/scoring.py`), never from template comparisons.

## Typography

One family, **Inter**, loaded from Google Fonts at weights 400 and 500 only. Seven-step scale: 11 / 13 / 15 / 18 / 22 px.

- **Page title (`headline-lg`):** 22px medium, tight line height. Section headings (`headline-md`): 18px medium.
- **Body (`body-md`):** 15px regular, line height 1.6. Card titles (`title-md`): 15px medium.
- **Labels, buttons and inputs:** 13px (medium for labels and buttons).
- **Captions, table headers and badges:** 11px.
- **KPI values:** 22px medium with tabular figures. All numeric table cells and `.num` inputs use tabular figures too.

`--font-mono` (JetBrains Mono) is defined in `tokens.css` but unused and not loaded. Don't start using it without loading the font.

## Layout

- 4px base spacing scale: `sp-1` (4) to `sp-8` (32). There is no `sp-7`.
- Content column max 1100px, centred, 24px side padding. Sticky top nav, 52px high.
- Grids: `.kpi-grid`, `.layout-2col`, `.layout-sidebar-main`, and form grids `.form-grid-2`, `-3`, `-2-1`, `-2-1-1`.
- Breakpoints: **≤ 640px** (KPI grid to 2 columns, two-column layouts and form grids to 1, nav collapses to the hamburger menu, `.col-hide-mobile` hidden) and **≤ 400px** (KPI grid to 1 column).

## Elevation & Depth

Flat. Hierarchy comes from tonal layers (page, then card, then secondary surface) and 1px borders, not shadows. The top nav is translucent white with a 12px backdrop blur. Shadows appear only on floating or dragged elements (kanban card hover and drag, menus, modals), and there is no shadow token yet.

## Shapes

Soft but not round. Cards use 12px corners, buttons, inputs and KPI tiles 8px, small elements 6px. Chips and verdict badges are pills (20px). Score bars are 4px high with 2px corners.

## Components

Use the existing class or partial. Don't restyle it per page.

- **Buttons:** `.btn` (white, bordered), `.btn-primary` (green fill, white text), `.btn-danger` (red text, light red border). 13px medium, 8px radius.
- **Cards:** `.card` with an optional `.card-title` (15px medium, subtle bottom border).
- **KPI grid:** `.kpi-grid` > `.kpi-card` with `.kpi-label`, `.kpi-value`, `.kpi-sub`, or the `components/kpi_card.html` partial.
- **Verdict badge:** always `{% include "components/verdict_badge.html" %}`, never hand-written markup.
- **Score bar, empty state, form section:** use the partials in `templates/components/`.
- **Forms:** `.form-group` > `.form-label`, `.form-input`, `.form-hint`, `.form-error`. Widgets in `core/forms.py` apply the classes, so there are no per-field `attrs` in templates.
- **Tables:** `.table-wrap` > `.data-table`. Right-align numbers with `.col-right`.
- **Tabs:** `.tab-bar` > `.tab-btn.is-active`. Switch panels with the `hidden` attribute, not `style.display`.
- **Chips:** `.chip` / `.chip.is-active` inside `.chip-group`, used for filters.
- **Messages and banners:** `.message-success`, `-warning`, `-error`, and `.brrrr-banner` with `.is-full-cycle`, `.is-partial` or `.is-trap`.
- **Pipeline screens** (`pipeline.css`): kanban board, pipeline cards and stage badges. They currently use their own form classes (`.field-input`, `.input-sm`) and verdict classes (`.verdict-pass`, `.verdict-fail`). New screens use the base classes above.

## Do's and Don'ts

- Do use `var(--token)` from `tokens.css` for every colour, size, space and radius.
- Do keep colour semantic: green means good, amber caution, red risk. Never use colour as the only signal; pair it with a label or verdict text.
- Do maintain WCAG AA contrast (4.5:1 for body text).
- Do put threshold logic in Python and pass the CSS class to the template.
- Don't use Bootstrap classes, inline `style=` on layout elements, hex colours in templates (the PDF export is the exception), or `!important` ([AGENTS.md](AGENTS.md) "Never Do").
- Don't add a dark mode, new fonts, new weights (only 400 and 500 are loaded) or new colours without updating this file in the same PR.
- Don't copy the current exceptions. Known deviations from this file (undefined tokens, off-palette `.chip-success`, `-info`, `-warning`, `-danger` colours, Bootstrap leftovers, hex in two templates, the removed focus outline on inputs, and white-on-primary text at 3.39:1 on `.btn-primary` and `.chip.is-active`, which fails AA) are being fixed in the "Fix design-system drift" issue (not yet created; `scripts/setup-project-board.sh` creates it).
