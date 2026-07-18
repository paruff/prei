# Specification: Growth Area Settings & Data Health
# Written: 2026-07-19

---

## 0. Executive Summary

Add a settings/health section for growth areas showing API key status,
data quality indicators, and what's needed for growth areas to work
correctly.

---

## 1. Problem Statement

**Current:** System page shows growth area count and FIPS coverage percentage.
No visibility into whether the required API keys are configured, or whether
the underlying data sources are returning good data.

**Desired:** A growth area settings section showing:
- Which API keys are configured (FRED, HUD, ATTOM)
- Growth area data health (count, states covered, last updated)
- Whether the data pipeline is working correctly

---

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | System page shows API key status for FRED, HUD, ATTOM | live-system |
| AC-02 | Shows growth area data health: count, states, last seeded | live-system |
| AC-03 | Key status shows ✓ (configured) or ✗ (missing) | live-system |
