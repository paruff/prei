# Changelog

## [Unreleased]

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
