# Specification: Missing Acceptance Tests
# Written: 2026-07-19

---

## 0. Executive Summary

Every component in the Product Maturity matrix is missing automated acceptance
tests. Add httpx-based HTTP tests for all components with live-system endpoints.

---

## 1. Scope

| Component | Tests | Priority |
|---|---|---|
| Growth Areas | API response structure + system page | P0 |
| Pipeline | List, kanban, screener views | P0 |
| Portfolio | Dashboard view | P1 |
| BRRRR | Calculator page | P1 |
| Leasing | List, kanban views | P1 |
| Underwriting | Property report view | P1 |

---

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | Growth areas API returns valid JSON structure | live-system |
| AC-02 | Pipeline list renders with stage counts | live-system |
| AC-03 | Pipeline kanban renders with stage columns | live-system |
| AC-04 | Screener page renders with filter bar | live-system |
| AC-05 | Dashboard renders with property cards | live-system |
| AC-06 | BRRRR calculator page loads | live-system |
| AC-07 | Leasing list renders | live-system |
| AC-08 | Leasing kanban renders with columns | live-system |
