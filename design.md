# Design: UX Maturity Gaps
# Written: 2026-07-19

---

## 1. Growth Areas Dashboard

Add a table to `system.html` showing all growth areas with key metrics:

```
| City, State | Composite Score | Landlord Score | Emp Growth | Pop Growth |
| Austin, TX  | 0.8523          | 8.5/10         | 3.2%       | 2.1%       |
```

Query `GrowthArea.objects.all().order_by("-composite_score")[:10]` in the view.

## 2. Underwriting Comparison

New URL: `/property/compare/?a=<id>&b=<id>`

Render a side-by-side card layout:

```
┌──────────────┐ ┌──────────────┐
│ Property A   │ │ Property B   │
│ NOI: $12,000 │ │ NOI: $8,400  │
│ Cap: 6.0%    │ │ Cap: 4.2%    │
│ CoC: 12.0%   │ │ CoC: 8.4%    │
│ DSCR: 1.25   │ │ DSCR: 0.90   │
└──────────────┘ └──────────────┘
```

## 3. BRRRR Timeline

Add a CSS-only visual timeline below the calculator results. Colored bars showing:

```
│████████████████████████████████│  Rehab (3 mo)
│████████████│  Rent-up (1 mo)
│████████████████████████████████████████████████████████│  Hold (24 mo → refinance)
│████████████████████████████████│  Post-refi cash flow
```

## 4. File Changes

| File | Change |
|---|---|
| `core/views/__init__.py` | Add comparison view, update system_status |
| `core/urls.py` | Add /property/compare/ URL |
| `templates/system.html` | Add growth areas table |
| `templates/property_compare.html` | New comparison template |
| `templates/brrrr_calculator.html` | Add CSS timeline |