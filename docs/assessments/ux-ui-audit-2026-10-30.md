# UX and UI audit, 2026-10-30

**Method.** I ran the seeded container (`seed_market`) and walked the journey (`tests_bdd/test_journey.py`), so the data looked like real use: one property acquired, one failed screening, one lease stabilized. Then I crawled 40 logged-in pages in Chrome at 1280px and 390px. For each page I took a full screenshot and recorded the HTTP status, horizontal overflow, unlabelled inputs, Bootstrap classes, WCAG contrast and touch-target size. I also checked statically every `var(--token)`, `<style>` block, hex colour and component partial against [DESIGN.md](../../DESIGN.md) and [tokens.css](../../static/css/tokens.css).

**Short answer to "is DESIGN.md the source of UI design?"** Partly. `tokens.css` and `base.css` follow it, and the newest screens use it well: dashboard, portfolio, BRRRR and pipeline detail. Older screens never moved over. About 20 templates still use Bootstrap markup, but Bootstrap is not loaded, so those pages render as unstyled browser defaults. Six templates have their own `<style>` blocks. 17 CSS variables are referenced but never defined. The design-system partials are barely used: `kpi_card` in 2 templates, `empty_state` in 2, `form_section` in 0. DESIGN.md is accurate, but nothing enforces it.

---

## 1. Broken or wrong (fix first)

| # | Finding | Evidence | Fix |
|---|---|---|---|
| B1 | **Financing comparison page returns 500.** | `/properties/<id>/financing/`: `TemplateSyntaxError: Invalid filter: 'sub'`. The filter exists in `core/templatetags/math_filters.py`, but the template only does `{% load humanize %}`. | Add `math_filters` to the `{% load %}`. Better: compute the rent cushion in the service and pass it in. A template-level threshold `>=` also breaks DESIGN.md's rule that thresholds live in Python. |
| B2 | **The logo is invisible.** It shows as a white square with a blue shadow. | `.brand-mark` uses `var(--color-grow-600)`, which is undefined. That invalidates the gradient, leaving a white stroke on a white background. The shadow is a hard-coded blue `rgba(37,99,235,.25)`. | Use `var(--color-primary)` as a flat fill and remove the blue shadow. |
| B3 | **The portfolio numbers mislead the investor.** | Total Equity shows **$180,000**, the full list price, for a property closed at **$95,000** with a $131k loan. Monthly Cash Flow shows **$1,800**, which is gross rent with no expenses or debt service. Price shows $180,000, the list price, not the purchase price. Avg GACS shows **0.0** while the matching growth area below scores **7.44**. | Equity = value − loan balance. Cash flow = rent − opex − debt service, using the services that already exist. Show the closing price. Join GACS through the property's market. (Domain fix, needs a spec row.) |
| B4 | **The dashboard verdict contradicts its own metrics.** | 1200 Seed Pass Ln shows **CoC 0.2%** (in green), **cap rate 0.1%**, then **"A · Strong Buy", score 100**. The tile says "Best CoC 0.2%, Target ≥ 8%" in green. | Check the scoring inputs for acquired properties. A 0.2% CoC must not render green or score 100. Colour classes come from `UnderwritingScore`, so the bug is in the data passed in or in the score. |
| B5 | **The same number is formatted three ways.** | Population growth reads `1.00%` on Growth Areas, `0.01%` on Portfolio and `-0.01` (no %) for employment growth. Prices appear as `$95000.00`, `$450,000.00` and `$180,000`. GACS appears as `7.44`, `7.4400` and `7.4`. | Add one set of formatting filters (`money`, `pct`, `score`) and use them everywhere. |
| B6 | **Counts disagree between pages.** | The dashboard says "1 property", but `/properties/` lists 4. | Pick the scope (acquired, or everything tracked), say it in the subtitle, and use it on both pages. |
| B7 | **A route is shadowed.** | `core/urls.py` maps `markets/` twice (lines 26 and 217), so `markets_list` can never be reached. | Delete one route, or move it to its own path. |

