# Changelog

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
