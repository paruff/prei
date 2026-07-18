# Specification: Remaining UX Issues
# Written: 2026-07-19

---

## 0. Executive Summary

Close the final UX gaps from the Product Maturity matrix: MAO visualization
on the offer form, equity dashboard on the portfolio page, and a seed data
button for growth areas on the system page.

---

## 1. Scope

| Gap | Current | Desired |
|---|---|---|
| Offer Management | Offer form shows numbers but no MAO vs price visual | MAO bar with price indicator |
| Portfolio | Dashboard shows property cards but no equity view | Equity bar per property (loan/value) |
| Growth Areas | Must run CLI to populate growth areas | One-click seed from system page |

---

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-01 | Offer form shows MAO visualization with price comparison | live-system |
| AC-02 | Dashboard shows equity bar per property | live-system |
| AC-03 | System page has "Seed Growth Areas" button | live-system |
