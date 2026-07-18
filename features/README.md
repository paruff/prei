# Feature Specifications

Each subdirectory archives the spec, design, and tasks for a completed (or in-progress) feature.

## Structure

```
features/
├── README.md                     # This file
├── gitops-phase1-manifests/      # Completed Phase 1
│   ├── specification.md
│   ├── design.md
│   └── tasks.json
├── gitops-phase3-hardening/      # Current (in progress)
│   ├── specification.md
│   └── ...
└── ...
```

## Convention

Files at repo root (`specification.md`, `design.md`, `tasks.json`) are the ACTIVE working
documents for the current feature being built. After implementation completes and the PR
merges, those files are archived into `features/<slug>/`.

The root files are transformed — they are not the source of truth for past features. The
archived versions in `features/` are the permanent record.

## Status Legend

| Status | Meaning |
|---|---|
| `IN PROGRESS` | Feature branch open, PR active |
| `MERGED` | PR merged to main |
| `DEFERRED` | Spec written but not yet implemented |
