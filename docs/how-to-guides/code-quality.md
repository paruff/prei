# How to Run Code Quality Tools

This guide explains how to use the linters, formatters, and type checkers configured for this project.

## Overview

The project uses three main code quality tools:

1. **ruff** — Fast Python linter
2. **black** — Python code formatter
3. **mypy** — Static type checker

## Installing Tools

All code quality tools are included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running Ruff (Linter)

### Check for Issues

```bash
ruff check .
```

### Auto-fix Issues

```bash
ruff check . --fix
```

### Check Specific Files

```bash
ruff check core/models.py investor_app/finance/utils.py
```

### Common Ruff Checks

Ruff checks for:
- Unused imports
- Undefined variables
- PEP 8 style violations
- Common bugs and anti-patterns
- Import sorting

## Running Black (Formatter)

### Check Formatting

Check if files need formatting without modifying them:

```bash
black --check .
```

### Format Code

Auto-format all Python files:

```bash
black .
```

### Format Specific Files

```bash
black core/models.py investor_app/finance/utils.py
```

### Black Configuration

Black is configured with default settings (88 character line length).

## Running Mypy (Type Checker)

### Check All Files

```bash
mypy .
```

### Check Specific Module

```bash
mypy core/
mypy investor_app/
```

### Common Type Issues

Mypy checks for:
- Type annotation correctness
- Function signature compatibility
- Attribute existence
- Return type consistency

### Mypy Configuration

Configuration is in `mypy.ini`:

```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Enable gradually
```

## Running All Tools Together

### Sequential Execution

```bash
ruff check . && black --check . && mypy .
```

### With Auto-fixing

```bash
ruff check . --fix && black . && mypy .
```

## Pre-commit Checks

Before committing code, run all quality checks:

```bash
# Auto-fix what can be fixed
ruff check . --fix
black .

# Verify everything passes
ruff check .
black --check .
mypy .
```

## CI/CD Integration

Code quality tools run automatically in CI (`.github/workflows/ci.yml`):

```yaml
- name: Ruff (lint)
  run: ruff check .

- name: Black (format check)
  run: black --check .

- name: Mypy (type checks)
  run: mypy .
```

## Tool-Specific Configuration

### Ruff Configuration

Ruff uses default configuration. To customize, create `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
ignore = []
```

### Black Configuration

Black uses default settings. To customize, add to `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py311']
```

### Mypy Configuration

Mypy configuration is in `mypy.ini`. Customize as needed:

```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
check_untyped_defs = True
```

## Common Workflows

### Before Committing

```bash
# Fix formatting and auto-fixable issues
black .
ruff check . --fix

# Verify all checks pass
ruff check .
black --check .
mypy .

# Run tests
pytest -q
```

### Fixing Specific Issues

#### Unused Imports

Ruff will identify and can auto-remove:

```bash
ruff check . --fix
```

#### Formatting Issues

Black will auto-format:

```bash
black .
```

#### Type Errors

Mypy errors usually require manual fixes:

1. Run `mypy .` to see errors
2. Add type annotations or fix type mismatches
3. Run `mypy .` again to verify fixes

## IDE Integration

### VS Code

Install extensions:
- **Ruff** — Official Ruff extension
- **Black Formatter** — Microsoft's Black extension
- **Mypy Type Checker** — Mypy extension

Configure in `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "mypy-type-checker.args": ["--config-file=mypy.ini"]
}
```

### PyCharm

1. **Ruff:** Install via Settings → Plugins → Marketplace → "Ruff"
2. **Black:** Configure as External Tool or use the Black plugin
3. **Mypy:** Configure as External Tool or use Mypy plugin

## Troubleshooting

### Ruff and Black Conflict

If Ruff and Black disagree on formatting:
- Black has priority for formatting
- Run `black .` first, then `ruff check . --fix`

### Mypy False Positives

If mypy reports incorrect errors:
- Add `# type: ignore` comment for specific lines
- Use more specific type annotations
- Update `mypy.ini` configuration

### Performance Issues

If tools are slow:
- Limit scope: `ruff check core/` instead of `ruff check .`
- Use caching: Ruff and Black cache results by default
- Exclude virtual environments: Add `.venv/` to `.gitignore`

## Best Practices

1. **Run locally before pushing** — Catch issues early
2. **Use auto-fix capabilities** — Let tools handle simple fixes
3. **Add type hints gradually** — Don't try to type everything at once
4. **Configure IDE integration** — Get real-time feedback
5. **Keep tools updated** — `pip install --upgrade ruff black mypy`

## Next Steps

- [Run Tests](running-tests.md) — Execute the test suite
- [Set Up Local Development](setup-local-dev.md) — Configure your development environment
- [CI/CD Configuration](../reference/ci-configuration.md) — Understanding automated checks

## Related Documentation

- [Contributing Guidelines](../explanation/contributing.md) — Code contribution standards
- [Testing Strategy](../explanation/testing-strategy.md) — Testing approach
