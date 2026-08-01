# Discovering Properties

> Source distressed and foreclosure properties in a growth area, then move them into
> your pipeline for screening.

---

## Prerequisites

- A **growth area** to search in. Run the
  [Growth Explorer](analyze-growth-areas.md) for a state first, or pick an existing
  area from the list. Without one, discovery shows a market picker instead.
- API keys for the sources you want to use (optional but recommended) — see
  [Data Sources & API Keys](../reference/data-sources.md).

## Step 1: Choose a Growth Area

- From the **Growth Areas** list, click **Discover Properties** on a market row — this
  opens `/discovery/?growth_area_id=X` pre-filtered to that market.
- Or open `/discovery/` directly: you'll see a picker of your top growth areas.

## Step 2: Review Available Sources

The discovery page lists the available sources for the chosen market, with a count of
existing records per source:

| Source | What it contains | Has rent data? |
|---|---|---|
| **HUD REO** | Government-owned HUD foreclosures | No |
| **USDA REO** | USDA Rural Development foreclosures | No |
| **VRM (VA REO)** | VA-owned foreclosures via VRM | **Yes** (projected rent) |
| **ATTOM Pre-foreclosure** | NOD/NTS pre-foreclosure notices | No |
| **County Foreclosure Notices** | County-level NTS / sheriff sale / auction records | No |

> **Rent data matters for screening.** Properties from VRM carry projected rents, so
> gross-yield and price-to-rent screening can run. HUD, USDA, ATTOM, and County sources
> have no rent estimate — yield and PTR are skipped for them (see
> [Screening Properties](screen-properties.md)).

Each source shows its **count** — how many matching records already exist in the app
for that state + city. Check the boxes for the sources you want to query.

## Step 3: Run Discovery

1. Select at least one source (you'll get a warning if none are selected).
2. Click **Discover Properties in [City]**.

What happens:

- prei queries the selected sources for the growth area's state + city and creates
  `PipelineProperty` records for matches.
- HUD/USDA/VRM/ATTOM/County collection runs in **background threads** (Gunicorn
  worker timeout is 30s). If no VRM listings exist for the state yet, a VRM scrape
  starts in the background — you'll see an info message telling you to refresh in a
  minute.
- When finished, you're redirected to the **Screener** for this growth area.

## Step 4: Review Results

After discovery you land on the screener (`/pipeline/screener/?growth_area_id=X`) and
see:

- **KPI cards** — totals for discovered, passed screening, failed, and already-existing
  properties in this market.
- **Success/warning messages** at the top describing what was created.
- The properties themselves in the screener table, ready for review.

Continue to [Screening Properties](screen-properties.md).

---

## Source Details

### HUD REO
Government-owned foreclosures sourced from the HUD API. Good volume of banked
properties; no rent estimates, so yield/PTR screening is skipped.

### USDA REO
Rural Development foreclosures, similar shape to HUD. Relevant when you invest in
smaller towns that qualify for USDA programs.

### VRM (VA REO)
VA-owned foreclosures via VRM Properties. The only source with **projected monthly
rent**, enabling full yield/PTR screening.

### ATTOM Pre-foreclosure
Notice of Default (NOD) and Notice of Trustee Sale (NTS) records. Properties here are
still in pre-foreclosure — earlier stage, more upside, more uncertainty.

### County Foreclosure Notices
NTS, sheriff sale, and auction records at the county level. Often the earliest notice
of distress in a market.

---

## Troubleshooting

| Problem | Cause / Fix |
|---|---|
| "No growth areas yet" | Run the Growth Explorer for a state first (see [Analyzing Growth Areas](analyze-growth-areas.md)) |
| Source count is 0 | No data for that state+city yet — run discovery anyway to trigger collection, or check your API keys |
| "VRM scrape started in background" | No VA listings existed for the state; refresh in ~1 minute and re-run discovery |
| Nothing happened on POST | At least one source must be checked; also confirm the growth area is resolved (check the URL has `growth_area_id`) |
| Results don't show rent | Expected for HUD/USDA/ATTOM/County — only VRM carries rents |