## 2. Design system conformance

| # | Finding | Evidence | Fix |
|---|---|---|---|
| D1 | **Bootstrap markup with no Bootstrap loaded** | `row`, `col-md-*`, `card-body`, `form-control`, `d-flex`, `mb-3`, `btn-outline-*` and `badge` match no CSS rule. Worst offenders: `properties/edit.html` (99 hits), `properties/add.html` (96, now superseded), `portfolio.html` (49), `vrm_properties/list.html`, `investment_targets/edit.html`, `hud/usda` lists, `properties/list.html`, `compare.html`, `system.html`, `onboard.html`. Live, these pages show default 13px inputs, unaligned labels and no grid. See Investment Targets and the Properties list. | Migrate each one to `.form-group`, `.form-grid-*`, `.card`, `.table-wrap` and `.data-table`, and drop the `attrs={"class": "form-control"}` in `core/forms.py`. |
| D2 | **17 undefined tokens** | `--color-grow-600`, `--color-grow-5`, `--color-neutral-300/400/600`, `--color-text`, `--color-text-tertiary`, `--color-muted`, `--color-surface`, `--color-success/warning/danger`, `--color-border`, `--radius`, `--shadow-md`, `--surface-primary`, `--weight-semibold`. | Map each one to an existing token. Add a pre-commit check that fails on any `var(--x)` not defined in `tokens.css`. |
| D3 | **Off-palette colours from an older (Tailwind-blue) theme** | `base.css:52, 81, 136` and `pipeline.css:723` use `rgba(37,99,235,…)`: the nav active state, hover and kanban drop zone show a blue tint behind green text (1.5:1). `base.css:454-456` uses `#16a34a` and `rgba(34,197,94,…)` for the confidence chip (1.45:1). `<style>` fallbacks use `#2563eb` and `#e5e7eb`. `theme.css` is a leftover dark-mode and Bootstrap file. | Replace them with `--color-primary-bg`, `--color-grow-50` and `--color-grow-700`. Delete `theme.css`. |
| D4 | **Six templates have their own `<style>` block** | `property_discovery`, `growth_explorer`, `offline`, `properties/financing_comparison`, `markets/dashboard`, `exports/deal_summary` (the last is allowed, as a PDF export). | Move the progress bar, spinner and financing table into `base.css`. |
| D5 | **Design-system partials are underused** | `kpi_card` is used in 2 templates against 8 with hand-written `.kpi-card`. `empty_state` is used in 2, and empty data shows as `—`, an empty table or "No … found" rows. `form_section` is used in 0. Verdicts are hand-written as `Strong Buy · Strong Buy` (duplicated) on `/properties/`. | Adopt the partials. Fix the duplicated verdict label in the properties list. |
| D6 | **Two systems for pipeline screens** | `pipeline.css` has its own `.field-input`, `.verdict-pass/-fail` and stage-badge styles (already recorded in DESIGN.md). The screener's Quick Filters inputs and the kanban's "Discover Properties" panel are unstyled browser controls. | Move them onto the base form classes when those screens are next touched. |
| D7 | **Default link styling inside tables** | Address links on the dashboard, screener and kanban cards render in browser-default blue (`#0000EE`) and underlined. That is the only non-palette blue on those pages. | Add `.data-table a` and `.pipeline-card a` rules using `--color-neutral-900`, underlined on hover. |

## 3. Accessibility (WCAG AA)

