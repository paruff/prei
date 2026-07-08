# Changelog

## [0.4.0] - 2026-07-08

### Added
- **Discovery Source Models (DISC-0)**: `HudProperty`, `UsdaProperty`, `CountyForeclosureNotice` models for structured HUD/USDA/county foreclosure data storage.
- **HUD REO Ingestion (DISC-1)**: `ingest_hud_reo` command fetching from HUD ArcGIS Hub GeoJSON feed. Confirmed real endpoint replaces guessed mock.
- **USDA REO Ingestion (DISC-2)**: `ingest_usda_reo` command with fixed-width TXT parser for USDA rural REO data.
- **HUD/USDA Pipeline Screening (DISC-3)**: Extended `screen_property()` to accept HudProperty/UsdaProperty directly; hard-kill criteria for non-rentable sources.
- **HUD/USDA List/Detail Views (DISC-4)**: Property list and detail pages with "Add to Pipeline" for HUD and USDA sources.
- **Dallas County TX NTS Scraper (DISC-5)**: First county-level foreclosure scraper targeting Dallas County publicsearch.us. Playwright-based with graceful auth-wall handling.
- **ATTOM Preforeclosure Integration (DISC-6)**: Wired existing `ATTOMAdapter` to fetch NOD/NTS/Lis Pendens notices by ZIP code into `CountyForeclosureNotice`. Management command `fetch_attom_preforeclosure`.
- **Property Discovery Page**: Source management and request system for triggering property fetches.
- **Fannie Mae HomePath Datasource**: Scraper stub for HomePath.com (blocked by Cloudflare WAF — returns empty results gracefully).

### Fixed
- HUD endpoint corrected from guessed URL to real ArcGIS Hub GeoJSON (DISC-HG-1).
- Migration conflicts resolved between DISC-0/DISC-1/DISC-2 branches.
- Test conftest merged HUD + USDA fixtures after merge conflict.
- Reportlab 5 upgrade unblocked by replacing xhtml2pdf with Playwright PDF generation.
- 7 CodeQL clear-text logging alerts suppressed in ATTOM adapter.
- CI failure for PR #241 (missing HUD test fixtures) and PR #232 (ruff/mypy/CodeQL gates).

### Changed
- **Python 3.14**: Project fully migrated from Python 3.12/3.13 to Python 3.14.6. All venvs, hooks, CI configs updated.
- **Django 6.0**: Upgraded from Django 5.2 to 6.0.7.
- **Reportlab 5.0**: Upgraded from reportlab 4.x to 5.0; xhtml2pdf replaced by Playwright `page.pdf()`.
- **ATTOM Adapter**: Added `postalcode` param support to `fetch_foreclosure_data()`.
- **Dependencies**: Updated django-stubs, svglib, types-reportlab; added pypdf for test PDF extraction.

### Removed
- `xhtml2pdf` dependency (replaced by Playwright for PDF generation).

## [0.3.1-alpha.2] - 2026-07-08

### Added
- **Pipeline Lifecycle System (PIPE-0 through PIPE-14)**: End-to-end deal pipeline with discovery, 9-criteria screening, offer/DD/renovation/closing/leasing views, and pipeline list/detail UI. Includes new models for pipeline transactions and leasing properties.
- **Semver 2.0 Versioning**: Version now auto-detected from git tags (dev) or baked-in Docker metadata (production). Docker labels, structured logging, and automated semantic-release workflow added.
- **ATTOM API + FRED API Integration**: ATTOM comps fixes and FRED economic data integration for market analysis.
- **Growth Area Enhancements**: Pagination, CSV export, UX overhaul, and overlay fixes for the Growth Area Explorer.
- **Pipeline Navigation**: Restructured main nav into Buy / Maintain / Sell groups with pipeline-focused links.

### Changed
- Version source: removed stale `VERSION` file, now reads from git tag at HEAD or baked Docker metadata.
- Docker image includes `org.opencontainers.image.version` and `revision` labels.
- Startup logging now emits structured JSON fields (`version`, `git_commit`, `python_version`, `django_version`).
- Automated releases via `python-semantic-release` on merge to `main`.

