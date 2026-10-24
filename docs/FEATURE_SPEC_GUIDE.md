# Feature Spec Writing Guide

> How to write intent.md, spec.md and plan.md (the AI-native SDLC artifact chain). Each is approved at a gate by merging the PR that changes it; work status lives only on the [project board](https://github.com/users/paruff/projects/3) (see `AGENTS.md`).

---

## The Three Documents

| Document | Purpose | Audience |
|---|---|---|
| `intent.md` | The problem, outcome and constraints (gate: intent) | Product owner |
| `spec.md` | WHAT we decided to build (gate: spec) | PM, stakeholder, reviewer |
| `plan.md` | HOW and in what order, by release milestone (gate: plan) | Developer, AI agent |

---

## intent.md

```markdown
# Intent: <title>
**Author:** <name> · **Status:** draft | accepted · **Date:** <YYYY-MM-DD>

## Problem
## Proposed outcome
## Affected users and systems
## Constraints
## Open questions
```

### Rules
- No solution design: that belongs in `spec.md` and `plan.md`
- Check against `VISION.md` non-goals before writing
- Intent changes go in their own `docs(intent):` PR

---

## spec.md

Answer these questions:

```markdown
# Specification: <Feature Name>
# From: intent.md
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

## plan.md

```markdown
# Plan: <title>
**From:** intent.md and spec.md, <date> · **Status:** draft | approved

## Release milestones
One `###` per release (= GitHub milestone). Table: Row | Work | Spec IDs | Issue (or `no issue yet`).
No status column: status lives on the board.

## Files that change
## Order of work
## Risks
## Proof
```

### Rules
- Every row cites spec IDs (FR-n, AC-n) and maps to one issue in that release's milestone
- Must respect `docs/ARCHITECTURE.md` layer constraints
- Rows that share files run in sequence, not in parallel
- When implementation departs from the plan, update `plan.md` in the same PR

---

## After Implementation

1. After the release ships, archive to `features/<slug>/intent.md`, `spec.md`, `plan.md`
2. Start the next release's `intent.md` at root
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
