> Load with: "finance-review skill" in your prompt
> Example: "Use the finance-review skill to review this calculation change."

# Finance Review Skill — prei

## When to use

Review any change to financial calculations, KPI formulas, or investment analysis logic. This skill ensures Decimal precision, edge-case safety, and regression prevention.

## Files to read first

- `investor_app/finance/utils.py` — all KPI calculations (canonical)
- `core/services/` — business logic that calls finance utils
- `tests/test_finance_utils.py` — existing test patterns
- `core/tests/test_deal_analyzer.py`, `tests/test_hold_period.py`, `tests/test_tax_analysis.py`

## What to check

### 1. Decimal discipline
- [ ] All inputs coerced via `to_decimal()` before math
- [ ] No `float()` used for money (only as intermediate for numpy)
- [ ] Output is `Decimal`, quantized to appropriate precision
- [ ] `Decimal("0")` used, not `Decimal(0)` or `0`

### 2. Division-by-zero safety
- [ ] Every division guarded by zero-check
- [ ] Pattern: `if denominator == 0: return Decimal("0")`
- [ ] IRR: catches NaN/Inf from numpy_financial
- [ ] No unguarded `/` on user-supplied values

### 3. Edge cases to verify
| Scenario | Expected behavior |
|----------|-------------------|
| Zero purchase price | cap_rate → 0, cash_on_cash → 0 |
| Zero debt service | DSCR → 0 |
| Zero cash invested | CoC → 0 |
| Negative cash flow | ROI negative, no crash |
| hold_years < 1 | ValueError raised |
| exit_cap_rate ≤ 0 | ValueError raised |
| All-positive cash flows | IRR → 0 (no sign change) |
| Single cash flow | ValueError (need ≥ 2 for IRR) |

### 4. Quantization
- [ ] Currency: `.quantize(Decimal("0.01"))` (cents)
- [ ] Rates: `.quantize(Decimal("0.0001"))` (basis points)
- [ ] ROI percentages: `.quantize(Decimal("0.1"))` (one decimal)
- [ ] No silent precision loss

### 5. Tax/depreciation correctness
- [ ] 27.5-year straight-line for residential depreciation
- [ ] `calculate_tax_benefits()` uses hardcoded 80% building / 20% land split
- [ ] `annual_depreciation()` accepts explicit `land_value` parameter (preferred)
- [ ] Depreciation tax shield: `depreciation × marginal_tax_rate`
- [ ] Tax rate as decimal in [0, 1], not percentage

### 6. Regression risk
- [ ] Existing tests still pass (`pytest investor_app/tests/`)
- [ ] New edge cases covered by new tests
- [ ] No behavior change in `compute_analysis_for_property()` unless intended
- [ ] Quantization precision unchanged for existing fields

## Output format

```markdown
## Finance Review

### Decimal Safety ✅ / ⚠️ / ❌
[findings]

### Division Safety ✅ / ⚠️ / ❌
[findings]

### Edge Cases ✅ / ⚠️ / ❌
[findings]

### Quantization ✅ / ⚠️ / ❌
[findings]

### Regression Risk ✅ / ⚠️ / ❌
[findings]

### Verdict: SAFE / UNSAFE — [reason]
```

## Boundary

This skill is read-only guidance for reviewing financial math. It does not write code — the coder or test-writer acts on findings.
