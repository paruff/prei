# EXECUTION_QUEUE.md (weeks) — prei

**Horizon**: Weekly sprint | **Owner**: Dev lead (Phil) | **Review**: Weekly

---

## Priority Tiers

### P0 — Blocks Beta Release

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Rentcast spike (API key, coverage test) | Not started | — | **Do first** — unblocks M2.2 |
| Postgres + Redis docker-compose | Not started | — | **Do in parallel** — foundation for Celery |
| FBI CDE retry | Not started | — | Try correct endpoint before fallbacks |

### P1 — This Sprint (H2A)

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Rentcast adapter + fallback chain | Not started | Rentcast spike | `core/integrations/sources/rentcast_adapter.py` |
| ATTOM rent probe | Not started | — | Extend `attom_adapter.py` |
| GACS backtest script | Not started | — | `scripts/backtest_gacs.py`; FHFA/Zillow data |
| GACS signal completion (schools, supply, employment) | Not started | — | GreatSchools key; Census permits |

### P2 — Next Sprint (H2B)

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Crime adapter (FBI retry → SpotCrime) | Not started | FBI CDE retry | `core/integrations/market/crime.py` |
| Postgres migration + docker-compose | Not started | — | Remove LIMIT-05 |
| Celery + Redis | Not started | Postgres/Redis | Async screening, discovery, VRM |
| Team model + shared pipeline | Not started | Postgres | Team, TeamMembership, PipelineProperty.team |

### P3 — Following Sprint (H2C)

| Item | Status | Depends On | Notes |
|---|---|---|---|
| django-csp + CSP headers | Not started | — | CSP, Permissions-Policy, CORP |
| SRI on external scripts | Not started | — | `base.html` integrity attrs |
| ZAP clean pass | Not started | CSP headers | Authenticated scan: 0 FAIL, 0 WARN |

### P4 — Backlog (H3)

| Item | Status | Depends On | Notes |
|---|---|---|---|
| Portfolio analytics | Not started | — | LIMIT-14 |
| Leasing pipeline | Not started | — | LIMIT-14 |
| Advanced market intelligence | Not started | GACS validated | Rent trends, absorption |
| Partner API surface | Not started | Multi-user | Read-only deal sharing |

---

## Scope Drift Protection

**Before adding anything to this queue, check against `VISION.md` non-goals:**

- Active stock/REIT trading → NOT in scope
- Commercial property (>4 units) → NOT in scope
- Real-time auction bidding → NOT in scope
- Property management (maintenance, tenant portals) → NOT in scope
- Legal/tax advice → NOT in scope
- Kubernetes / canary deployments → NOT in scope (post-beta only)
- API reference documentation → NOT in scope (separate surface)
- MLS/RESO integration → NOT in scope
- 1031 exchange tracking → NOT in scope

If a request doesn't pass the non-goals check, it's rejected or deferred to post-beta.

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
