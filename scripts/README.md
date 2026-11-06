# scripts

## Overview
Repo tooling: design lint, UI crawl, reporting, container entrypoint, and GitOps/CI helper scripts.

## Interface
- check_design.py (+ design_allowlist.txt): enforces DESIGN.md "Don'ts" on templates and CSS; `--write-allowlist` regenerates the allow-list.
- ui_check.py: crawls the logged-in app at 1280px and 390px, fails on UI regressions.
- rent_coverage.py: Markdown report of rent coverage by source (`--city`, `--state`); also `make docker-rent-report`.
- agent_report.py: agent activity report.
- entrypoint.sh: container start; seeds demo data unless `SKIP_SEED=1`.
- init_django.sh `<project_name>`: Django skeleton generator.
- gitops-validate.sh, drift-check.sh, check-requirements-pinning.sh, validate-api-surface.sh: CI/GitOps checks, nonzero exit on failure.
- slo-report.sh, dora-metrics.sh, alert-check.sh: metrics from GitHub CI runs (via `gh`).
- setup-project-board.sh: one-shot GitHub project board setup.
- token-audit.sh: audits agent-file token cost.

## Invariants
- design_allowlist.txt may only shrink.
- Check scripts signal failure through exit codes.

## Side Effects
- `gh`-based scripts call the GitHub API; setup-project-board.sh creates board fields and items; entrypoint.sh writes seed data to the DB; ui_check.py and rent_coverage.py need a running app/seeded DB.

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (pytest.ini); shell scripts are run directly.
