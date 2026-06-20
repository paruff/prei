# Specification — UI-03: Property Entry Form

## User Story

As a passive real estate investor, I want to enter a property's details through a clean, structured form so that the system can calculate underwriting metrics and add it to my Deal Screener dashboard.

## Requirements

### Functional Requirements

1. **Form renders at two URLs:**
   - `/properties/add/` — new property (blank form)
   - `/properties/<id>/edit/` — edit existing property (pre-populated)

2. **Form fields** (all from `Property` model):
   - Location: address, city, state, zip_code, property_type
   - Purchase: purchase_price, sq_ft, bedrooms, year_built
   - Income: monthly_rent_gross, other_monthly_income
   - Expenses: property_taxes_annual, insurance_annual, hoa_monthly, maintenance_monthly, capex_monthly
   - Loan: down_payment_pct, interest_rate, loan_term_years
   - Assumptions: vacancy_rate, mgmt_fee_pct

3. **Widget styling** via custom widget base classes in `core/forms.py`:
   - `StyledNumberInput` — adds `class="form-input num"`
   - `StyledTextInput` — adds `class="form-input"`
   - `StyledSelect` — adds `class="form-input"`
   - All widgets get `class="form-input"` automatically via `__init__`
   - No per-field `attrs` patching in the template

4. **Template** (`templates/property_form.html`):
   - Extends `base.html`
   - Sections: Location, Purchase, Income, Annual expenses, Loan, Assumptions
   - Each field has a `<label>` with `for` matching the input's `id`
   - Validation errors render via `.form-error` below each field
   - Cancel button returns to dashboard
   - Submit button: "Save & analyze" (new) or "Save changes" (edit)

5. **View logic:**
   - `property_create` — GET shows blank form, POST creates property and redirects to detail
   - `property_update` — GET shows pre-populated form, POST updates and redirects to detail
   - Both use `IsAuthenticated` permission
   - Both redirect to `property_detail` on success

### Non-Functional Requirements

- `make lint` passes
- No raw HTML class attributes in template for form inputs (classes come from widgets)
- All Django conventions followed (CSRF, form validation, user scoping)

## Acceptance Criteria

- [ ] Form renders at `/properties/add/` and `/properties/<id>/edit/`
- [ ] Every `label[for]` matches its input `id` — clicking label focuses the input
- [ ] All inputs have `class="form-input"` via widget class — not via per-field attrs in template
- [ ] `grep -rn 'class="form-input"' templates/property_form.html` returns zero matches (classes on widgets, not in template)
- [ ] Validation errors render below each field via `.form-error`
- [ ] Success redirects to property detail; cancel returns to dashboard
- [ ] `make lint` passes

## Constraints

- Depends on UI-01B being merged (existing Property model, URL structure)
- Widget classes must be in `core/forms.py` — not inline in template
- Form must be a `ModelForm` bound to `Property`
