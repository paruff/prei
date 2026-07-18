# Specification: Growth Explorer — Tier Filter + Multi-State Analysis
# Written: 2026-07-19

---

## 0. Problem

Growth explorer requires picking one state at a time. Users want to see top markets
across landlord-friendly states (or all states) in one view.

## 1. Requirements

- Support `tier` parameter: `landlord_friendly`, `mixed`, `tenant_friendly`
- When tier is selected, analyze all states in that tier (limit 5 cities per state for performance)
- When state is empty and no tier, analyze all 50 states
- Results sorted by composite score across all analyzed states
- Max 50 results displayed

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | Selecting "Landlord-friendly" tier analyzes TX, FL, IN, TN, GA, AL, AZ, AR, LA, ID, MS, SC, KY, OK, WV, WY | unit |
| AC-02 | Results sorted by composite score across all analyzed states | unit |
