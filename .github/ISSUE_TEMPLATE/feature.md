## name: Feature
about: Product feature to be implemented by a Copilot agent, directed by a PM
title: “[FEAT] “
labels: product, effort-medium
assignees: ‘’

<!--
  DORA 2025 (PLAT-02 — Golden Path): The PM-authored issue is the spec.
  Acceptance criteria become tests. User story provides intent.
  The more specific this issue, the better the agent output.

  Fill in every section. Vague issues produce vague code.
-->

## User Story

**As a** [type of user]
**I want to** [do something]
**So that** [I achieve a benefit]

-----

## Acceptance Criteria

<!-- Each criterion should be specific enough to become a test or BDD scenario. -->

<!-- Use: "Given / When / Then" or "The app [does X] when [condition Y]" -->

- [ ] AC1:
- [ ] AC2:
- [ ] AC3:

-----

## Context for the Agent

<!-- What does the agent need to know that isn't in the codebase? -->

<!-- Reference relevant files: src/types/index.ts, existing services, etc. -->

## **Relevant files:**

## **Existing patterns to follow:**

## **Constraints:**

-----

## Out of Scope

<!-- What should the agent explicitly NOT do? Prevents scope creep. -->

-

-----

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests written and passing
- [ ] `npm run preflight` passes
- [ ] AI-Assisted Review Block completed in PR
- [ ] No architecture boundary violations
- [ ] `docs/API_SURFACE.md` updated if new public functions were added
- [ ] Feature is behind a feature flag (if this is a new end-user feature)

-----

## Effort Estimate

<!-- Update the label to match: effort-small / effort-medium / effort-large -->

**Estimate:**

-----

## Agent Assignment

<!-- When ready to assign: open issue, click "Assignees", select "Copilot" -->

<!-- Or use: @copilot please implement this issue following docs/GOLDEN_PATH.md -->

**Assign to:** Copilot
**Phase:**
