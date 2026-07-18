# Design: Missing Acceptance Tests

All tests in `tests/acceptance/` using the existing `conftest.py` fixtures
(`base_url`, `client` — httpx.Client). Run against deployed app via `BASE_URL`.

New files:
- `tests/acceptance/test_growth.py` — growth areas API + system page
- `tests/acceptance/test_pipeline.py` — list, kanban, screener views
- `tests/acceptance/test_dashboard.py` — dashboard view
- `tests/acceptance/test_brrrr.py` — calculator page
- `tests/acceptance/test_leasing.py` — list, kanban views
