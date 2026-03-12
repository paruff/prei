## Phase 3.5 — Saved Search Nightly Tuning Job

### User Story
As an investor, I want my saved searches to be automatically refined based on which listings I actually save or dismiss, so that future recommendations improve over time without manual filter tweaks.

### Background
- `SavedSearch` model exists in `core/models.py`: `user`, `zip_code`, `state`, `min_price`, `max_price`, `query`
- `UserWatchlist` model tracks properties the user has saved/watched
- `Notification` model tracks generated alerts (can be used to infer interest)
- Celery + Beat are configured in `docker-compose.yml` and `investor_app/celery.py`

### Acceptance Criteria
- [ ] Add a field `adjusted_min_score` (`DecimalField`, nullable) to `SavedSearch` in `core/models.py` and create a migration
- [ ] Create `core/services/search_tuning.py` with:
  - `tune_saved_searches(user) -> int`  
    — for each of the user's `SavedSearch` objects, count how many listings matched in the last 30 days vs. how many resulted in a watchlist save; if match rate < 10%, raise `adjusted_min_score` by 5%; return total number of searches updated
  - `run_nightly_tuning() -> dict`  
    — iterate all users with at least one `SavedSearch`; call `tune_saved_searches(user)` for each; return `{"users_processed": int, "searches_updated": int}`
- [ ] Add a Celery Beat periodic task in `core/tasks.py`:
  - `nightly_search_tuning_task()` — calls `run_nightly_tuning()` and logs the result
  - Register in `investor_app/celery.py` `beat_schedule` to run daily at 02:00 UTC
- [ ] Unit tests in `core/tests/test_search_tuning.py` (`@pytest.mark.django_db`):
  - User with no watchlist saves → `adjusted_min_score` raised for searches with low match rate
  - User with high watchlist rate → score unchanged
  - `run_nightly_tuning` with no users → returns `{"users_processed": 0, "searches_updated": 0}`
  - Migration correctly adds `adjusted_min_score` field (test that field exists on model)

### Files to Change
| File | Action |
|------|--------|
| `core/models.py` | **Edit** — add `adjusted_min_score` to `SavedSearch` |
| `core/migrations/` | **Create** — migration for `adjusted_min_score` |
| `core/services/search_tuning.py` | **Create** |
| `core/tasks.py` | **Edit** — add `nightly_search_tuning_task` |
| `investor_app/celery.py` | **Edit** — register beat schedule |
| `core/tests/test_search_tuning.py` | **Create** |

### Implementation Notes
- Use `Decimal` throughout; no `float` in score adjustments
- Guard divide-by-zero when `total_matches = 0` → skip tuning for that search
- Keep tuning logic in the service; task is thin (just calls service + logs)
- Add a DB index on `SavedSearch.user` if not already present

### Definition of Done
- `pytest core/tests/test_search_tuning.py -v` passes
- `ruff check core/services/search_tuning.py core/tests/test_search_tuning.py` passes
- Migration applies cleanly (`python manage.py migrate --check`)
- Beat schedule visible in `celery.py` with correct crontab

### Labels
`enhancement` `phase-3` `backend`
