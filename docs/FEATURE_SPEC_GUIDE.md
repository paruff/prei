# Feature Spec Writing Guide

> How to write specification.md, design.md, and tasks.json for the feature-flow process.

---

## The Three Documents

| Document | Purpose | Audience |
|---|---|---|
| `specification.md` | WHAT we're building and WHY | PM, stakeholder, reviewer |
| `design.md` | HOW we're building it | Developer, architect |
| `tasks.json` | Ordered work items with acceptance criteria | AI agent, implementer |

---

## specification.md

Answer these questions:

```markdown
# Specification: <Feature Name>
# Written: <date> session with <author>

## 0. Executive Summary
One paragraph. What problem does this solve? Why now?

## 1. Problem Statement
Current state → Desired state. Be specific. Use bullet points.

## 2. Requirements
Table with ID, description, priority (P0/P1/P2).

## 3. Acceptance Criteria
Table with ID, criterion, test_type (unit/integration/live-system).

## 4. Out of Scope
What we are explicitly NOT building in this feature.
```

### Rules
- Acceptance criteria must be binary pass/fail — no "should" or "improve"
- Every criterion must have a `test_type` tag
- `test_type: live-system` criteria will be run against a real deployment
- Reference the product discovery brief and ARCHITECTURE.md for constraints

---

## design.md

Answer these questions:

```markdown
# Design: <Feature Name>
# Written: <date>

## 1. Architecture Overview
ASCII diagram or numbered flow showing new/modified components.

## 2. Component Design
For each new/modified component: purpose, location, interface, edge cases.

## 3. Workflow/CI Changes
If this touches GitHub Actions, show the before/after job graph.

## 4. File Changes
Table: file, change type (new/modified), purpose.

## 5. Constraints & Risks
Table: risk, mitigation.
```

### Rules
- Must reference ARCHITECTURE.md for layer constraints
- New files should follow existing directory conventions
- CI changes must include a YAML parse check
- Every new endpoint/service function must be documented

---

## tasks.json

```json
{
  "meta": {
    "project": "prei",
    "session": "<slug>-<date>",
    "date": "<YYYY-MM-DD>",
    "feature": "<Feature Name>",
    "spec": "specification.md",
    "design": "design.md"
  },
  "tasks": [
    {
      "id": "T-01",
      "summary": "<one-line description>",
      "description": "<detailed description of what to build>",
      "depends_on": ["T-00"],
      "acceptance_criteria": [
        {"id": "AC-01-01", "description": "<criterion>", "test_type": "unit"},
        {"id": "AC-01-02", "description": "<criterion>", "test_type": "live-system"}
      ]
    }
  ]
}
```

### Rules
- Task IDs are `T-<letter><number>` (e.g., T-A1, T-01, T-G3)
- Acceptance criteria IDs are `AC-<task>-<number>` (e.g., AC-A1-01)
- `test_type` must be one of: `unit`, `integration`, `live-system`
- Tasks must be ordered by dependency (independents first)
- Maximum 6 tasks per feature (prefix each additional task with "─ subtask")

---

## After Implementation

1. Archive to `features/<slug>/specification.md`, `design.md`, `tasks.json`
2. Update `specification.md` at root to point to archived version
3. Update `docs/planning/PRODUCT_STRATEGY.md` if feature affects product strategy
4. Run `docs/ARCHITECTURE.md` if feature changes layer boundaries

---

## Before Starting a New Feature

1. Read `discovery-brief.md` — understand the product vision
2. Read `docs/planning/PRODUCT_STRATEGY.md` — understand what's built vs planned
3. Read `docs/ARCHITECTURE.md` — know the layer constraints
4. Read `docs/KNOWN_LIMITATIONS.md` — don't make listed issues worse
5. Read `docs/CHANGE_IMPACT_MAP.md` — know what files co-change
6. Check `features/` for similar past work — learn from previous features
