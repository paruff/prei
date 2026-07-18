# Design: P1 — Screening UX + Leasing Kanban
# Written: 2026-07-19

---

## 1. Screening Filter Bar

Add a filter bar above the screener results table:

```html
<div class="screener-filters">
  <input type="number" name="price_min" placeholder="Min Price">
  <input type="number" name="price_max" placeholder="Max Price">
  <input type="number" name="rent_min" placeholder="Min Rent">
  <input type="number" name="cap_rate_min" placeholder="Min Cap Rate %">
  <button type="submit">Filter</button>
</div>
```

Modify the view to accept query params: `price_min`, `price_max`, `rent_min`,
`cap_rate_min`, `sort`, `order`. Filter the queryset before rendering.

## 2. Sortable Columns

Add clickable column headers with sort direction indicators:

```html
<th><a href="?sort=price&order=asc">Price ↑↓</a></th>
<th><a href="?sort=cap_rate&order=desc">Cap Rate ↑↓</a></th>
```

Server-side sorting via queryset `.order_by()`.

## 3. Leasing Kanban

The leasing kanban view (`leasing_kanban`) already handles POST with
`property_id` + `new_stage` parameters. The template already has drag-drop JS.
Verify the JS sends the correct parameters and the endpoint is correct.

## 4. File Changes

| File | Change | Purpose |
|---|---|---|
| `templates/pipeline/screener.html` | Modified | Add filter bar + sortable headers |
| `core/views/__init__.py` | Modified | Add query param filtering to screener view |
| `templates/leasing/leasing_kanban.html` | Modified | Verify JS params match backend |