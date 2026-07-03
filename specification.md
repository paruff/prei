# Specification: Market Data API Integrations

## 1. Overview

Replace three dummy stub adapters in `core/integrations/market/` with live API integrations for passive real estate investment analytics. The existing Census and BLS adapters (`census.py`, `bls.py`) serve as the reference pattern: module-level functions, `requests` for HTTP, `django.core.cache` for response caching, `Decimal` for numeric output, and `None`-on-failure semantics.

| Priority | Adapter | File | Status |
|---|---|---|---|
| P1 (HIGH) | RentCast | `rents.py` | Replace stub |
| P2 (MEDIUM) | GreatSchools | `schools.py` | Replace stub |
| P3 (LOW) | Walk Score | `walkscore.py` | New file |

All adapters converge on a single API contract pattern: function takes identifying parameters + `api_key`, returns typed result or `None`, uses Django cache, logs errors without raising.

---

## 2. Functional Requirements

### 2.1 P1 — RentCast Adapter (`core/integrations/market/rents.py`)

RentCast provides a REST API for rental estimates by address/ZIP. The current stub computes `price / sq_ft * 0.9` — replace with a live API call.

**Function:** `fetch_rent_estimate(address: str, api_key: str, zip_code: str | None = None) -> Decimal | None`

- Build URL: `https://api.rentcast.io/v1/rent/long-term` with `address` and `propertyType` params.
- Authenticate via header `X-Api-Key: {api_key}`.
- Parse `data.rent` from JSON response; return as `Decimal` rounded to 2 places.
- Cache result keyed by `rentcast_rent_{md5(address)}` with 7-day TTL (604800s).
- Track daily call count in cache key `rentcast_calls_{date}`; reject if >= 100 (free tier limit).
- On any failure (HTTP error, malformed JSON, missing key, budget exceeded), log warning and return `None`.
- Fallback: when API returns `None`, the caller can use the original heuristic (PPSF * 0.9).

### 2.2 P2 — GreatSchools Adapter (`core/integrations/market/schools.py`)

GreatSchools provides school ratings by ZIP code (0–10 scale). The current stub returns hardcoded state-based values — replace with a live API call.

**Function:** `fetch_school_rating(zip_code: str, api_key: str) -> Decimal | None`

- Build URL: `https://api.greatschools.org/schools/nearby` with `zip` and `key` params, accept header `application/json`.
- Parse response list, compute mean of `gsRating` values across all returned schools.
- Return average as `Decimal` rounded to 1 decimal place (e.g. `Decimal("7.3")`).
- Cache result keyed by `greatschools_rating_{zip_code}` with 30-day TTL (2592000s).
- On any failure, log warning and return existing stub values (the dummy logic from today).
- No budget guard (free tier is generous).

### 2.3 P3 — Walk Score Adapter (`core/integrations/market/walkscore.py`)

New file. Walk Score provides walk/transit/bike scores by address. No existing stub to replace.

**Function:** `fetch_walk_score(address: str, api_key: str) -> dict | None`

- Build URL: `https://api.walkscore.com/score` with `address`, `wsapikey`, and `format=json`.
- Parse `walkscore` (int), `transit.score` (int | None), `bike.score` (int | None) from response.
- Return dict: `{"walk_score": int, "transit_score": int | None, "bike_score": int | None}`.
- Cache result keyed by `walkscore_{md5(address)}` with 30-day TTL (2592000s).
- On any failure, log warning and return `None` (caller handles gracefully — no fallback stub exists).
- No budget guard.

---

## 3. Acceptance Criteria

Each criterion is binary pass/fail. All ACs must pass for the release.

### P1 — RentCast

| # | Criterion | Verification |
|---|---|---|
| AC01 | `fetch_rent_estimate` returns `Decimal` monthly rent on successful API response | Unit test with mock returning `{"data": {"rent": 1850}}` |
| AC02 | `fetch_rent_estimate` returns `None` on HTTP 4xx/5xx | Unit test with mock raising `requests.HTTPError` |
| AC03 | `fetch_rent_estimate` returns `None` on connection error | Unit test with mock raising `requests.ConnectionError` |
| AC04 | `fetch_rent_estimate` returns `None` when API key is empty string | Unit test with `api_key=""`, assert no HTTP call |
| AC05 | `fetch_rent_estimate` returns `None` when daily budget (100 calls) is exceeded | Unit test with cache key `rentcast_calls_{date}` set to 100 |
| AC06 | Cache hit returns cached value without calling API | Unit test with pre-set cache entry, assert `requests.get` not called |
| AC07 | Successful response is stored in cache with 7-day TTL | Unit test asserting `cache.set` called with timeout=604800 |
| AC08 | Output is `Decimal` rounded to 2 decimal places | Assert `result == Decimal("1850.00")` |

