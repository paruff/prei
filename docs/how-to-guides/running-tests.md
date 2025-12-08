# How to Run Tests

This guide explains how to run the test suite for the Real Estate Investor application.

## Test Types

The application includes three types of tests:

1. **Unit Tests** — Test individual functions and methods in isolation
2. **Integration Tests** — Test interactions between components
3. **BDD Tests** — Behavior-driven tests using Gherkin syntax

## Prerequisites

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

## Running All Tests

To run the complete test suite:

```bash
pytest
```

For a quieter output with just pass/fail counts:

```bash
pytest -q
```

For verbose output with test names:

```bash
pytest -v
```

## Running Specific Test Types

### Unit Tests Only

```bash
pytest core/tests/test_finance_utils.py
```

### Integration Tests

```bash
pytest core/tests/test_views.py
pytest core/tests/test_models.py
```

### BDD Tests

```bash
pytest tests_bdd/
```

## Running Tests for a Specific Module

Run tests in a specific file:

```bash
pytest core/tests/test_models.py
```

Run a specific test function:

```bash
pytest core/tests/test_finance_utils.py::test_noi_calculation
```

Run tests matching a keyword:

```bash
pytest -k "finance"
```

## Using Test Coverage

Generate a coverage report:

```bash
pip install pytest-cov
pytest --cov=core --cov=investor_app
```

Generate an HTML coverage report:

```bash
pytest --cov=core --cov=investor_app --cov-report=html
```

Open `htmlcov/index.html` in your browser to view the detailed coverage report.

## Running Tests with Docker Compose

If you're using Docker Compose:

```bash
docker-compose exec web pytest -q
```

For verbose output:

```bash
docker-compose exec web pytest -v
```

## Database Configuration for Tests

Tests use a separate test database configured in `investor_app/settings_test.py`. The test database is automatically created and destroyed for each test run.

To use PostgreSQL for testing (instead of SQLite):

```bash
export DATABASE_URL="postgres://postgres:postgres@localhost:5432/investor_db_test"
pytest
```

## Running Tests in CI

The CI pipeline (`.github/workflows/ci.yml`) automatically runs tests on every push and pull request. Tests run with:

- PostgreSQL service container
- Full linting (ruff)
- Format checking (black)
- Type checking (mypy)
- Complete test suite (pytest)

## Common Test Scenarios

### Testing Financial Calculations

```bash
pytest core/tests/test_finance_utils.py -v
```

### Testing Models and Database Operations

```bash
pytest core/tests/test_models.py -v
```

### Testing Views and URLs

```bash
pytest core/tests/test_views.py -v
```

## Debugging Test Failures

### Show print statements during tests

```bash
pytest -s
```

### Stop at first failure

```bash
pytest -x
```

### Drop into debugger on failure

```bash
pytest --pdb
```

### Run only failed tests from last run

```bash
pytest --lf
```

## Test Fixtures

Common fixtures are defined in:

- `core/tests/conftest.py` — Shared fixtures for core app tests
- `tests_bdd/conftest.py` — BDD test fixtures

Example fixtures:

- `user` — Creates a test user
- `property` — Creates a test property
- `rental_income` — Creates rental income records
- `operating_expense` — Creates expense records

## Writing New Tests

When adding new functionality, always add corresponding tests:

1. **Unit tests** for financial calculations and utility functions
2. **Integration tests** for model methods and view logic
3. **BDD tests** for user workflows and scenarios

Follow the existing test structure and naming conventions:

- Test files: `test_<module_name>.py`
- Test functions: `test_<specific_behavior>`
- Test classes: `Test<ClassName>`

## Best Practices

- Keep tests deterministic (no random data, no external API calls)
- Use factories or fixtures for test data
- Test edge cases (zero values, negative numbers, very large values)
- Ensure tests clean up after themselves
- Write descriptive test names that explain what is being tested

## Troubleshooting

### Tests fail with database errors

Ensure the test database can be created:

```bash
python manage.py migrate --settings=investor_app.settings_test
```

### Import errors

Make sure you're in the project root and your virtual environment is activated:

```bash
source .venv/bin/activate
```

### Fixture not found

Check that `conftest.py` files are in the correct locations and fixtures are properly defined.

## Next Steps

- [Code Quality Tools](code-quality.md) — Run linters and type checkers
- [CI/CD Configuration](../reference/ci-configuration.md) — Understanding automated testing
- [Contributing Guidelines](../explanation/contributing.md) — How to contribute tests
