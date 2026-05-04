---
name: Testing Instructions
description: Applied when writing or modifying test files
applyTo: "tests/**/*.ts,tests/**/*.tsx,**/*.test.ts,**/*.spec.ts"
---

# Testing Instructions

## Test-First Discipline

**Always write the failing test before the implementation.**

The commit order is:
1. `test(scope): failing test for [what you're building]` — RED
2. `feat(scope): implement [what you're building]` — GREEN
3. `refactor(scope): clean up [if needed]` — REFACTOR

Never commit a test that already passes before you write the implementation.

## Test Categories and Where They Live

| Category | Location | What Goes Here |
|---|---|---|
| Unit | `tests/unit/` | Pure functions in `src/utils/` |
| Service | `tests/integration/` | Service functions with Firebase emulator |
| Component | `tests/unit/` | React component rendering and interactions |
| E2E | `tests/e2e/` | BDD scenarios (Cucumber + Playwright) |

## Unit Test Pattern

[PLACEHOLDER — replace with your actual test framework and patterns. Example using Jest:]

```typescript
// tests/unit/utils/compoundInterest.test.ts
import { projectGrowth } from '../../../src/utils/compoundInterest';

describe('projectGrowth', () => {
  it('returns initial amount when rate is 0', () => {
    expect(projectGrowth(1000, 0, 12)).toBe(1000);
  });

  it('throws ValidationError for negative principal', () => {
    expect(() => projectGrowth(-100, 5, 12)).toThrow(ValidationError);
  });

  it('handles monthly compounding correctly', () => {
    // 1000 at 12% annual = 1126.83 after 12 months
    expect(projectGrowth(1000, 12, 12)).toBeCloseTo(1126.83, 1);
  });
});
```

## What Every Test Must Have

- A `describe` block named after the function/component being tested
- At least one **happy path** test
- At least one **error/edge case** test (invalid input, empty state, network failure)
- Descriptive `it()` names — read like sentences: "returns X when Y"

## What Tests Must NEVER Do

- Call live Firebase (use emulator or mock)
- Have side effects on other tests (clean up state in `afterEach`)
- Import from `screens/` or `components/` in unit tests for `utils/`
- Be deleted to make CI pass — fix the code instead
