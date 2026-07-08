---
title: "prei v0.3.1-alpha.2: Pipeline Lifecycle, Auto-Versioning, and Market Intelligence"
published: false
tags: realestate, investing, django, python, opensource
---

## Why

Passive real estate investors need more than just a deal calculator — they need a **workflow**. The gap between "this deal looks good on paper" and "I own this property" is where most analysis tools stop. prei now bridges that gap with an end-to-end pipeline that tracks a property from discovery through screening, offer, renovation, closing, and into leasing.

## What

This alpha release ships the full pipeline lifecycle system (PIPE-0 through PIPE-14) alongside major improvements to market intelligence and infrastructure. You can now screen a property against 9 criteria, move it through offer/DD/renovation/closing stages, and track leasing — all within the app.

We also overhauled our versioning system. Every build now carries its git tag and commit SHA as baked Docker metadata, visible in the footer, in logs, and via `docker inspect`. Releases are auto-tagged from conventional commits via `python-semantic-release`.

## How

The pipeline introduces new models (`PipelineProperty`, `ScreeningCriteria`, `PipelineTransaction`, `LeasingProperty`) and views for each stage. The nav now organizes actions into Buy / Maintain / Sell groups.

For operators: `docker compose pull && docker compose up -d` gets you the latest. The footer will show `v0.3.1-alpha.2` with the commit SHA.

## Proof

105 unit tests pass across models, validators, finance utilities, and forms. The pipeline views have been verified through our live-system acceptance test suite (PIPE-14). Every Docker image is scanned for CRITICAL/HIGH CVEs, signed with build provenance attestation, and published to GHCR.

## What's Next

- Property comparison and portfolio scenario modeling
- Enhanced notifications and collaboration features
- Additional data source integrations (Redfin, Zillow)
- Stable v0.3.0 release

[GitHub Repo](https://github.com/paruff/prei)
