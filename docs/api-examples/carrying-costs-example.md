# Carrying Cost Calculation API Examples

## Endpoint

```
POST /api/v1/real-estate/carrying-costs/calculate
```

## Example 1: Basic Single-Family Home Analysis

This example shows a typical single-family home investment analysis with negative cash flow.

### Request

```json
{
  "propertyDetails": {
    "purchasePrice": 350000,
    "propertyType": "single-family",
    "squareFeet": 1850,
    "bedrooms": 3,
    "bathrooms": 2,
    "yearBuilt": 1995,
    "location": {
      "address": "123 Main St, Miami, FL 33139",
      "county": "Miami-Dade",
      "state": "FL",
      "zip": "33139"
    }
  },
  "financing": {
    "downPayment": 70000,
    "loanAmount": 280000,
    "interestRate": 7.5,
    "loanTermYears": 30,
    "closingCosts": 8500,
    "loanPoints": 2800
  },
  "operatingExpenses": {
    "propertyTaxRate": 2.1,
    "insuranceAnnual": 1800,
    "hoaMonthly": 0,
    "utilitiesMonthly": 200,
    "maintenanceAnnualPercent": 1.0,
    "propertyManagementPercent": 10,
    "vacancyRatePercent": 8
  },
  "rentalIncome": {
    "monthlyRent": 2500,
    "otherMonthlyIncome": 0
  },
  "investmentStrategy": "buy-and-hold"
}
```

## Understanding the Response

### Carrying Costs Breakdown

The `carryingCosts` section includes:

- **mortgage**: Monthly principal and interest payment
- **propertyTax**: Monthly property tax (annual tax / 12)
- **insurance**: Monthly insurance premium
- **hoa**: Monthly HOA fees (if applicable)
- **utilities**: Monthly utility costs
- **maintenance**: Monthly maintenance reserve (typically 1% of property value annually)
- **propertyManagement**: Management fee (percentage of rent)
- **total**: Sum of all carrying costs

### Cash Flow Analysis

The `cashFlow` section shows:

- **grossRentalIncome**: Total rental income before expenses
- **vacancyLoss**: Expected loss due to vacancy
- **effectiveGrossIncome**: Rental income after vacancy
- **operatingExpenses**: All expenses except debt service
- **noi**: Net Operating Income (before debt service)
- **debtService**: Mortgage payments
- **netCashFlow**: Final cash flow after all expenses

### Investment Metrics

- **totalCashInvested**: Down payment + closing costs + loan points
- **cocReturn**: Cash-on-Cash return percentage
- **cocInterpretation**: Rating (negative, poor <5%, fair 5-8%, good 8-12%, excellent >12%)
- **capRate**: Capitalization rate (NOI / purchase price)
- **breakEvenRent**: Minimum rent needed to cover all costs
- **debtCoverageRatio**: NOI / debt service (lenders typically require >1.25)

### Warnings

The API generates warnings for:

- **negative_cash_flow**: When monthly costs exceed rental income
- **break_even_mismatch**: When required rent exceeds market rent
- **low_dcr**: When debt coverage ratio is below typical lender requirements

## Tips for Best Results

1. **Property Tax Rate**: Use your county's actual tax rate for accuracy
2. **Insurance**: Provide actual insurance quotes when available
3. **Maintenance**: Adjust percentage based on property age and condition
4. **Vacancy Rate**: Research local market averages (typically 5-10%)
5. **Property Management**: Standard rates are 8-10% of gross rent
