# How to Add a New Property

This guide shows you how to add a new investment property to the Real Estate Investor application.

## Using the Django Admin Interface

### Step 1: Access the Admin Panel

1. Navigate to `http://localhost:8000/admin`
2. Log in with your superuser credentials

### Step 2: Navigate to Properties

1. Click on **Properties** in the **CORE** section
2. Click the **Add Property** button in the top-right corner

### Step 3: Fill in Property Details

Enter the following required information:

- **User:** Select the owner of this property
- **Address:** Street address (e.g., "123 Main Street")
- **City:** City name (e.g., "Portland")
- **State:** State or province (e.g., "OR")
- **Zip code:** Postal code (e.g., "97201")
- **Purchase price:** Property acquisition cost (e.g., "350000.00")

Optional fields:

- **Purchase date:** Date of acquisition
- **Sqft:** Property square footage
- **Units:** Number of rental units (defaults to 1)
- **Notes:** Any additional information

### Step 4: Save the Property

Click **Save** to create the property record.

## Using the Django Shell

For programmatic property creation:

```python
# Start the Django shell
python manage.py shell

# Import necessary models
from django.contrib.auth import get_user_model
from core.models import Property
from decimal import Decimal
from datetime import date

User = get_user_model()

# Get or create a user
user = User.objects.first()  # or create a new user

# Create a property
property = Property.objects.create(
    user=user,
    address="456 Oak Avenue",
    city="Seattle",
    state="WA",
    zip_code="98101",
    purchase_price=Decimal("425000.00"),
    purchase_date=date(2024, 1, 15),
    sqft=1800,
    units=1,
    notes="Single-family rental property"
)

print(f"Created property: {property}")
```

## Using a Management Command (Bulk Import)

For importing multiple properties from a CSV file, see [Import Bulk Data](import-data.md).

## Next Steps

After adding a property:

1. [Add Rental Income](update-rental-income.md) to track expected revenue
2. [Add Operating Expenses](manage-expenses.md) to account for costs
3. [Calculate Investment Metrics](calculate-metrics.md) to analyze the property's performance

## Validation Rules

The application enforces these validation rules:

- **Address** is required and must be unique per user
- **Purchase price** must be a positive decimal value
- **Units** must be at least 1
- All required fields must be filled before saving

## Tips

- Use consistent formatting for addresses to improve data quality
- Enter purchase price as the total acquisition cost (including closing costs)
- Update the purchase date for accurate IRR calculations
- Use the notes field to track property-specific information like property managers or special conditions
