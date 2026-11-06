# investor_app/finance

## Overview
Decimal-based real-estate finance math. All finance calculation lives here (project rule: no finance math in views).

## Interface
- utils.py: `to_decimal`, `noi`, `cap_rate`, `cash_on_cash`, `dscr`, `irr`, `build_cashflows`, `compute_analysis_for_property(prop) -> InvestmentAnalysis`, `calculate_whatif_monthly_cashflow`.
- mortgage.py: `calculate_monthly_mortgage`, `calculate_property_tax`, `estimate_insurance`, `calculate_maintenance_reserve`, `calculate_break_even_rent`, `calculate_carrying_costs`, `calculate_principal_paydown`, `calculate_appreciation`, `calculate_roi_components`.
- scoring.py: `one_percent_rule`, `gross_rent_multiplier`, `price_to_rent_ratio`, `normalize_market_price_to_rent_score`, `normalize_market_growth_rate_score`, `clamp_market_score`.
- strategies.py: `calculate_flip_strategy`, `calculate_rental_strategy`, `calculate_vacation_rental_strategy`, `estimate_arv`, `estimate_rehab_cost`, `max_refinance_loan`, `cash_left_in_deal`, `brrrr_coc_return`.
- taxes.py: `calculate_tax_benefits`, `annual_depreciation`, `after_tax_cash_flow`, `after_tax_irr`, `project_annual_cash_flows`, `project_property_value`, `net_sale_proceeds`, `total_return_summary`, `depreciation_recapture_tax`, `calculate_annual_depreciation`, `calculate_after_tax_cashflow`.
- tax_strategy.py: `calculate_qbi_deduction`, `calculate_pal_phase_out`, `calculate_pal_allowance`, `calculate_1031_deferral_ratio`, `calculate_1031_exchange`, `calculate_total_tax_benefit`; constants `QBI_DEDUCTION_RATE` (0.20), `PAL_FULL_ALLOWANCE` (25000), `PAL_PHASEOUT_START/END` (100000/150000).

## Invariants
- Money and rates are `Decimal`, never float.
- Market scores are clamped (`clamp_market_score`); price-to-rent thresholds are 15/20/30 and growth is bounded to -5%..10% in scoring.py.

## Side Effects
- None, except `compute_analysis_for_property` in utils.py, which takes a `Property` model and builds an `InvestmentAnalysis` (reads related rows).

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)
