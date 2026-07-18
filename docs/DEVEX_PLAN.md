# Development Plan — July 2026

> Priority: P0 items first, then work through acceptance tests for all 9 components.

---

## P0 — Acquisition Pipeline (CRM Kanban Board)

**Current:** List page with status filter. No drag-and-drop, no visual pipeline.
**Target:** Drag-and-drop kanban board with stage transitions, status badges, deal counts per stage.

### Tasks

| # | Task | Type |
|---|---|---|
| P0-01 | Add kanban board template: columns per stage, deal cards with drag handles | UX |
| P0-02 | Add JavaScript drag-and-drop (SortableJS or vanilla) with POST to stage transition API | UX |
| P0-03 | Add stage transition API endpoint (`POST /pipeline/<id>/transition/`) | Backend |
| P0-04 | Add stage transition validation (rules: can't skip stages, can't go backward) | Backend |
| P0-05 | Add acceptance tests: create deal → drag to screening → drag to underwriting → verify stage | test_type: live-system |
| P0-06 | Add UX review: test kanban on mobile, check accessibility, verify keyboard navigation | UX review |

---

## P0 — Property Discovery (Data Health Dashboard)

**Current:** Scrapers run in background threads. No visibility into what data sources are working.
**Target:** System status page shows per-source health: last run, records fetched, error state.

### Tasks

| # | Task | Type |
|---|---|---|
| D-01 | Add data source health model: source name, last run, record count, error message | Backend |
| D-02 | Update system status page with data source health table | UX |
| D-03 | Add "Refresh All Sources" button with progress indicators | UX |
| D-04 | Add acceptance tests: load system page → verify data source table → trigger refresh → verify updates | test_type: live-system |
| D-05 | Fix scraper reliability: add timeouts, retries, circuit breaker for failing sources | Backend |

---

## P1 — Screening UX (Batch Filtering)

**Current:** Single property view. No batch filtering or comparison.
**Target:** Filter bar with price, rent, cap rate, location filters. Sortable results grid.

---

## P1 — Leasing Pipeline (Backend Wiring)

**Current:** Kanban template exists (HTML/CSS) but is read-only.
**Target:** Functional drag-and-drop kanban with backend stage transitions.

---

## P2 — Acceptance Tests (All Components)

After UX work is done on each component, add automated acceptance tests:

| Component | Test scope |
|---|---|
| Growth Areas | Verify system page data dashboard, growth area population, API response structure |
| Property Discovery | Verify data source health, scraper results, discovery page search |
| Screening | Verify filter/sort UX, batch screening results, criteria validation |
| Underwriting | Verify KPI report page, comparison view, market cap rate display |
| Offer Management | Verify MAO calculation, offer form submission, competition display |
| Pipeline | Verify kanban drag-drop, stage transition validation, deal counts |
| Portfolio | Verify dashboard KPIs, property detail view, time-series data |
| BRRRR | Verify calculator inputs, projection results, equity timeline |
| Leasing | Verify kanban stage transitions, tenant screening form, lease creation |

---

## Session Plan

Each session follows this flow:

```
1. Pull latest main
2. Create feature branch: feat/<component>-<task>
3. Work through tasks (UX → backend → acceptance tests → UX review)
4. Run pre-commit + tests
5. Push + open PR
6. Merge after CI passes + human review
```

### Session Log

| Date | Session | Branch | Status |
|---|---|---|---|
| 2026-07-18 | Docs audit + plans | feat/gitops-phase3-hardening | ✅ Merged |
| - | TODO: P0-01 Kanban board | feat/pipeline-kanban | ⬜ Next |
| - | TODO: D-01 Data health | feat/discovery-health | ⬜ |
