---
name: "Bug Fix"
about: "A defect to be investigated and fixed by a Copilot agent"
title: "[BUG] "
labels:
  - bug
  - effort-small
assignees: []
---

## What Is Broken

<!-- Be specific. "It doesn't work" is not enough. What exactly fails? -->

## Steps to Reproduce

1.
1.
1.

**Expected behaviour:**

**Actual behaviour:**

-----

## Context for the Agent

**Error message or stack trace (if any):**

```
[paste here]
```

**Relevant files:**

<!-- Where does the PM suspect the bug lives? -->

-

**What was recently changed in this area?**

<!-- Link to the PR that may have introduced this. -->

-----

## Acceptance Criteria for the Fix

- [ ] The steps to reproduce no longer produce the bug
- [ ] A regression test is added that would have caught this bug
- [ ] No other tests are broken

-----

## Out of Scope

<!-- What should the agent NOT refactor while fixing this? -->

-----

## Definition of Done

- [ ] Bug is fixed and steps to reproduce pass
- [ ] Regression test added
- [ ] `ruff check . && black --check . && pytest -q` passes
- [ ] `docs/KNOWN_LIMITATIONS.md` updated to remove this limitation (if it was listed)
- [ ] Root cause noted in PR description
