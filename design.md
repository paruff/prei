# Design: Market Data API Integrations

## 1. Architecture Overview

Three stateless adapter functions inside `core/integrations/market/`. No new models, views, services, or settings. Each adapter accepts identifying parameters + `api_key`, returns a typed result or `None`, uses Django cache, and logs warnings on failure without raising.

```
┌─────────────────────────────────────────────────────────┐
│                   Caller (view / service / command)      │
│  Reads api_key from os.environ, passes to adapter        │
└────────────┬──────────────────────┬──────────────────────┘
             │                      │
    ┌────────▼────────┐   ┌─────────▼─────────┐
    │   fetch_rent_   │   │  fetch_school_     │
    │   estimate()    │   │  rating()          │
    │   (rents.py)    │   │  (schools.py)      │
    │   P1 — modified │   │  P2 — modified     │
    └────────┬────────┘   └─────────┬──────────┘
             │                      │
    ┌────────▼──────────────────────▼──────────┐
    │   fetch_walk_score()  (walkscore.py — P3) │
    │   New file, no migration from stub        │
    └────────────────┬──────────────────────────┘
                     │
                     ▼
          ┌──────────────────┐
          │  django.core.    │
          │  cache           │
          └──────────────────┘
```

**Constraints:**
- All adapters are pure functions (no class state, no DI).
- No new dependencies (`requests`, `logging`, `hashlib`, `decimal`, `django.core.cache` are all present).
- Money/ratings are `Decimal`, never `float`.
- The existing stub functions (`get_rent_estimate_for_listing`, `get_school_rating`) remain untouched for backward compatibility.

---

## 2. Component Design

### 2.1 RentCast Adapter — `core/integrations/market/rents.py` (P1, modified)

**Existing file:** 11 lines. Contains `get_rent_estimate_for_listing(listing) -> Decimal` (heuristic: PPSF × 0.9). This function is imported by `core/tests/test_neighborhood_insights.py`, `core/services/market_data.py`, and the `get_comps_for_listing` chain. **Keep it as-is** — it becomes the fallback.

**Addition:** New function `fetch_rent_estimate`.

```python
RENTCAST_API_BASE = "https://api.rentcast.io/v1/rent/long-term"
RENTCAST_CACHE_TTL = 604800       # 7 days
RENTCAST_DAILY_BUDGET = 100        # free tier limit

def fetch_rent_estimate(
    address: str,
    api_key: str,
    zip_code: str | None = None,
) -> Decimal | None
```

**Cache:**
- Key: `rentcast_rent_{md5(address)}`
- TTL: 604800s (7 days)
- Module: `from django.core.cache import cache`

**Budget guard (RentCast-only):**
- Key: `rentcast_calls_{YYYY-MM-DD}`
- On each call, `cache.get_or_set(counter_key, 0, timeout=86400)`. If >= 100, log warning, return `None`.
- Increment counter on successful API response (not on cache hit).

**Error handling:**
- Empty `api_key` → return `None`, no HTTP call.
- `requests.RequestException` → log warning, return `None`.
- `json.JSONDecodeError` → log warning, return `None`.
- Missing `data.rent` key → log warning, return `None`.
- Budget exceeded → log warning, return `None`.

**Fallback mechanism:** When `fetch_rent_estimate` returns `None`, the caller (e.g. `market_data.py` service) can call `get_rent_estimate_for_listing` for the heuristic fallback. This is the caller's decision — the adapter doesn't internally chain.

### 2.2 GreatSchools Adapter — `core/integrations/market/schools.py` (P2, modified)

**Existing file:** 12 lines. Contains `get_school_rating(zip_code, city, state) -> Decimal` (hardcoded state-based values). Imported by `test_neighborhood_insights.py` and `market_data.py`. **Keep as-is.**

**Addition:** New function `fetch_school_rating`.

```python
GREATSCHOOLS_API_BASE = "https://api.greatschools.org/schools/nearby"
GREATSCHOOLS_CACHE_TTL = 2592000    # 30 days

def fetch_school_rating(
    zip_code: str,
    api_key: str,
) -> Decimal | None
```

**Cache:**
- Key: `greatschools_rating_{zip_code}`
- TTL: 2592000s (30 days)

**Error handling:**
- Empty `api_key` → return `None`, no HTTP call.
- `requests.RequestException` → log warning, return `None`.
- `json.JSONDecodeError` → log warning, return `None`.
- Empty response list → return `None`.
- Missing `gsRating` in any entry → skip that entry.

**No budget guard.**

### 2.3 Walk Score Adapter — `core/integrations/market/walkscore.py` (P3, new)

