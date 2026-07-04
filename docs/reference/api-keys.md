# API Keys Reference — prei

This reference documents the API keys required to power the data-driven intelligence features of prei, including signup links and usage details.

---

## Keys At-A-Glance

| Environment Variable | Service | Free Tier | Signup URL |
|---|---|---|---|
| `ATTOM_API_KEY` | ATTOM Data | 1,000 calls/mo | [api.attomdata.com](https://api.attomdata.com) |
| `CENSUS_API_KEY` | US Census Bureau | Unlimited | [api.census.gov](https://api.census.gov/data/key_signup.html) |
| `BLS_API_KEY` | Bureau of Labor Statistics | 25,000 calls/day | [data.bls.gov/registrationEngine](https://data.bls.gov/registrationEngine/) |
| `RENTCAST_API_KEY` | RentCast | 50 calls/mo | [rentcast.io](https://rentcast.io) |
| `GREATSCHOOLS_API_KEY` | GreatSchools | Free basic tier | [greatschools.org/api](https://www.greatschools.org/api/) |
| `WALKSCORE_API_KEY` | Walk Score | Free basic tier | [walkscore.com/professional/api](https://www.walkscore.com/professional/api) |

---

## 1. ATTOM Data API Key (`ATTOM_API_KEY`)

Used for property-level detail enrichment, foreclosures, taxes, and comps valuation.

- **Purpose:** Enriches a newly created property page with structural details (sqft, bedrooms, bathrooms, year built) and fetches local comparable sales (comps) for BRRRR After-Repair Value (ARV) calculations.
- **Get Key:** Go to [api.attomdata.com](https://api.attomdata.com), click "Sign Up", create a developer account, and copy your API key from the dashboard.
- **Cost / Limits:** The Free Trial includes 1,000 requests per month.
- **Budget Monitoring:**
  - `ATTOM_MONTHLY_BUDGET=1000.00`
  - `ATTOM_COST_PER_CALL=0.01`
  - Configure these in `.env` to prevent unexpected charges.

---

## 2. Census API Key (`CENSUS_API_KEY`)

Used for population growth and demographic tracking at the ZIP-code level.

- **Purpose:** Powers the **Markets** page population signal. Calculates population growth over the last 1, 3, and 5 years.
- **Get Key:** Visit [api.census.gov/data/key_signup.html](https://api.census.gov/data/key_signup.html), fill out the form, and you will receive your API key via email.
- **Cost / Limits:** 100% Free with no daily limit.

---

## 3. Bureau of Labor Statistics API Key (`BLS_API_KEY`)

Used for state/metro unemployment rates and employment diversity index.

- **Purpose:** Powers the **Markets** page economic scoring signals. Pulls monthly Local Area Unemployment Statistics (LAUS) and Quarterly Census of Employment and Wages (QCEW).
- **Get Key:** Register at [data.bls.gov/registrationEngine/](https://data.bls.gov/registrationEngine/) to receive your registration key.
- **Cost / Limits:** Free tier allows up to 25,000 requests per day.

---

## 4. RentCast API Key (`RENTCAST_API_KEY`)

Used for gross rent estimates and rental comps.

- **Purpose:** Provides expected rental estimates for properties and BRRRR deals based on active/historical rental listings in the immediate radius.
- **Get Key:** Register at [rentcast.io](https://rentcast.io) or go directly to the developer dashboard.
- **Cost / Limits:** Free tier includes 50 requests per month.

---

## 5. GreatSchools API Key (`GREATSCHOOLS_API_KEY`)

Used for neighborhood school quality indicators.

- **Purpose:** Displays local school ratings on the Property detail scorecard and factors into the neighborhood rating signal.
- **Get Key:** Apply at [greatschools.org/api](https://www.greatschools.org/api/).
- **Cost / Limits:** Free basic tier for non-commercial or personal developer use.

---

## 6. Walk Score API Key (`WALKSCORE_API_KEY`)

Used for walkability and transit quality scores.

- **Purpose:** Pulls Walk Score, Transit Score, and Bike Score for the property address to display on the scorecard dashboard.
- **Get Key:** Apply at [walkscore.com/professional/api](https://www.walkscore.com/professional/api).
- **Cost / Limits:** Free basic tier.

---

## Safe Environment Management

### Local (`.env`)

Never commit your actual API keys to git. Put them in your root `.env` file (copied from `.env.example`), which is already in `.gitignore`.

```env
# Example .env config
ATTOM_API_KEY=your_key_here
CENSUS_API_KEY=your_key_here
BLS_API_KEY=your_key_here
```

### Dev Container / Codespaces

If you are using Codespaces, do not edit `.devcontainer/devcontainer.json` to insert real keys. Instead:
1. Open GitHub → Repo Settings → Secrets and Variables → **Codespaces**
2. Add your keys as Codespace secrets (e.g. `ATTOM_API_KEY`)
3. Rebuild your Codespace — the variables are automatically injected into your terminal and `devcontainer.json` environment.

### Render (`render.yaml` or Dashboard)

When deploying to production:
1. Open **Render Dashboard** → Your Web Service → **Environment**
2. Add the corresponding environment variables as hidden/secret variables.
3. Re-deploy. Do not hardcode them in `render.yaml`.
