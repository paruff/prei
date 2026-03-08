## Phase 2.6 — Structured Logging Configuration

### User Story
As an operator, I want structured log output from analytics pipelines so that errors are traceable and observable in production without code changes.

### Background
- `investor_app/settings.py` has a `LOGGING` dict (or none at all — check)
- Several service functions (e.g., `irr` in `finance/utils.py`, market adapters) catch exceptions silently
- `AGENTS.md` requires logging in all analytics pipelines

### Acceptance Criteria
- [ ] Add (or update) the `LOGGING` dict in `investor_app/settings.py` with:
  - Root logger at `WARNING`
  - `investor_app` logger at `INFO` with a console handler
  - `core` logger at `INFO` with a console handler
  - Formatter that includes: `levelname`, `name`, `message`, and (in DEBUG mode) `pathname` + `lineno`
- [ ] Confirm `irr()` in `investor_app/finance/utils.py` logs a `WARNING` with the exception details when numpy-financial raises
- [ ] Confirm `refresh_market_snapshot` (Phase 2.2) logs `ERROR` on adapter failure
- [ ] Add a test in `core/tests/test_services_phase2.py` (already exists — add to it) or a new file that uses `caplog` to assert:
  - `irr` with un-solvable cashflows emits a WARNING log
  - No unhandled exceptions escape from `irr`

### Files to Change
| File | Action |
|------|--------|
| `investor_app/settings.py` | **Edit** — add/update `LOGGING` dict |
| `investor_app/finance/utils.py` | **Edit** — confirm `irr` logs on failure (add `logger.warning(...)` if missing) |
| `core/tests/test_services_phase2.py` | **Edit** — add `caplog` assertions for `irr` warning |

### Implementation Notes
- Use `logging.getLogger(__name__)` at module level in each file
- Do **not** use `print()` — use the `logging` module
- In `settings.py`, use `env("LOG_LEVEL", default="INFO")` so it can be overridden in production
- Add `LOG_LEVEL=INFO` to `.env.example`

### Definition of Done
- `pytest core/tests/test_services_phase2.py -v` passes with new caplog test
- `ruff check investor_app/settings.py investor_app/finance/utils.py` passes
- `LOG_LEVEL` documented in `.env.example`

### Labels
`chore` `phase-2` `backend`
