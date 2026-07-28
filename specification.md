# Specification: Phase B — Financial Math (docs/TOP_01_PLAN.md)
# Written: 2026-07-27

---

## 0. Problem

`docs/TOP_01_PLAN.md` Phase B requires the core financial-math functions in
`investor_app/finance/utils.py` to have independent reference implementations,
broad edge-case coverage gated in CI, and mathematical derivation docstrings.
Investigation found Phase B partially done already (commit `30fd355`): B-1 was
missing IRR's reference implementation, B-2 had only 5-9 cases per function
(well short of "50+"), B-3 was already wired, and B-4 had zero derivation
docstrings anywhere. The audit also surfaced a live `AGENTS.md` "Never Do"
violation adjacent to this work: `prei/pipeline/handlers/underwriting.py` was
a second, fully float-based implementation of NOI/cap-rate/cash-on-cash living
outside `services/utils` (Never-Do #1 and #3) — approved for fixing in this
same PR.

## 1. Requirements

- B-1: `tests/finance_reference.py` has an independent, `numpy_financial`-free
  reference implementation of every core KPI, including IRR.
- B-2: `tests/test_finance_math.py` covers 50+ parameterized edge cases per
  function (normal, zero, negative, extreme magnitude, sub-cent precision,
  boundary, int/Decimal coercion).
- B-3: `ci-quality.yml`'s `finance-math` job gates on the full expanded suite
  (already wired; automatically covers new IRR cases once added).
- B-4: `noi`, `cap_rate`, `cash_on_cash`, `dscr`, `irr` in
  `investor_app/finance/utils.py` have full derivation docstrings; `one_percent_rule`/
  `gross_rent_multiplier` get a derivation note added to their existing docstrings.
- UW-1: `prei/pipeline/handlers/underwriting.py` converts from `float` to
  `Decimal` and stops duplicating `cap_rate`/`cash_on_cash` — it imports the
  canonical implementations from `investor_app.finance.utils` instead.

## 2. Acceptance Criteria

| ID | Criterion | test_type |
|---|---|---|
| AC-B1-01 | `ref_irr` exists in `tests/finance_reference.py`, no numpy dependency | unit |
| AC-B2-01 | `pytest tests/test_finance_math.py` passes with 50+ cases per function | unit |
| AC-B2-02 | `one_percent_rule`/`gross_rent_multiplier` reference functions raise `ValueError` matching production's contract | unit |
| AC-B3-01 | `ci-quality.yml`'s `finance-math` job runs `tests/test_finance_math.py` (already true) | ci |
| AC-B4-01 | `noi`/`cap_rate`/`cash_on_cash`/`dscr`/`irr` each have a "Derivation:" docstring paragraph | unit |
| AC-UW-01 | `UnderwritingInput`/`UnderwritingMetrics` fields are `Decimal`, not `float` | unit |
| AC-UW-02 | `underwriting.py` imports `cap_rate`/`cash_on_cash` from `investor_app.finance.utils`, no local duplicate | unit |
| AC-UW-03 | `pytest prei/pipeline/tests/test_underwriting.py tests/test_underwriting_integration.py tests/test_offer_integration.py` passes | unit |
| AC-UW-04 | `orchestrator.py`'s `price * 0.012`/`price * 0.004` boundary uses `Decimal` arithmetic | unit |

## 3. Out of Scope

- `prei/pipeline/handlers/offer.py`'s remaining float-based currency — tracked
  as `docs/KNOWN_LIMITATIONS.md` LIMIT-21, not fixed here.
- Reconciling the bare-function vs. `calculate_*` contract divergence and the
  duplicate `score_listing_v2` functions in `investor_app/finance/utils.py` —
  tracked as LIMIT-20, requires an API-contract decision out of scope for this PR.

## 4. Verification

- `pytest tests/test_finance_math.py -v --tb=short`
- `pytest prei/pipeline/tests/test_underwriting.py tests/test_underwriting_integration.py tests/test_offer_integration.py prei/pipeline/tests/test_orchestrator.py -q -o addopts=""`
- `pytest tests_bdd/ core/tests/ prei/pipeline/tests/ -q`
- `mypy core/ investor_app/finance/` (existing CI command)
- Push branch, open PR, watch `ci-quality.yml` go green. PR stays open for
  human review/merge — never merge or push to `main` directly.
