# Current State — prei

> **Last updated:** 2026-08-20
> **Replaces:** All files in `docs/assessments/archive/` and `docs/planning/PRODUCT_STRATEGY.md` maturity sections.

---

## Executive Summary

prei is a **passive residential real estate investment analytics** platform for buy-and-hold investors. The core workflow spans Growth Areas → Discovery → Screening → Underwriting → Offer → Pipeline CRM → Portfolio → Leasing.

**Test coverage:** 1,981 tests collected (1,952 passing, 29 E2E Playwright tests).
**23 Django models** across pipeline, growth, and sources.

---

## Component Maturity (August 2026)

### ✅ Pipeline CRM Kanban — BETA → GA
| Attribute | Status |
|-----------|--------|
| Model | `PipelineProperty` — 11 stages, 4 statuses, 5 source types |
| Views | List, kanban (drag-drop), detail, advance/kill/hold/reactivate endpoints |
| Templates | Kanban board with drag-and-drop, action dropdown, list view |
| Tests | Unit, integration, E2E (Playwright drag-drop) |
| **Recent work** | Added REST endpoints (advance/kill/hold/reactivate), action dropdown UI, 15 E2E tests |

### ✅ Property Discovery — BETA
| Attribute | Status |
|-----------|--------|
| Sources | VRM, HUD REO, USDA REO, 11 TX county foreclosure scrapers, sheriff sales |
| Views | Discovery page with state selector, AJAX results |
| Tests | 264 pipeline tests + E2E workflow journey |
| **Recent work** | Data health dashboard, circuit breaker, refresh-all with polling, 4 E2E tests |

### ✅ Screening — BETA
| Attribute | Status |
|-----------|--------|
| Logic | 9-criteria screening (4 hard kill, 5 soft) |
| Views | Screener with AJAX filter bar, criteria settings, preview impact |
| Tests | Unit, integration, E2E (filter bar, preview, version history) |
| **Recent work** | AJAX filter bar, preview impact button, auto-version on save, version history display, 3 E2E tests |

### ✅ Underwriting — BETA
| Attribute | Status |
|-----------|--------|
| Code | 40+ KPI functions, v2 scoring, deal comparison view |
| Tests | 58 parametrized edge cases, 5 comparison tests |
| UX | Property report, side-by-side comparison (2-4 properties) |

### ✅ Offer Management — BETA
| Attribute | Status |
|-----------|--------|
| Code | 3 offer strategies, MAO visualization |
| Tests | Offer handler tests included in pipeline suite |

### ✅ Portfolio Tracking — BETA
| Attribute | Status |
|-----------|--------|
| Code | Property model, rental income, operating expense, investment analysis |
| Tests | Property analysis, portfolio aggregation |

### ✅ BRRRR Analysis — BETA
| Attribute | Status |
|-----------|--------|
| Code | Server-side engine + client-side calculator |
| Tests | 25+ BRRRR-specific tests |

### ✅ Leasing Pipeline — BETA
| Attribute | Status |
|-----------|--------|
| Model | `LeasingPipelineProperty` — 8 stages, 3 statuses |
| Views | List, kanban (drag-drop), add, detail, 6 stage-specific forms |
| Tests | Unit, integration, acceptance, BDD |
| **Recent work** | Fully implemented end-to-end (was THIN SHELL in Jul 2026) |

### ✅ Growth Areas — BETA → GA
| Attribute | Status |
|-----------|--------|
| Code | Market scoring, growth area population, Census ACS + FRED |
| Tests | 8 test files, E2E system page |
| **Recent work** | E2E tests for system status page, data health dashboard |

### ✅ Data Health Dashboard — NEW
| Attribute | Status |
|-----------|--------|
| Code | `DataSourceHealth` model, `DataSourceHealthMonitor` |
| Views | System status with refresh-all button, health JSON endpoint |
| Features | Circuit breaker (3-error threshold), retry decorator, live polling |
| Tests | 4 E2E tests |

---

## Remaining Gaps

| Component | Gap | Priority |
|-----------|-----|----------|
| **Growth Areas** | No seeded data on deploy (requires CLI command) | P2 |
| **Discovery** | 6/7 sources still stubs (only VRM, HUD, USDA, counties real) | P2 |
| **Offer** | No competition analysis display | P2 |
| **BRRRR** | No visual projection timeline | P3 |
| **Portfolio** | No time-series charts, no equity dashboard | P2 |

---

## Tech Stack

- **Backend:** Django 6.0, Python 3.14
- **Database:** SQLite (dev), PostgreSQL (prod)
- **Frontend:** Vanilla JS, custom design system (CSS tokens)
- **Testing:** pytest 9.1, Playwright 1.62 (E2E), 1,981 tests
- **CI:** GitHub Actions (lint, typecheck, unit, integration, E2E, ZAP scan)
- **Deploy:** Docker (python:3.14.7-slim-bookworm), Render

---

## Architecture

```
Growth Areas → Discovery → Screening → Underwriting → Offer → Pipeline CRM → Portfolio → Leasing
     ↑              ↑          ↑           ↑           ↑          ↑            ↑          ↑
  Census/FRED    VRM/HUD    9-criteria   40+ KPIs   3 strategies  11 stages   Aggregates  8 stages
  + FRED         /USDA      screening    + v2 score  + MAO       + kanban    + variance   + kanban
                 /Counties                                              + deal compare
```
