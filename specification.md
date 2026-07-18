# Specification: UX Maturity Gaps
# Written: 2026-07-19

---

## 0. Executive Summary

Three UX gaps from the July 2026 Product Maturity matrix: growth area dashboard
on the system page, property comparison view for underwriting, and BRRRR
projection timeline.

---

## 1. Problem Statement

**Gap 1 — Growth Areas Dashboard:** System page shows counts but no per-area
details (scores, cities, states). Users can't see which areas are high-scoring.

**Gap 2 — Underwriting Comparison:** No side-by-side view to compare two
properties' KPIs. Users manually switch tabs to compare.

**Gap 3 — BRRRR Timeline:** Calculator gives numbers but no visual timeline
showing when refinance happens and equity builds over time.

---

## 2. Requirements

| ID | Description | Priority |
|---|---|---|
| F-01 | System page shows growth areas table: city, state, composite score, landlord score | P0 |
| F-02 | Property comparison view: select two properties, side-by-side KPI display | P1 |
| F-03 | BRRRR calculator shows simple visual timeline (cash flow bars) | P1 |

---

## 3. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | System page renders growth areas table with ≥5 rows when populated | live-system |
| AC-02 | Comparison page shows NOI, cap rate, cash-on-cash, DSCR for both properties | live-system |
| AC-03 | BRRRR page shows visual timeline with at least 3 phases | live-system |