```python
WALKSCORE_API_BASE = "https://api.walkscore.com/score"
WALKSCORE_CACHE_TTL = 2592000       # 30 days

def fetch_walk_score(
    address: str,
    api_key: str,
) -> dict | None
```

Returns `{"walk_score": int, "transit_score": int | None, "bike_score": int | None}`.

**Cache:**
- Key: `walkscore_{md5(address)}`
- TTL: 2592000s (30 days)

**Error handling:**
- Empty `api_key` → return `None`, no HTTP call.
- `requests.RequestException` → log warning, return `None`.
- `json.JSONDecodeError` → log warning, return `None`.
- Missing `walkscore` key → return `None`.
- `transit.score` and `bike.score` are optional → default to `None`.

**No budget guard.**

---

## 3. Migration Approach for Existing Stubs

### rents.py

| Symbol | Action |
|---|---|
| `get_rent_estimate_for_listing(listing)` | **Keep unchanged.** Used by `market_data.py`, `test_neighborhood_insights.py`, and comps chain. |
| `fetch_rent_estimate(address, api_key, zip_code)` | **Add new.** Live API call with caching and budget guard. |

The service layer (`core/services/market_data.py`) will be updated separately to try `fetch_rent_estimate` first, falling back to `get_rent_estimate_for_listing` on `None`.

### schools.py

| Symbol | Action |
|---|---|
| `get_school_rating(zip_code, city, state)` | **Keep unchanged.** Used by `market_data.py` and `test_neighborhood_insights.py`. |
| `fetch_school_rating(zip_code, api_key)` | **Add new.** Live API call with caching. |

The service layer will call `fetch_school_rating` first; on `None`, it falls back to `get_school_rating`.

### walkscore.py

Entirely new file. No migration needed — no existing stub or callers.

---

## 4. Data Flow

```
Caller
  │
  ├─ 1. Build cache key (md5 of address / raw zip_code)
  ├─ 2. cache.get(key)
  │     ├─ HIT → return cached value immediately (no HTTP)
  │     └─ MISS →
  │           ├─ 3. (RentCast only) Check daily budget counter
  │           │     ├─ Exceeded → log warning, return None
  │           │     └─ OK → continue
  │           ├─ 4. Build URL + headers/params
  │           ├─ 5. requests.get (or .post for BLS pattern)
  │           │     ├─ HTTP error → log warning, return None
  │           │     └─ 200 → continue
  │           ├─ 6. resp.json()
  │           │     ├─ JSON error → log warning, return None
  │           │     └─ parsed → continue
  │           ├─ 7. Extract value from response dict
  │           │     ├─ Missing key → log warning, return None
  │           │     └─ Found → continue
  │           ├─ 8. Convert to Decimal / dict
  │           │     ├─ Conversion error → log warning, return None
  │           │     └─ Success → continue
  │           ├─ 9. (RentCast only) Increment daily counter
  │           ├─ 10. cache.set(key, value, timeout=TTL)
  │           └─ 11. Return value
  │
  └─ Caller decides: if None, use fallback stub or skip
```

---

## 5. Files Changed

| File | Action | Notes |
|---|---|---|
| `core/integrations/market/rents.py` | **Modify** | Append `fetch_rent_estimate`; keep existing `get_rent_estimate_for_listing` |
| `core/integrations/market/schools.py` | **Modify** | Append `fetch_school_rating`; keep existing `get_school_rating` |
| `core/integrations/market/walkscore.py` | **Create** | New adapter, 3 functions or fewer |
| `core/integrations/market/__init__.py` | **Modify** | Add module-level docstring; no explicit exports needed (imports use dotted path) |
| `.env.example` | **Modify** | Add `RENTCAST_API_KEY`, `GREATSCHOOLS_API_KEY`, `WALKSCORE_API_KEY` under "Data Source API Keys" |
| `.devcontainer/devcontainer.json` | **Modify** | Add 3 new vars to `containerEnv` |
| `tests/test_market_adapters.py` | **Modify** | Add 3 test classes (see §6) |

---

## 6. Test Strategy

All tests extend `django.test.TestCase`. HTTP calls are mocked with `unittest.mock.patch`. No real API calls in CI.

### Layout

```python
class RentCastFetchRentEstimateTest(TestCase):
    """P1 — RentCast adapter tests."""

class GreatSchoolsFetchSchoolRatingTest(TestCase):
    """P2 — GreatSchools adapter tests."""

class WalkScoreFetchWalkScoreTest(TestCase):
    """P3 — Walk Score adapter tests."""
```

