# How to Import Bulk Data

This guide explains how to import multiple properties, rental income records, and operating expenses from CSV files.

## Prerequisites

- The application is installed and migrations are complete
- You have CSV files formatted according to the expected schema
- You have created at least one user in the system

## CSV File Formats

### Properties CSV (`properties.csv`)

Required columns:

```csv
user_id,address,city,state,zip_code,purchase_price,purchase_date,sqft,units,notes
1,"123 Main St","Portland","OR","97201",350000.00,2023-01-15,1800,1,"Single family home"
1,"456 Oak Ave","Seattle","WA","98101",425000.00,2023-03-20,2100,1,"Recently renovated"
```

**Column Descriptions:**

- `user_id` — Database ID of the property owner
- `address` — Street address
- `city` — City name
- `state` — State or province code
- `zip_code` — Postal code
- `purchase_price` — Total acquisition cost (decimal)
- `purchase_date` — Date in YYYY-MM-DD format (optional)
- `sqft` — Square footage (optional)
- `units` — Number of rental units (optional, defaults to 1)
- `notes` — Additional information (optional)

### Rental Income CSV (`rents.csv`)

Required columns:

```csv
property_id,monthly_rent,effective_date,vacancy_rate
1,2500.00,2023-01-15,0.05
2,3200.00,2023-03-20,0.05
```

**Column Descriptions:**

- `property_id` — Database ID of the property
- `monthly_rent` — Monthly rental income (decimal)
- `effective_date` — Date in YYYY-MM-DD format
- `vacancy_rate` — Vacancy rate as decimal (e.g., 0.05 for 5%, optional)

### Operating Expenses CSV (`expenses.csv`)

Required columns:

```csv
property_id,category,amount,frequency,effective_date
1,"Property Tax",4200.00,annual,2023-01-15
1,"Insurance",1200.00,annual,2023-01-15
1,"Maintenance",200.00,monthly,2023-01-15
2,"Property Tax",5100.00,annual,2023-03-20
```

**Column Descriptions:**

- `property_id` — Database ID of the property
- `category` — Expense category (e.g., "Property Tax", "Insurance", "Maintenance")
- `amount` — Expense amount (decimal)
- `frequency` — Either "monthly" or "annual"
- `effective_date` — Date in YYYY-MM-DD format

## Import Command

### Basic Usage

```bash
python manage.py import_csv <properties_file> <rents_file> <expenses_file>
```

### Example

```bash
python manage.py import_csv data/properties.csv data/rents.csv data/expenses.csv
```

### With Docker Compose

```bash
docker-compose exec web python manage.py import_csv data/properties.csv data/rents.csv data/expenses.csv
```

## Step-by-Step Import Process

### Step 1: Prepare Your CSV Files

Create or obtain CSV files following the formats described above. Sample files are available in the `data/` directory.

### Step 2: Verify User IDs

Before importing properties, ensure user IDs in your CSV match existing users:

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()
for user in User.objects.all():
    print(f"User ID: {user.id}, Username: {user.username}")
```

### Step 3: Run the Import Command

```bash
python manage.py import_csv data/properties.csv data/rents.csv data/expenses.csv
```

The command will:

1. Validate the CSV file formats
2. Import properties first
3. Import rental income records
4. Import operating expenses
5. Display a summary of imported records

### Step 4: Verify the Import

Check the Django admin interface to confirm the data was imported correctly:

1. Navigate to `http://localhost:8000/admin`
2. Check **Properties**, **Rental Incomes**, and **Operating Expenses**

## Sample Data

The repository includes sample CSV files in the `data/` directory:

```bash
ls data/
# Output:
# properties.csv
# rents.csv
# expenses.csv
```

You can use these as templates or import them directly for testing.

## Error Handling

The import command validates data and provides informative error messages:

### Missing Required Fields

```
Error: Missing required column 'address' in properties.csv
```

**Solution:** Ensure all required columns are present in the header row.

### Invalid User ID

```
Error: User with ID 999 does not exist
```

**Solution:** Verify user IDs exist in the database before importing.

### Invalid Date Format

```
Error: Invalid date format for 'purchase_date'. Expected YYYY-MM-DD
```

**Solution:** Format dates as `YYYY-MM-DD` (e.g., `2023-01-15`).

### Invalid Decimal Values

```
Error: Invalid decimal value for 'purchase_price': 'abc'
```

**Solution:** Ensure all numeric fields contain valid numbers.

### Invalid Frequency

```
Error: Invalid frequency 'yearly'. Must be 'monthly' or 'annual'
```

**Solution:** Use only "monthly" or "annual" for expense frequency.

## Tips for Large Imports

### Split Large Files

For very large CSV files, consider splitting them into smaller chunks:

```bash
split -l 1000 large_properties.csv properties_chunk_
```

### Use Database Transactions

The import command uses database transactions, so failed imports won't leave partial data.

### Monitor Memory Usage

For imports with thousands of records, monitor memory usage and consider processing in batches.

## Updating Existing Data

The import command creates new records but does not update existing ones. To update:

1. Export existing data
2. Modify the CSV files
3. Delete old records (if appropriate)
4. Re-import the updated CSV files

Or use the Django admin interface to update individual records.

## Exporting Data

To export data back to CSV format:

```python
# Django shell
python manage.py shell

# Export properties
from core.models import Property
import csv

with open('exported_properties.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['user_id', 'address', 'city', 'state', 'zip_code', 'purchase_price'])
    for prop in Property.objects.all():
        writer.writerow([prop.user_id, prop.address, prop.city, prop.state, prop.zip_code, prop.purchase_price])
```

## Next Steps

After importing data:

1. [Calculate Investment Metrics](calculate-metrics.md) — Generate KPI analysis for imported properties
2. [View Financial Reports](../reference/financial-kpis.md) — Understand the calculated metrics
3. [Update Property Information](update-property.md) — Modify imported data as needed

## Troubleshooting

### Command not found

Ensure you're in the project root directory and your virtual environment is activated:

```bash
source .venv/bin/activate
```

### Permission denied

Check file permissions on CSV files:

```bash
chmod 644 data/*.csv
```

### Encoding issues

If you encounter encoding errors with special characters, ensure CSV files are UTF-8 encoded:

```bash
file -i data/properties.csv
# Should show: charset=utf-8
```
