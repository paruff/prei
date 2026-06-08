# Migration Safety Skill — prei

## When to load
- Before creating any Django migration
- When modifying models that have existing data
- When reviewing migrations in PRs

## Non-negotiable rules

1. **Reversible by default.** Every migration must have a `reverse()` path. If you can't reverse it, explain why in the PR and get human approval.
2. **No data loss.** Never use `RemoveField`, `DeleteModel`, or `RunSQL DELETE` without a backup plan. Create the backup table/column first, migrate data, then remove.
3. **Decimal fields:** Never change `DecimalField` precision or `max_digits` on columns with existing data without a data migration that preserves values.
4. **Backward compatible.** Old code must work against the new schema during rolling deploys. Add columns as nullable first, backfill, then add constraints.
5. **Test migrations.** Run `python manage.py migrate --check` and `python manage.py migrate` in CI. Test forward AND reverse.

## Migration checklist

Before submitting a migration PR:

```
□ Migration is reversible (has reverse() or is explicitly irreversible with justification)
□ No data loss — existing rows preserved
□ Decimal fields: precision unchanged or data migration preserves values
□ New columns are nullable (or have defaults) for backward compatibility
□ Data migration (if needed) is separate from schema migration
□ Migration tested forward AND reverse
□ No sensitive data in migration (secrets, PII, production values)
```

## Common anti-patterns

| Anti-pattern | Why it's bad | Correct approach |
|---|---|---|
| `RemoveField` without backup | Data loss, irreversible | Rename to `_backup`, create new field, migrate data |
| `AlterField` on DecimalField | Truncates existing values | Add new field, copy data, drop old |
| `RunSQL` with hardcoded IDs | Breaks in other environments | Use `RunPython` with queries |
| Adding `NOT NULL` without default | Fails on existing rows | Add nullable, backfill, then constrain |
| Large data migration in single transaction | Locks table, timeouts | Batch in chunks of 1000 |

## Django migration commands

```bash
# Check for pending migrations
python manage.py makemigrations --check

# Dry run
python manage.py migrate --plan

# Apply
python manage.py migrate

# Reverse last migration
python manage.py <app> 0001_previous
```

## Financial data migrations

When migrating financial data (Decimal fields):

1. **Never truncate.** `Decimal("12345.67")` must stay `Decimal("12345.67")`, not `12345.67`.
2. **Log before/after.** Print row counts and sample values in `RunPython`.
3. **Idempotent.** Migration must be safe to run multiple times.
4. **Test with production-like data.** Create test data with edge cases (zero, negative, very large values).
