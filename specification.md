# Specification: P1 — Screening UX + Leasing Kanban
# Written: 2026-07-19
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

P1 addresses two gaps: screening needs batch filter/sort controls so users can
quickly kill 90% of deals, and the leasing kanban needs JS wiring verification
(it has backend code but the drag-drop fetch may have the same parameter mismatch
we fixed in the pipeline kanban).

---

## 1. Problem Statement

### P1-S: Screening Batch UX

**Current:** Screener page shows a list of properties with KPI summary. No inline
filtering, sorting, or batch actions. Users must scroll through all properties.

**Desired:** Filter bar with price range, rent range, cap rate min, location search.
Sortable columns by price, cap rate, GRM, score. Results update without page reload.

### P1-L: Leasing Kanban Wiring

**Current:** Full backend (views, models, stage validation) and template
(drag-drop, columns, styling). Likely the JS fetch uses the same `new_stage` /
`property_id` parameters that work.

**Desired:** Verify kanban drag-drop works end-to-end. Fix parameter names if
needed (match with `property_id` + `new_stage` similar to pipeline kanban fix).

---

## 2. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | Screener page has filter bar: price min/max, rent min, cap rate min | P0 |
| F-02 | Results sortable by price, cap rate, GRM, score (header click) | P0 |
| F-03 | Leasing kanban drag-drop posts to correct endpoint with correct params | P0 |
| F-04 | Leasing stage transitions validated (forward-only, no skipping) | P0 |

---

## 3. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | Screener page has filter inputs for price, rent, cap rate | live-system |
| AC-02 | Clicking column header sorts results ascending/descending | live-system |
| AC-03 | Leasing kanban loads with 8 stage columns | live-system |
| AC-04 | Dragging card to next stage persists via POST | live-system |
| AC-05 | Backward/forward drag validation returns error | unit |
