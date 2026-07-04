# CI Diagnosis

**PR:** #196 — Phase B: GrowthArea Population, SQLite Default, ATTOM comps fix  
**Branch:** `feature/tasks-a`  
**Date:** 2026-07-03

---

## Failure Inventory

### Failure 1: `test_refresh_market_snapshot_comps_fails_logged`
| Field | Value |
|-------|-------|
| **Job** | `test-and-lint` / `Tier 1 — Tests` |
| **Location** | `core/services/market_data.py:179` |
| **Evidence** | `Exception: comps unavailable` — `get_comps_for_listing` raises inside `except` handler without its own `try/except` |
| **Likely Cause** | Line 179 calls `get_comps_for_listing(listing)` inside the `except Exception:` block on line 173. When the fallback raises, the exception propagates uncaught. |
| **Confidence** | HIGH |
| **Classification** | Code Failure |

### Failure 2: Ruff format check
| Field | Value |
|-------|-------|
| **Job** | `Tier 1 — Lint` |
| **Location** | `core/tests/test_neighborhood_insights.py`, `core/tests/test_finance_utils.py`, `tests/test_container_startup.py` |
| **Evidence** | `3 files would be reformatted, 161 files already formatted` |
| **Likely Cause** | `ruff format --check` failed because these 3 files have formatting issues. `test_neighborhood_insights.py` was modified in this PR; the other 2 are pre-existing. |
| **Confidence** | HIGH |
| **Classification** | Code Failure |

### Failure 3: GitGuardian / CodeQL
| Field | Value |
|-------|-------|
| **Job** | GitGuardian Security Checks / CodeQL |
| **Likely Cause** | `.agents/logs/2026-07-03.jsonl` contains CI-related data that may trigger false positives. |
| **Confidence** | LOW — need to investigate |
| **Classification** | Unclassifiable (needs more info) |

---

## Proposed Fixes

### Fix 1: `market_data.py:179` — wrap comps fallback in try/except
```python
except Exception:
    logger.error(...)
    try:
        comps = get_comps_for_listing(listing)
    except Exception:
        logger.error("Comps fallback also failed for zip=%s", zip_code)
        comps = []
```

### Fix 2: Run `ruff format` on the 3 failing files
```bash
ruff format core/tests/test_neighborhood_insights.py core/tests/test_finance_utils.py tests/test_container_startup.py
```

### Fix 3: Investigate GitGuardian/CodeQL — may need to add `.agents/logs/` to `.gitignore` or superseed false positives.
