# How to Calculate Investment Metrics

This guide explains how to compute and view financial KPIs for your investment properties.

## Automatic Calculation

The Real Estate Investor application automatically calculates investment metrics when you have the required data:

1. **Property** — Purchase price and basic details
2. **Rental Income** — Monthly rent and vacancy rate
3. **Operating Expenses** — Property expenses (taxes, insurance, maintenance, etc.)

## Using the Finance Utility Functions

### Programmatic Calculation

You can trigger KPI calculations using the `compute_analysis_for_property` function:

```python
from investor_app.finance.utils import compute_analysis_for_property
from core.models import Property

# Get a property
property = Property.objects.get(id=1)

# Calculate all metrics
analysis = compute_analysis_for_property(property)

# View results
print(f"NOI: ${analysis.noi}")
print(f"Cap Rate: {analysis.cap_rate * 100:.2f}%")
print(f"Cash-on-Cash: {analysis.cash_on_cash * 100:.2f}%")
print(f"IRR: {analysis.irr * 100:.2f}%")
print(f"DSCR: {analysis.dscr}")
```

### Via Django Shell

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from core.models import Property, RentalIncome, OperatingExpense
from investor_app.finance.utils import compute_analysis_for_property
from decimal import Decimal

User = get_user_model()
user = User.objects.first()

# Create a property
property = Property.objects.create(
    user=user,
    address="789 Investment Ave",
    city="Austin",
    state="TX",
    zip_code="78701",
    purchase_price=Decimal("400000")
)

# Add rental income
RentalIncome.objects.create(
    property=property,
    monthly_rent=Decimal("3000"),
    effective_date="2024-01-01",
    vacancy_rate=Decimal("0.05")
)

# Add operating expenses
OperatingExpense.objects.create(
    property=property,
    category="Property Tax",
    amount=Decimal("4800"),
    frequency="annual",
    effective_date="2024-01-01"
)

OperatingExpense.objects.create(
    property=property,
    category="Insurance",
    amount=Decimal("1800"),
    frequency="annual",
    effective_date="2024-01-01"
)

OperatingExpense.objects.create(
    property=property,
    category="Maintenance",
    amount=Decimal("300"),
    frequency="monthly",
    effective_date="2024-01-01"
)

# Calculate metrics
analysis = compute_analysis_for_property(property)

# Display results
print(f"\nProperty: {property}")
print(f"Purchase Price: ${property.purchase_price}")
print(f"\nFinancial Metrics:")
print(f"  NOI: ${analysis.noi}")
print(f"  Cap Rate: {float(analysis.cap_rate) * 100:.2f}%")
print(f"  Cash-on-Cash: {float(analysis.cash_on_cash) * 100:.2f}%")
print(f"  IRR: {float(analysis.irr) * 100:.2f}%")
print(f"  DSCR: {analysis.dscr}")
```

## Viewing Metrics in Django Admin

1. Navigate to `http://localhost:8000/admin`
2. Click on **Investment analyses** under the **CORE** section
3. View the calculated metrics for each property

## Understanding the Calculations

### Net Operating Income (NOI)

```
NOI = Annual Income - Annual Operating Expenses
```

- **Annual Income** = Monthly Rent × 12 × (1 - Vacancy Rate)
- **Annual Expenses** = Sum of all operating expenses (normalized to annual)

### Cap Rate

```
Cap Rate = NOI ÷ Purchase Price
```

Expressed as a percentage (e.g., 0.059 = 5.9%)

### Cash-on-Cash Return

```
Cash-on-Cash = Annual Cash Flow ÷ Total Cash Invested
```

In the MVP:
- **Annual Cash Flow** = NOI (no debt service)
- **Total Cash Invested** = Purchase Price

### Internal Rate of Return (IRR)

IRR is calculated using a 12-month cash flow projection:

- Month 0: `-Purchase Price`
- Months 1-12: `NOI ÷ 12`

### Debt Service Coverage Ratio (DSCR)

```
DSCR = NOI ÷ Annual Debt Service
```

In the MVP, DSCR returns 0 when there's no debt service (all-cash purchase).

## Manual Calculation Examples

### Example Property

- **Purchase Price:** $350,000
- **Monthly Rent:** $2,500
- **Vacancy Rate:** 5%
- **Annual Property Tax:** $4,200
- **Annual Insurance:** $1,200
- **Monthly Maintenance:** $200

### Calculate NOI

```
Effective Monthly Income = $2,500 × (1 - 0.05) = $2,375
Annual Income = $2,375 × 12 = $28,500

Monthly Expenses = ($4,200 ÷ 12) + ($1,200 ÷ 12) + $200 = $650
Annual Expenses = $650 × 12 = $7,800

NOI = $28,500 - $7,800 = $20,700
```

### Calculate Cap Rate

```
Cap Rate = $20,700 ÷ $350,000 = 0.0591 or 5.91%
```

### Calculate Cash-on-Cash

```
Cash-on-Cash = $20,700 ÷ $350,000 = 0.0591 or 5.91%
```

(Same as Cap Rate in all-cash purchase scenario)

## Recalculating Metrics

Metrics are stored in the `InvestmentAnalysis` model. To recalculate:

```python
from investor_app.finance.utils import compute_analysis_for_property
from core.models import Property

# Recalculate for a specific property
property = Property.objects.get(id=1)
analysis = compute_analysis_for_property(property)

# Recalculate for all properties
for property in Property.objects.all():
    compute_analysis_for_property(property)
    print(f"Updated analysis for {property}")
```

## Best Practices

1. **Add complete data** — Ensure all rental income and expenses are entered
2. **Update regularly** — Recalculate when income or expenses change
3. **Check assumptions** — Verify vacancy rates and other assumptions
4. **Compare properties** — Use consistent assumptions when comparing investments
5. **Account for all expenses** — Don't forget property tax, insurance, HOA, utilities, etc.

## Common Issues

### Zero NOI

If NOI is zero, check:
- Have you added rental income records?
- Have you added operating expense records?
- Are the effective dates correct?

### Unexpected Cap Rate

If cap rate seems incorrect:
- Verify purchase price is accurate
- Check that expenses are properly categorized (monthly vs. annual)
- Ensure vacancy rate is set correctly

### IRR Calculation Errors

If IRR returns 0:
- This may indicate the calculation failed (negative cash flows only)
- Current MVP uses simplified 12-month projection
- Future versions will support custom holding periods

## Next Steps

- [Understanding Financial KPIs](../reference/financial-kpis.md) — Detailed calculation reference
- [Manage Operating Expenses](manage-expenses.md) — Add and update expenses
- [Update Rental Income](update-rental-income.md) — Modify rent and vacancy rates

## Related Documentation

- [Financial KPIs Reference](../reference/financial-kpis.md)
- [Property Model](../reference/index.md)
- [Add a Property](add-property.md)
