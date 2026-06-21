# How to Use the BRRRR Calculator

This guide explains how to use the client-side BRRRR (Buy, Rehab, Rent, Refinance, Repeat)
calculator to analyze whether a distressed property can be bought, rehabbed, rented, and
refinanced to recycle your down payment into the next deal.

---

## What is BRRRR?

BRRRR is a wealth-building strategy for scaling from 1 to 10+ properties:

1. **Buy** a distressed property below market value
2. **Rehab** to bring it to rent-ready condition
3. **Rent** at market rate
4. **Refinance** at 75% LTV of ARV (After-Repair Value) — the "cash-out refi"
5. **Repeat** — use the refinanced equity to fund the next deal

The key metric: **How much of my own money did I leave in the deal?**

---

## Access the Calculator

Navigate to **BRRRR Calculator** in the navigation menu, or browse to `/brrrr/` on your
prei instance.

---

## Step-by-Step

### Step 1: Enter Property Details

| Field | Description |
|---|---|
| **Purchase Price** | What you'll pay to acquire the property |
| **After-Repair Value (ARV)** | Estimated market value after renovations |
| **Down Payment %** | Percentage down on the purchase loan (typically 20–25%) |
| **Interest Rate** | Annual interest rate on the purchase loan |
| **Loan Term (Years)** | Loan amortization period (typically 30) |

> **ARV is required.** The calculator dims results until you provide an ARV value and shows
> a prompt explaining why it's needed.

### Step 2: Enter Rehab & Refinance Costs

| Field | Description |
|---|---|
| **Rehab Cost** | Total estimated renovation costs |
| **Closing Costs** | Purchase closing costs (optional, defaults to 0) |
| **Refinance LTV %** | Loan-to-value ratio on the cash-out refi (defaults to 75%) |
| **Refinance Interest Rate** | Rate on the new refinanced loan |
| **Refinance Loan Term** | Term of the refinanced loan (typically 30 years) |

### Step 3: Enter Rental Income

| Field | Description |
|---|---|
| **Monthly Rent** | Expected gross monthly rent after rehab |
| **Property Tax (Annual)** | Annual property tax |
| **Insurance (Annual)** | Annual insurance premium |
| **Other Monthly Expenses** | HOA, management, maintenance, etc. |

### Step 4: Read the Results

The calculator computes:

| Metric | Meaning |
|---|---|
| **Cash Left in Deal** | `purchase + rehab + closing - cash-out refi amount`. Negative = you got all your money back |
| **Monthly Cash Flow** | `rent - expenses - new mortgage payment` |
| **CoC Return** | Annual cash flow / cash left in deal (infinite if cash left ≤ 0) |
| **DSCR** | NOI / annual debt service on the new loan |
| **Total Cost** | `purchase + rehab + closing` |
| **New Loan Amount** | `ARV × refinance LTV%` |
| **Monthly PI (New)** | Principal + interest on the new loan |

### Step 5: Interpret the Verdict Banner

| Verdict | Condition | Meaning |
|---|---|---|
| **Full Cycle** 🟢 | Cash left ≤ 0 | You recycled 100% of your capital — ready for the next deal |
| **Partial Recycle** 🟡 | Cash left ≤ 25% of total cost | Most of your capital is free; some remains in the deal |
| **Capital Trap** 🔴 | Cash left > 25% of total cost | Significant capital is stuck in this property |

If **DSCR < 1.25**, a warning is appended to the verdict — most lenders require ≥ 1.25.

---

## Example

**Input:**
- Purchase Price: $150,000
- ARV: $210,000
- Rehab Cost: $40,000
- Down Payment: 20%
- Interest Rate: 7%
- Monthly Rent: $2,000
- Refinance LTV: 75%
- Refinance Rate: 6.5%

**Results:**
- Cash Left in Deal: **-$2,500** (negative = Full Cycle 🟢)
- Monthly Cash Flow: **$350**
- CoC Return: **∞** (infinite — no capital remaining)
- DSCR: **1.42** ✅

---

## Notes

- The calculator is **fully client-side** — no form POST, no page reload. All calculations
  run in JavaScript.
- Numbers are formatted with `toLocaleString()` for your locale.
- If ARV is zero, the results table dims to `opacity: 0.35` and a prompt is shown.
- The `UnderwritingScore` from the server-side engine also tracks BRRRR metrics; see
  `core/services/brrrr.py` for the server-side pure-math engine.
- 25+ unit tests cover the server-side BRRRR logic (`test_brrrr.py`).
