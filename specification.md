# Specification: P0 — CRM Kanban + Data Health
# Written: 2026-07-19
# Status: Draft for feature-flow implementation

---

## 0. Executive Summary

Two P0 items from the DEVEX_PLAN: a drag-and-drop CRM kanban board for the
acquisition pipeline, and a data source health dashboard so users know which
property scrapers are working.

---

## 1. Problem Statement

### P0-A: Pipeline Kanban

**Current:** List page with status filter and stage counts in a funnel header.
No visual board, no drag-and-drop, no stage transition validation.

**Desired:** Drag-and-drop kanban board with columns per stage, deal cards with
key info (address, price, days in stage), drag to transition stages, backend
validation of stage rules.

### P0-B: Data Source Health

**Current:** System page shows record counts. No per-source health: last run
timestamp, success/failure state, error messages.

**Desired:** System page shows a health table per data source with: source name,
last run time, record count, success/error status, and a refresh button.

---

## 2. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | Kanban board with columns: Discovered, Screening, Underwriting, Offer, Due Diligence, Closing | P0 |
| F-02 | Deal cards show: address, price, days in current stage | P0 |
| F-03 | Drag-and-drop with backend API for stage transition | P0 |
| F-04 | Stage transition validation: forward-only, no skipping | P0 |
| F-05 | Data source health table on system page | P0 |
| F-06 | Per-source: last run timestamp, record count, status (ok/error) | P0 |

---

## 3. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | Kanban board renders at /pipeline/kanban/ with 6 stage columns | live-system |
| AC-02 | Dragging a card to a new column posts to stage transition API | live-system |
| AC-03 | Forward-only rule enforced (can't drag backward or skip stages) | unit |
| AC-04 | System status page shows data source health table | live-system |
| AC-05 | Each source shows last_run, record_count, and status | unit |
| AC-06 | Refresh button triggers data source reload | live-system |
