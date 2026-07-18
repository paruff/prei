# PR Naming Standard — prei

> Enforced by CI via Conventional Commits regex in `ci-quality.yml`.
> Every PR title must pass this check before merge.

---

## Format

```
type(scope): lowercase description
```

### Rules

1. **Type** — one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
2. **Scope** — optional, lowercase, in parentheses: `(auth)`, `(ci)`, `(math)`, `(deps)`
3. **Colon-space** — exactly `: ` (colon followed by one space)
4. **First word after colon** — MUST be lowercase `[a-z]`
5. **Description** — free text, but keep it under 72 characters when possible

### Examples

| ✅ Valid | ❌ Invalid | Why |
|---|---|---|
| `feat(ci): add smoke tests` | `feat(ci): Add smoke tests` | Description starts uppercase |
| `fix(math): correct NOI formula` | `fix(math):Correct NOI formula` | Missing space after colon |
| `chore(deps): bump upload-artifact` | `feat: Bump upload-artifact` | Description starts uppercase |
| `docs: update API surface` | `docs:Update API surface` | Missing space |
| `feat(ci): phase A — CI guard` | `feat(ci): Phase A — CI guard` | "Phase" uppercase |

### How the Regex Works

```
^(${types.join('|')})(\([a-z0-9/._-]+\))?!?:\s[a-z].+
│                  │                     │  │    │
│                  │                     │  │    └─ any characters after
│                  │                     │  └─ first char MUST be lowercase a-z
│                  │                     └─ colon + space
│                  └─ optional scope in () with lowercase chars, digits, / . _ -
└─ type prefix
```

### Common Mistakes

| Mistake | Fix |
|---|---|
| "Phase", "Add", "Fix", "Bump" | lowercase: "phase", "add", "fix", "bump" |
| Missing space after `:` | Add space: `feat(ci): add` not `feat(ci):add` |
| Em dash `—` or special chars | Keep it simple: `feat(ci): add ci guard` not `feat(ci): add ci guard — phase A` |

### CI Gate Log

When a PR title fails, the CI log shows:

```
PR title "feat(ci): Phase A — CI guard..." does not follow Conventional Commits.
Expected: type(scope): description
```

The error tells you the PR title that was rejected but not why. The reason is always one of: uppercase first letter, missing space, or wrong format.
