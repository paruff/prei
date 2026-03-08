## Phase 4.2 — Risk Profile Configuration & Weighting

### User Story
As an investor, I want to configure my risk tolerance and rehab comfort level so that ranking and deal analysis automatically weight factors to match my investment style.

### Background
- `RANKING_WEIGHTS` will be added to `investor_app/settings.py` by Phase 3.2
- `rank_listings` in `core/services/ranking.py` uses those weights
- `compute_analysis_for_property` uses `FINANCE_DEFAULTS`
- No per-user risk profile exists today

### Acceptance Criteria
- [ ] Add a `RiskProfile` model to `core/models.py`:
  ```python
  class RiskProfile(models.Model):
      user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="risk_profile")
      risk_tolerance = models.CharField(max_length=16, choices=[("low","Low"),("medium","Medium"),("high","High")], default="medium")
      rehab_comfort = models.CharField(max_length=16, choices=[("none","None"),("light","Light"),("full","Full")], default="light")
      custom_vacancy_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
      custom_capex_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
  ```
- [ ] Create migration for `RiskProfile`
- [ ] Add `core/services/risk.py` with:
  - `get_effective_defaults(user) -> dict`  
    — returns `FINANCE_DEFAULTS` merged with the user's `RiskProfile` custom rates (if set); creates a default `RiskProfile` if one does not exist
  - `get_effective_ranking_weights(user) -> dict`  
    — returns `RANKING_WEIGHTS` adjusted for the user's `risk_tolerance` (high risk → lower crime weight; low risk → higher school weight)
- [ ] Unit tests in `core/tests/test_risk_profiles.py` (`@pytest.mark.django_db`):
  - User with no `RiskProfile` → default profile created; defaults returned
  - User with `custom_vacancy_rate = Decimal("0.10")` → returned in effective defaults
  - High risk tolerance → crime weight lower than medium risk
  - Low risk tolerance → school weight higher than medium risk
- [ ] Integrate `get_effective_defaults` into `compute_analysis_for_property` (pass as override if user is available)
- [ ] Add a basic risk profile settings page or form (can be admin-only for Phase 4)

### Files to Change
| File | Action |
|------|--------|
| `core/models.py` | **Edit** — add `RiskProfile` model |
| `core/migrations/` | **Create** — migration |
| `core/services/risk.py` | **Create** |
| `core/tests/test_risk_profiles.py` | **Create** |
| `investor_app/finance/utils.py` | **Edit** — optionally accept `defaults` override in `compute_analysis_for_property` |

### Implementation Notes
- `get_effective_defaults` uses `dict.copy()` and `.update()` — never mutates `settings.FINANCE_DEFAULTS`
- All custom rate values must be `Decimal`; validate in model `clean()` that they are between 0 and 1
- Migration must be reversible

### Definition of Done
- `pytest core/tests/test_risk_profiles.py -v` passes
- Migration applies and reverses cleanly
- `ruff check core/services/risk.py core/models.py` passes

### Labels
`enhancement` `phase-4` `backend`