| # | Finding | Evidence |
|---|---|---|
| A1 | **White text on primary green is 3.39:1**, below the 4.5:1 AA minimum, on every `.btn-primary` and active chip (already known as L8). | Measured on all 40 pages. |
| A2 | **`neutral-200` (#B4B2A9) is used for body-size text**, at 1.85–2.13:1. | KPI sub-labels ("Target ≥ 8%"), nav dropdown descriptions, footer, system page counts, BRRRR disclosure. |
| A3 | **Other low-contrast text** | The BRRRR timeline "🏗️ Rehab" is white on amber, 2.17:1. The confidence chip is 1.45:1. Active nav text on the blue tint is 1.53:1. |
| A4 | **The focus outline is removed** on `.form-input:focus` (base.css:335) and in `pipeline.css:648`. Keyboard users get only a 1px border colour change. | Use `:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px }`. |
| A5 | **Unlabelled controls**: four screening-settings sliders, the screener's growth-area select and its Min Price / Max Price / Min Yield filters, and the explorer's Tier / State selects (their visible labels are not linked with `for`). | Crawl `unlabelled` output. |
| A6 | **The kanban can only be used by dragging.** There is a `⋮` menu, but it is a 16px target and the columns give no sign that they scroll sideways ("DU…" is cut off at 1280px). | Make sure the card menu offers "Move to…", add a visible horizontal scroll affordance, and use a 24px or larger target. |
| A7 | **Touch targets under 24px**: 16 on `/properties/` and 8 on the kanban (checkboxes, "Details · Edit · Share" text links). | Crawl `smallTargets`. |

## 4. Mobile (390px)

- **Horizontal page scroll** on `/properties/` (557px wide), `/vrm-properties/` (632px), `/hud-properties/` and `/usda-properties/`. These tables are not inside `.table-wrap`, and the Properties table wraps text to one word per line.
- **Growth Areas desktop**: the actions column is clipped ("Discover Pr…", "View Scree…", "Market Indi…"). The table is wider than the content column, and the overflow is hidden instead of scrolling.
- The nav collapses to a hamburger correctly, and the newer screens (dashboard, portfolio, BRRRR, pipeline detail) reflow well.

## 5. Information architecture and journey

The journey in [VISION.md](../../VISION.md) goes identify → discover → screen → underwrite → buy → own → grow. The UI does not show that order.

1. **Too many overlapping property lists.** "Deal screener" (`/dashboard/`), "Screened Properties" (`/pipeline/screener/`), "Properties" (`/properties/`), "Pipeline" (kanban), "Pipeline Dashboard" (`/pipeline/`), the review queue, and the VRM, HUD and USDA lists all list properties. A new user can't tell which one is the source of truth. **Proposal:** Market → Pipeline (one list with a kanban toggle and stage filters) → Portfolio. Fold the source lists into Discovery.
2. **The nav label "Growth Areas" opens the Explorer**, an empty form. The ranked list at `/growth/`, which is journey step 1, has no nav entry, and the nav is not highlighted when you are on it.
3. **Key pages are missing from the nav**: BRRRR, Investment Targets, Properties, Markets and System are reachable only from deep links (9 links in total). Settings needs a home, for example under the avatar menu.
4. **Acquired properties are a dead end.** The pipeline detail page for an acquired property offers no next step. "Add to leasing", "Enter actuals" and "Run BRRRR on this property" all exist but are not linked. Leasing and BRRRR don't know about the property: BRRRR is a standalone calculator that needs the price typed in again.
5. **Anonymous users see the whole nav**, and every link bounces them to the login page. The sign-in page is Django's unstyled `as_p` form, labelled "Login" on a page titled "Sign in", with no product context.
6. **Raw enums and jargon show through**: "Due_Diligence", "for_sale", "Vrm #900001", a duplicated "Acquired Acquired" badge, "Kill" as the delete action, "Landlord —/10", "GACS" with no explanation, and "Conf." Investment Targets labels say "(%)" but expect a fraction (`0.08`).
7. **Empty states**: "Undervalued Listings (CMA)" shows an empty table with headers. The kanban shows "—" in empty columns. Markets shows a single grey line. Each should explain why it's empty and give the next action (the `empty_state` partial already does this).
8. **Forms default to `0` instead of empty placeholders** (Monthly Actuals). A missed field is then saved as $0 rent, which is silent bad data.
9. **Emoji are used inconsistently.** "🚀 Growth Areas" is the only nav item with an icon, and the BRRRR timeline and empty-state icons also use emoji. DESIGN.md doesn't mention icons. Either choose one icon approach (inline SVG like the brand mark) or remove them.

## 6. What's working

- `tokens.css` and `base.css` are a solid, coherent base: warm neutrals, one accent, a 4px spacing scale, tabular figures and self-hosted Inter. The dashboard, portfolio, BRRRR and pipeline detail pages match DESIGN.md closely.
- The type scale is mostly followed: 11/13/15/18/22. Stray sizes come from un-migrated pages (13.33px browser-default controls, 30px Bootstrap-era `h1`s, 17.55px and 22.5px).
- Semantic colour (green, amber, red) is used consistently in verdicts and KPI values, and it is paired with text labels.
- The disclaimer banner on Growth Areas ("weights are a hypothesis") is good, honest product copy.
- No console errors on the 200 pages.

---

## Improvement plan

Ordered by investor impact per unit of effort. Each phase is a set of plan rows and PRs that can ship on its own.

### Phase 1: Trust and breakage (1–2 days)
1. B1: fix the financing page 500 and add a URL smoke test that GETs every named route for the demo user and asserts no 500.
2. B2: fix the logo.
3. B3, B4: correct the portfolio equity, cash flow and price, and the dashboard score for acquired properties. *These are finance bugs: the numbers investors act on are wrong.* They need spec rows and service-layer tests.
4. B5: add `money`, `pct` and `score` template filters and apply them across all templates.
5. B7: remove the shadowed route.

### Phase 2: Enforce DESIGN.md (2–3 days)
1. Add a pre-commit check (a small Python script) that fails on: `var(--x)` not defined in `tokens.css`; hex or `rgb(` in `static/css` outside `tokens.css`; `<style>` in templates other than `exports/`; and a Bootstrap class list (`row`, `col-*`, `form-control`, `card-body`, `d-flex`, `m[tb]-N`, `btn-outline-*`, `badge`). Start with the current violations on an allow-list so it passes today, then shrink the list.
2. D2, D3: map the undefined tokens, replace the blue and Tailwind colours, delete `theme.css`.
3. A1–A4: darken `--color-primary` for fills (use `grow-700` for button backgrounds, or a new 500 step that reaches 4.5:1), stop using `neutral-200` for text (use `neutral-500`), and restore `:focus-visible`. Update DESIGN.md in the same PR.
4. D7: style links in tables and cards.

### Phase 3: Migrate legacy screens (about 1 day per screen group)
In this order: Investment Targets and Screening Settings (the user's own thresholds) → Properties list, edit and compare → the VRM, HUD and USDA lists → System and Onboard → the sign-in page. Each one moves to `.form-group`, `.form-grid-*`, `.table-wrap` and the partials, and comes off the allow-list. Fix A5 and A7 while each page is open.

### Phase 4: Information architecture (needs a human decision, gate `intent`)
1. Nav = **Markets · Pipeline · Portfolio · Leasing**, with Settings under the avatar. Fold the dashboard "Deal screener" and `/properties/` into Pipeline and Portfolio.
2. Make `/growth/` the Markets landing page, with the Explorer as its "Analyze a new state" action.
3. Give the acquired property a next-step bar: Enter actuals · Start leasing · Model BRRRR (pre-filled from the property).
4. Hide the app nav from anonymous users, and style the sign-in page.
5. Write a plain-language pass for labels: no raw enums, "Remove" instead of "Kill", a GACS tooltip, and "%" fields that take percentages.

### Phase 5: Guard against regressions
- Add the crawl used for this audit as a `make ui-check` target. It would fail on any non-200 response, horizontal overflow at 390px, unlabelled inputs, or AA contrast failures on named routes. (It runs Playwright against local Chrome or the container. The script is available on request.)
- Add a screenshot of the main journey pages to PR review for UI changes (REVIEW.md).

Phase 1 B3/B4 and Phase 4 change product behaviour and need spec/plan rows before an agent picks them up. Phases 2, 3 and 5 are conformance work against the existing DESIGN.md and can go straight to the board.