### Fixed
- Integration test skipping when API keys absent (CI #505).
- VRM scraper: replaced obsolete CSS selectors with embedded JSON model parsing.
- Growth Explorer overlay visibility on page load.
- Devcontainer SQLite path permissions and `collectstatic` ordering in entrypoint.

## [0.2.2] - 2026-07-06

### Added
- **Growth Area Explorer**: Full view and template for exploring growth areas with demographic and economic data.
- **Growth Area → VRM Foreclosures Linking**: Navigate from growth area rows to filtered VRM foreclosure lists.
- **Pipeline Navigation**: Restructured main nav into Buy / Maintain / Sell groups.
- **Census Integration**: `discover_places_in_state` function for discovering places by state.
- **Growth Phase B**: GrowthArea population, SQLite default configuration, ATTOM comps fix.
- **Tests**: Docker e2e smoke test, Makefile validation, Census adapter tests for discover_places and growth_explorer.

### Changed
- Devcontainer: switched to absolute SQLite path to resolve bind-mount permission errors (multiple fixes).
- CI: replaced `amannn/action-semantic-pull-request` with `github-script`; bumped pre-commit ruff to v0.15.20.
- Entrypoint now runs `collectstatic` and `seed_data` automatically in devcontainer.
- Nav bar now includes Growth Areas and VRM Foreclosures links.

### Fixed
- VRM scraper: parse embedded JSON model instead of obsolete CSS selectors.
- Devcontainer port visibility; `USE_X_FORWARDED_HOST` support added.
- Production settings tests; CodeQL logging sanitization.
- GitOps validation: skip `USER root` check for devcontainer Dockerfile.

## [0.2.1] - 2026-07-03

### Added
- **VRM JSON Import**: Importer, management command, API endpoint, template, and tests for importing VRM data from JSON.
- **Version Number in Footer**: Git commit SHA and version tag now displayed in the app footer.

### Changed
- CI: replaced `black` with `ruff format`; upgraded mypy `python_version` from 3.11 to 3.12.
- Docker build: installed `libcairo2-dev` for svglib 1.6+ pycairo compilation.
- Pre-commit hooks reorganized with modern ruff configuration.

### Fixed
- Various CodeQL, bandit, and mypy lint issues across the codebase.
- `reportlab` pinned to `<5.0` for xhtml2pdf compatibility.

### Dependencies
- Updated: `aiohttp`, `docker/setup-buildx-action` (v3→v4), `playwright`, `reportlab`, `actions/checkout` (v6→v7), `docker/build-push-action` (v6→v7).

## [0.2.0] - 2026-06-21

### Added
- **P1 RentCast API**: New `fetch_rent_estimate` for real rental estimates by address. Includes 7-day caching, daily budget guard (100 calls/day), and automatic fallback to PPSF heuristic on failure.
- **P2 GreatSchools API**: New `fetch_school_rating` for real school ratings by ZIP code (0-10 scale). Includes 30-day caching and fallback to stub values.
- **P3 Walk Score API**: New `fetch_walk_score` for walkability, transit, and bike scores by address. 30-day caching with graceful `None` return.
- **Configuration**: `RENTCAST_API_KEY`, `GREATSCHOOLS_API_KEY`, and `WALKSCORE_API_KEY` env vars supported in `.env.example` and devcontainer.
- **Test coverage**: 23 new unit tests across all three adapters (happy path, error handling, cache behavior, edge cases).

### Changed
- `core/integrations/market/__init__.py` updated with adapter documentation.
- Pipeline artifacts: `specification.md`, `design.md`, `tasks.json` produced and committed.

### Notes
- All three adapters follow the existing Census/BLS pattern: stateless functions, `requests` for HTTP, Django cache, `Decimal` precision, and `None`-on-failure semantics.
- Existing stub functions (`get_rent_estimate_for_listing`, `get_school_rating`) preserved for backward compatibility.