### Pattern (per adapter)

| Test | Assertion |
|---|---|
| `test_returns_decimal_on_success` | Mock valid response → assert `Decimal` result |
| `test_returns_none_on_http_error` | Mock `requests.RequestException` → assert `None` |
| `test_returns_none_on_connection_error` | Mock `requests.ConnectionError` → assert `None` |
| `test_returns_none_on_invalid_json` | Mock `json.JSONDecodeError` → assert `None` |
| `test_returns_none_on_missing_key` | Mock response missing expected field → assert `None` |
| `test_returns_none_on_empty_api_key` | Pass `api_key=""`, assert no HTTP call, assert `None` |
| `test_cache_hit_returns_cached_value` | Pre-set cache entry → assert no HTTP call |
| `test_cache_set_on_success` | Assert `cache.set` called with correct key and TTL |
| `test_returns_none_on_budget_exceeded` | (RentCast only) Pre-set counter to 100 → assert `None` |
| `test_returns_decimal_precision` | Assert rounding precision (RentCast: 2dp, GreatSchools: 1dp) |
| `test_empty_list_returns_none` | (GreatSchools only) Mock `[]` → assert `None` |
| `test_transit_bike_optional` | (Walk Score only) Mock missing transit/bike → assert `None` |

### Test helper

```python
def _mock_response(self, json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status.return_value = None
    return mock_resp
```

(Duplicated pattern from existing Census/BLS tests — one `_mock_response` per class is fine.)

---

## 7. Sequence Diagrams

### 7.1 Happy Path

```
Caller              Adapter              Cache              API
  │                    │                   │                 │
  │  fetch_*(args)     │                   │                 │
  │───────────────────>│                   │                 │
  │                    │  cache.get(key)   │                 │
  │                    │──────────────────>│                 │
  │                    │  None (miss)      │                 │
  │                    │<──────────────────│                 │
  │                    │                   │                 │
  │                    │  GET /endpoint    │                 │
  │                    │────────────────────────────────────>│
  │                    │  200 + JSON       │                 │
  │                    │<────────────────────────────────────│
  │                    │                   │                 │
  │                    │  parse + convert  │                 │
  │                    │                   │                 │
  │                    │  cache.set(key,   │                 │
  │                    │    value, TTL)    │                 │
  │                    │──────────────────>│                 │
  │                    │                   │                 │
  │  Decimal/dict/None │                   │                 │
  │<───────────────────│                   │                 │
```

### 7.2 Cache Hit

```
Caller              Adapter              Cache              API
  │                    │                   │                 │
  │  fetch_*(args)     │                   │                 │
  │───────────────────>│                   │                 │
  │                    │  cache.get(key)   │                 │
  │                    │──────────────────>│                 │
  │                    │  cached_value     │                 │
  │                    │<──────────────────│                 │
  │                    │                   │                 │
  │  Decimal/dict/None │                   │                 │
  │<───────────────────│                   │                 │
  │                                       (no HTTP call)
```

### 7.3 Error Path (HTTP failure)

```
Caller              Adapter              Cache              API
  │                    │                   │                 │
  │  fetch_*(args)     │                   │                 │
  │───────────────────>│                   │                 │
  │                    │  cache.get(key)   │                 │
  │                    │──────────────────>│                 │
  │                    │  None (miss)      │                 │
  │                    │<──────────────────│                 │
  │                    │                   │                 │
  │                    │  GET /endpoint    │                 │
  │                    │────────────────────────────────────>│
  │                    │  4xx/5xx or       │                 │
  │                    │  ConnectionError  │                 │
  │                    │<────────────────────────────────────│
  │                    │                   │                 │
  │                    │  log.warning()    │                 │
  │                    │                   │                 │
  │  None              │                   │                 │
  │<───────────────────│                   │                 │
```

### 7.4 Budget Exceeded (RentCast only)

```
Caller           RentCast Adapter        Cache
  │                    │                   │
  │  fetch_rent_       │                   │
  │  estimate()        │                   │
  │───────────────────>│                   │
  │                    │  cache.get(key)   │
  │                    │──────────────────>│
  │                    │  None (miss)      │
  │                    │<──────────────────│
  │                    │                   │
  │                    │  cache.get(       │
  │                    │    rentcast_      │
  │                    │    calls_date)    │
  │                    │──────────────────>│
  │                    │  100              │
  │                    │<──────────────────│
  │                    │                   │
  │                    │  log.warning(     │
  │                    │    budget exceeded)│
  │                    │                   │
  │  None              │                   │
  │<───────────────────│                   │
```
