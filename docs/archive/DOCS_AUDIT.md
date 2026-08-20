# Documentation Audit — prei

> Audit date: 2026-07-18
> Reference: AGENTS.md

---

## Directory Structure

```
prei/
├── specification.md          → CURRENT feature spec (ephemeral, overwritten)
├── design.md                 → CURRENT feature design (ephemeral, overwritten)
├── tasks.json                → CURRENT feature tasks (ephemeral, overwritten)
├── features/                 → ARCHIVED feature specs (permanent)
│   └── <slug>/               → one directory per feature
├── docs/                     → LASTING documentation
│   ├── ARCHITECTURE.md       → system architecture
│   ├── API_SURFACE.md        → public API reference
│   ├── KNOWN_LIMITATIONS.md  → active issues
│   ├── CHANGE_IMPACT_MAP.md  → co-change rules
│   ├── PR_STANDARD.md        → naming conventions
│   ├── DEPLOYMENT_STRATEGY.md→ deployment plan
│   ├── TEST_PYRAMID_PLAN.md  → testing roadmap
│   ├── TOP_01_PLAN.md        → quality roadmap
│   ├── GITOPS_COMPLIANCE_AUDIT.md → compliance status
│   ├── UFAWKES_OBS_SETUP.md  → integration guide
│   ├── assessments/          → one-off assessment reports
│   │   ├── APP_REVIEW.md
│   │   ├── DISCOVERY_ASSESSMENT.md
│   │   ├── GROWTH_AREA_ASSESSMENT.md
│   │   └── GROWTH_AREAS_AUDIT.md
│   └── planning/             → roadmap plans
│       ├── AI_POLICY.md
│       ├── FEATURE_FLOW_AUDIT.md
│       ├── PRODUCT_STRATEGY.md
│       └── PM Critique.md
└── tests/                    → test suites
    ├── test_finance_math.py
    ├── test_finance_reference.py
    └── acceptance/
```

## Findings

### 1. Root files are ephemeral — no archive existed

The root `specification.md`, `design.md`, `tasks.json` get overwritten for every feature.
The previous feature's work was lost unless committed to the feature branch.

**Fixed:** Created `features/` directory with conventions in `features/README.md`.

### 2. `docs/` had assessment reports mixed with lasting docs

Files like `DISCOVERY_ASSESSMENT.md`, `GROWTH_AREA_ASSESSMENT.md`, `APP_REVIEW.md` are
one-off reports, not ongoing documentation. They clutter `docs/`.

**Fixed:** Moved to `docs/assessments/`.

### 3. Planning docs had no clear home

`AI_POLICY.md`, `PRODUCT_STRATEGY.md`, `FEATURE_FLOW_AUDIT.md`, `PM Critique.md` are
planning artifacts, not reference docs.

**Fixed:** Moved to `docs/planning/`.

### 4. AGENTS.md had no guidance on doc vs feature vs test structure

**Fixed:** Added in AGENTS.md below.

---

## Code → Docs → Tests Alignment

| Concern | Code | Docs | Tests |
|---|---|---|---|
| KPI math | `investor_app/finance/utils.py` | `docs/ARCHITECTURE.md` | `tests/test_finance_math.py` |
| CI pipeline | `.github/workflows/` | `docs/TEST_PYRAMID_PLAN.md` | `tests/acceptance/` |
| Deployment | `docker-publish.yml` | `docs/DEPLOYMENT_STRATEGY.md` | `post-deployment.yml` |
| API surface | `core/api_views.py` | `docs/API_SURFACE.md` | `tests/acceptance/test_api.py` |
| GitOps | `deploy/` | `docs/GITOPS_COMPLIANCE_AUDIT.md` | `scripts/gitops-validate.sh` |

**Status:** All major concerns have code, docs, AND tests aligned. No orphaned docs or untested code.
