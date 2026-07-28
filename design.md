# Design: Phase B — Financial Math

### B-1: IRR reference implementation
`ref_irr(cashflows: list[Decimal]) -> Decimal` in `tests/finance_reference.py`
is independent of `numpy_financial` (unlike production's `irr()`, which wraps
it). It brackets a sign change in `NPV(r) = Σ cashflows[t] / (1+r)^t` over a
coarse grid (`r ∈ (-0.9999, 10)`, step `0.01`), then bisects within the
bracket to a `1e-7` tolerance. Returns `Decimal("0")` when no sign change is
found (no real root), mirroring production's existing NaN/Inf fallback.

### B-2: Expanded edge-case coverage
`tests/test_finance_math.py`'s case lists (`NOI_CASES`, `CAP_RATE_CASES`,
`COC_CASES`, `DSCR_CASES`, `ONE_PCT_CASES`, `GRM_CASES`, new `IRR_CASES`) were
expanded to 50+ rows each, organized by category: normal/typical, zero in
each param position, negative in each param position, extreme magnitude,
currency sub-cent precision, boundary/threshold, and int-vs-Decimal coercion.
`ref_one_percent_rule`/`ref_gross_rent_multiplier` were updated to raise
`ValueError` under the same zero/negative conditions as production, so
zero/negative edge cases can't silently diverge between "production raises"
and "reference returns a value."

### B-3: No workflow change
`ci-quality.yml`'s `finance-math` job already runs the whole of
`tests/test_finance_math.py`; B-1/B-2 adding IRR cases to that same file
extends the existing gate automatically.

### B-4: Derivation docstrings
`noi`, `cap_rate`, `cash_on_cash`, `dscr`, `irr` in
`investor_app/finance/utils.py` gained full docstrings (formula + "Derivation:"
paragraph + Args/Returns), following the Args/Returns/Raises style already
used by `one_percent_rule`/`gross_rent_multiplier`. Those two also gained a
one-line derivation note for completeness. No function bodies changed —
docstrings only, verified via `ast.parse` + full test rerun.

### Underwriting.py: float → Decimal, dedup
`UnderwritingInput`/`UnderwritingMetrics` (`prei/pipeline/handlers/underwriting.py`)
became `Decimal`-typed pydantic models — pydantic v2 coerces int/float/str into
`Decimal` fields natively, so existing bare-numeric call sites keep working
unchanged. The local duplicate `cap_rate()` was deleted; the module now
imports `cap_rate`/`cash_on_cash`/`to_decimal` from `investor_app.finance.utils`
directly. `cash_on_cash_yield()` keeps its distinct name and semantics
(all-cash acquisition yield: NOI over price+rehab, no debt service netted
out) but delegates its division through the canonical `cash_on_cash()` instead
of reimplementing `/` locally. The remaining composition helpers
(`gross_potential_rent`, `effective_gross_income`, `total_operating_expenses`,
`net_operating_income`, `max_allowable_offer`) converted their arithmetic to
`Decimal` via the reused `to_decimal()` helper; `solve_underwriting()` uses
`.quantize()` instead of `round()` for the final output.

`orchestrator.py`'s `UnderwritingInput` construction boundary (`price * 0.012`/
`price * 0.004` tax/insurance defaults) was wrapped in `Decimal("0.012")`/
`Decimal("0.004")` arithmetic against a `to_decimal(canonical.price or 0.0)`-
coerced price, reusing `to_decimal()` rather than reinventing coercion.

**Two non-obvious risks found during implementation:**
- `pytest.approx(<float literal>)` compared against a `Decimal` actual is
  fragile, not uniformly broken — it silently short-circuits via exact
  equality for representable values but raises `TypeError` on near-matches
  (`abs(expected - actual)` can't mix `float` and `Decimal`). Every affected
  assertion site was fixed by wrapping the Decimal actual in `float(...)`
  rather than relying on which literals happen to match exactly.
- `Decimal * float` arithmetic (not just comparison) raises `TypeError`
  unconditionally. Test-file call sites that computed derived values inline
  (e.g. `uw.mao * 1.15`, `low.mao * 0.07 / 0.10`) needed `float(...)`-wrapping
  of the Decimal operand before the float arithmetic.
`prei/pipeline/handlers/offer.py`'s `OfferInput.mao: float` field is untouched
by this — pydantic coerces a `Decimal` input to `float` automatically since no
arithmetic happens before construction at the remaining safe call sites.

### Documentation-only additions
Two new `docs/KNOWN_LIMITATIONS.md` entries (LIMIT-20, LIMIT-21) record the
issues found but deliberately not fixed in this PR: the bare-function vs.
`calculate_*` contract divergence plus the duplicate `score_listing_v2`
functions, and `offer.py`'s remaining float-currency issue.