### P2 — GreatSchools

| # | Criterion | Verification |
|---|---|---|
| AC09 | `fetch_school_rating` returns `Decimal` average rating on success | Unit test with mock returning two schools with ratings 7 and 9 → `Decimal("8.0")` |
| AC10 | `fetch_school_rating` returns `None` on HTTP failure | Unit test with mock raising `requests.RequestException` |
| AC11 | `fetch_school_rating` returns `None` when API key is empty | Unit test with `api_key=""`, assert no HTTP call |
| AC12 | Cache hit returns cached value without calling API | Unit test with pre-set cache entry |
| AC13 | Successful response is stored in cache with 30-day TTL | Unit test asserting `cache.set` called with timeout=2592000 |
| AC14 | Output is `Decimal` rounded to 1 decimal place | Assert `result == Decimal("8.0")` |
| AC15 | Empty school list returns `None` | Mock returns `[]` |

### P3 — Walk Score

| # | Criterion | Verification |
|---|---|---|
| AC16 | `fetch_walk_score` returns dict with all three keys on success | Unit test with mock returning walk/transit/bike scores |
| AC17 | `transit_score` and `bike_score` are `None` when not in response | Unit test with response missing those fields |
| AC18 | `fetch_walk_score` returns `None` on HTTP failure | Unit test with mock raising `requests.RequestException` |
| AC19 | `fetch_walk_score` returns `None` when API key is empty | Unit test with `api_key=""`, assert no HTTP call |
| AC20 | Cache hit returns cached value without calling API | Unit test with pre-set cache entry |
| AC21 | Successful response is stored in cache with 30-day TTL | Unit test asserting `cache.set` called with timeout=2592000 |

### Cross-cutting

| # | Criterion | Verification |
|---|---|---|
| AC22 | `.env.example` contains `RENTCAST_API_KEY`, `GREATSCHOOLS_API_KEY`, `WALKSCORE_API_KEY` placeholders | Manual review of `.env.example` |
| AC23 | `devcontainer.json` `containerEnv` includes all three new API key env vars | Manual review of `devcontainer.json` |
| AC24 | `core/integrations/market/__init__.py` exports all new functions | `from core.integrations.market.rents import fetch_rent_estimate` works |
| AC25 | All new adapters use `from django.core.cache import cache` | Code review |
| AC26 | All new adapters use `logging.getLogger(__name__)` | Code review |
| AC27 | No adapter raises exceptions to caller (all caught internally) | Code review + unit tests |

---

## 4. API Contracts

### 4.1 RentCast

```
fetch_rent_estimate(address: str, api_key: str, zip_code: str | None = None) -> Decimal | None
```

| Input | Type | Description |
|---|---|---|
| `address` | `str` | Full street address (e.g. "123 Main St, Miami, FL 33139") |
| `api_key` | `str` | RentCast API key from `RENTCAST_API_KEY` env var |
| `zip_code` | `str \| None` | Optional 5-digit ZIP for disambiguation |

| Output | Type | Description |
|---|---|---|
| Success | `Decimal` | Monthly rent estimate, 2 decimal places (e.g. `Decimal("1850.00")`) |
| Failure | `None` | Any error condition |

**HTTP:** `GET https://api.rentcast.io/v1/rent/long-term`
**Auth:** Header `X-Api-Key: {api_key}`
**Response shape:**
```json
{"data": {"rent": 1850.00, "squareFootage": 1200}}
```

### 4.2 GreatSchools

```
fetch_school_rating(zip_code: str, api_key: str) -> Decimal | None
```

| Input | Type | Description |
|---|---|---|
| `zip_code` | `str` | 5-digit ZIP code (e.g. "90210") |
| `api_key` | `str` | GreatSchools API key from `GREATSCHOOLS_API_KEY` env var |

| Output | Type | Description |
|---|---|---|
| Success | `Decimal` | Mean school rating, 1 decimal place (0–10 scale, e.g. `Decimal("7.3")`) |
| Failure | `None` | Any error condition |

