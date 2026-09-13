# EXECUTION_QUEUE.md (weeks) — prei

**Horizon**: Weekly sprint | **Owner**: Dev lead (Phil) | **Review**: Weekly

---

## Priority Tiers

### P0 — Blocks Release

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Finance utils consolidation | Done | — | Single-source KPI functions (finance-utils-split PR) |
| CI quality gates (ZAP scan) | Done | — | LIMIT-22 resolved |
| Known limitations triage | Done | — | All active limitations documented |

### P1 — This Sprint

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Investor Workflow Documentation | Done | — | #335 (closed), PR #433, 85 tests passing |
| Growth Areas How-To Guide | Done | — | `docs/how-to-guides/analyze-growth-areas.md` (138 lines) |
| Discovery How-To Guide | Done | — | `docs/how-to-guides/discover-properties.md` (105 lines) |
| Screening How-To Guide | Done | — | `docs/how-to-guides/screen-properties.md` (134 lines) |
| Underwriting How-To Guide | Done | — | `docs/how-to-guides/underwrite-deals.md` (113 lines) |
| UI Patterns Reference | Done | — | `docs/reference/ui-patterns.md` (100 lines) |

### P2 — Next Sprint

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Auth hardening (CSP, SRI, cookies) | Not started | — | LIMIT-23 |
| Sanitized logging helper | Not started | — | LIMIT-03, LIMIT-09 |
| Growth Area consistency fix | Not started | — | LIMIT-08 |

### P3 — Backlog

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Postgres migration | Not started | — | LIMIT-05 |
| Rentcast adapter | Not started | — | LIMIT-11 |
| Celery background tasks | Not started | — | LIMIT-15 |
| Multi-user support | Not started | — | LIMIT-16 |
| Auction alert wiring | Not started | — | LIMIT-13 |

---

## Scope Drift Protection

**Before adding anything to this queue, check against `VISION.md` non-goals:**

- Active stock/REIT trading → NOT in scope
- Commercial property (>4 units) → NOT in scope
- Real-time auction bidding → NOT in scope
- Property management (maintenance, tenant portals) → NOT in scope
- Legal/tax advice → NOT in scope
- Kubernetes / canary deployments → NOT in scope (alpha)
- API reference documentation → NOT in scope (separate surface)

If a request doesn't pass the non-goals check, it's rejected or deferred to post-alpha.

---

## Bottom-Up Feedback

**Learnings from `plan-for-the-day.md` route back here.** After each session:
- Update item statuses in this queue
- Move completed items to `MILESTONES.md` if they're milestone-level
- Flag new blockers discovered during implementation
- Note scope drift attempts and whether they were rejected

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `VISION.md` | Why are we building this? What principles guide us? | ↗ links up |
| `MILESTONES.md` | What milestones are we targeting? | ↗ links up |
| `plan-for-the-day.md` | What are we doing right now? | ↘ links down |
| `CHANGELOG.md` | What has shipped? | parallel |
