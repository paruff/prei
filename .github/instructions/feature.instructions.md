---
name: Feature Development Instructions
description: Applied when implementing new product features from PM-authored issues
applyTo: "src/**/*.ts,src/**/*.tsx"
---

# Feature Development Instructions

## The PM Issue Is Your Spec

When implementing a feature from a GitHub issue:

1. **Read the acceptance criteria first.** Every acceptance criterion becomes either a unit test or a BDD scenario.
2. **Read the user story.** Understand *why* this feature exists before writing any code.
3. **Check `docs/KNOWN_LIMITATIONS.md`** for any gotchas in the area you're working.
4. **Write the failing test first.** Commit it before writing implementation code.

## Feature Development Sequence

```
1. Read the issue acceptance criteria
2. Identify which src/services/ functions are needed
3. Write unit test(s) for any new utility logic → commit: test(scope): failing test for [ISSUE-ID]
4. Implement the utility/service logic → commit: feat(scope): implement [ISSUE-ID]
5. Write/update the screen/component → commit: feat(ui): [ISSUE-ID] screen
6. Run: npm run preflight (lint + typecheck + tests must all pass)
7. Open draft PR with the required PR template filled out
```

## Component Patterns

[PLACEHOLDER — Add your actual component patterns here. Example:]

```tsx
// ✅ Correct — screen uses hook, hook calls service
export function GoalDetailScreen() {
  const { goal, isLoading } = useGoal(goalId);
  // ...
}

// ❌ Wrong — screen calls Firebase directly
export function GoalDetailScreen() {
  const goal = await getDoc(doc(db, 'goals', goalId)); // NEVER
}
```

## When Something Is Ambiguous

If the issue acceptance criteria don't cover an edge case:
- Handle it defensively (validate input, show a user-friendly error)
- Add a comment: `// TODO: PM decision needed — [describe the ambiguity]`
- Flag it in the PR description under "Files I was NOT sure about"

Do NOT invent product decisions. Flag them.