**HTTP:** `GET https://api.greatschools.org/schools/nearby?zip={zip}&key={key}`
**Auth:** Query param `key`
**Response shape:**
```json
[
  {"gsRating": "7", "schoolName": "Springfield Elementary"},
  {"gsRating": "9", "schoolName": "Washington High"}
]
```

### 4.3 Walk Score

```
fetch_walk_score(address: str, api_key: str) -> dict | None
```

| Input | Type | Description |
|---|---|---|
| `address` | `str` | Full street address (e.g. "123 Main St, Miami, FL 33139") |
| `api_key` | `str` | Walk Score API key from `WALKSCORE_API_KEY` env var |

| Output | Type | Description |
|---|---|---|
| Success | `dict` | `{"walk_score": int, "transit_score": int \| None, "bike_score": int \| None}` |
| Failure | `None` | Any error condition |

**HTTP:** `GET https://api.walkscore.com/score?address={address}&wsapikey={key}&format=json`
**Auth:** Query param `wsapikey`
**Response shape:**
```json
{
  "status": 1,
  "walkscore": 89,
  "transit": {"score": 72},
  "bike": {"score": 85}
}
```

---

## 5. Non-functional Requirements

### 5.1 Caching

| Adapter | Cache key prefix | TTL | Storage |
|---|---|---|---|
| RentCast | `rentcast_rent_{md5(address)}` | 7 days (604800s) | `django.core.cache` |
| GreatSchools | `greatschools_rating_{zip_code}` | 30 days (2592000s) | `django.core.cache` |
| Walk Score | `walkscore_{md5(address)}` | 30 days (2592000s) | `django.core.cache` |

Cache key generation uses `hashlib.md5` of the input string, matching the `attom_adapter.py` pattern.

### 5.2 Error Handling

All adapters follow the same rule: catch all exceptions internally, log at `WARNING` level, return `None`.

Exceptions to catch:
- `requests.RequestException` (HTTP errors, connection errors, timeouts)
- `json.JSONDecodeError` (malformed responses)
- `KeyError` / `IndexError` (unexpected response structure)
- `InvalidOperation` / `TypeError` (Decimal conversion)

### 5.3 API Key Management

Keys read from environment variables. Adapter functions accept `api_key: str` as a parameter, making them testable without mocking `os.environ`. The calling code (views, management commands, services) reads from `os.getenv()`.

| Variable | Adapter |
|---|---|
| `RENTCAST_API_KEY` | RentCast |
| `GREATSCHOOLS_API_KEY` | GreatSchools |
| `WALKSCORE_API_KEY` | Walk Score |

If `api_key` is empty string, the function returns `None` immediately without making an HTTP call.

### 5.4 Budget Guard (RentCast only)

RentCast free tier allows 100 API calls per day. Track daily call count in cache key `rentcast_calls_{YYYY-MM-DD}`. If the counter reaches 100, return `None` (cache miss treated as budget exceeded). The counter resets automatically via TTL.

---

## 6. Constraints

1. **No new dependencies.** Use `requests`, `logging`, `hashlib`, `decimal`, `django.core.cache` — all already present.
2. **Decimal only.** All monetary and rating values are `Decimal`, never `float`.
3. **No Django model changes.** These are stateless adapters; output is consumed by existing services/views.
4. **No management command changes.** The existing `refresh_market_data` command structure is unchanged.
5. **No settings.py changes.** Cache config lives in the adapter (TTL as module-level constant), not in Django settings.
6. **Tests live in `core/tests/`** following the pattern in `tests/test_market_adapters.py`.
7. **Mock all HTTP calls in tests.** No real API calls in CI.
8. **Respect .env.example conventions.** Group new keys under the existing "Data Source API Keys" section.

---

## 7. Out of Scope

- Retry logic or exponential backoff.
- Pagination (all three APIs return results in a single response at this usage level).
- API response schema validation library (e.g. Pydantic) — manual dict access is sufficient.
- Async HTTP (all adapters use synchronous `requests`).
- Rate limiting beyond the RentCast daily counter (no leaky bucket / token bucket).
- Dashboard or admin UI for API key management.
- Webhook endpoints for API changes.
- Integration tests against live APIs (unit-test-only coverage in this increment).
- Cross-adapter aggregation or caching (each adapter manages its own cache independently).
