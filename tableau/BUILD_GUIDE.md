# Tableau Public build guide

Goal: one dashboard, "Washington Hospital Readmissions," that takes about 2 hours to build in the free **Tableau Public** desktop app (https://public.tableau.com/app/learn/how-to → Download).

## 1. Connect the data

1. Open Tableau Public → **Connect → Text file** → `data/processed/wa_hospital_oe_flags.csv`.
2. Add the other files as **separate data sources** (Data → New Data Source → Text file):
   - `wa_vs_us_tests.csv`
   - `funnel_limits.csv`
   - `wa_hrrp_coverage.csv`
3. In each source, set `zip` to **Geographic Role → ZIP Code/Postcode** and `county` to **County**. Make sure `facility_id` and `zip` are strings, not numbers.

## 2. Sheets

### Sheet 1: "WA vs. Other States" (forest plot)
Source: `wa_vs_us_tests.csv`
- Rows: `measure_label`. Sort by `difference`, ascending.
- Columns: `Measure Values` with `wa_mean_err` and `other_states_mean_err` → change the mark type to **Circle**.
- Add the CIs: create a second axis with `wa_ci_low` / `wa_ci_high` as **Gantt bars** (size = `wa_ci_high - wa_ci_low`), or simply show the CI in the tooltip.
- Reference line: constant **1.0**, dashed, labeled "As expected".
- Tooltip: WA mean, 95% CI, other states mean, `p_welch_bh` (label it "Adjusted p-value"), and `significant_fdr_05`.

### Sheet 2: "Hospital Funnel Plot"
Source: `wa_hospital_oe_flags.csv` (dual axis with `funnel_limits.csv`, blended on `measure_label`)
- Columns: `expected_readmissions`. Rows: `oe_ratio`.
- Color: `oe_flag` (Higher = red #C0392B, Lower = green #1E8449, As expected = navy #1F4E79).
- Second axis: `upper_95` and `lower_95` from `funnel_limits` as **Lines**, grey, dashed. **Synchronize axes.**
- Filter: `measure_label` (single-value dropdown, shown on dashboard, default "Heart failure").
- Tooltip: hospital name, city, discharges, observed vs. expected readmissions, O/E with its 95% CI.

### Sheet 3: "Hospital Map"
Source: `wa_hospital_oe_flags.csv`
- Double-click `zip` for a map; Color: `oe_flag`; Size: `number_of_discharges`.
- Use the same measure filter as Sheet 2 (Apply to worksheets → All using related data sources).

### Sheet 4: "HRRP Coverage"
Source: `wa_hrrp_coverage.csv`
- Bar chart: `hospital_type` on Rows, `COUNT(facility_id)` on Columns, Color: `hrrp_status`.
- Title: "Not every WA hospital is measured: Critical Access Hospitals are outside HRRP."

### Sheet 5: KPI tiles (optional)
Three text tiles: WA hospitals in HRRP, # flagged higher than expected, # flagged lower than expected.

## 3. Dashboard layout (1200 × 900, fixed size)

```
┌──────────────────────────────────────────────────────────────┐
│ Title + 1-line subtitle + measure dropdown          KPI tiles│
├──────────────────────────────┬───────────────────────────────┤
│ Sheet 1: WA vs Other States  │ Sheet 2: Funnel plot          │
├──────────────────────────────┼───────────────────────────────┤
│ Sheet 3: Map                 │ Sheet 4: HRRP coverage        │
├──────────────────────────────┴───────────────────────────────┤
│ How to read this · Data: CMS Provider Data Catalog, period X │
└──────────────────────────────────────────────────────────────┘
```

- Add a dashboard **filter action**: clicking a hospital on the map highlights it on the funnel plot.
- Add a short "How to read this" text box: ERR < 1 = fewer readmissions than expected; points outside the funnel lines are statistically unusual.

## 4. Publish

File → **Save to Tableau Public** → sign in → name it "Washington Hospital Readmissions." Then on your Tableau Public profile:
- Add a description that links to the GitHub repo.
- Set the dashboard as **Featured** on your profile.
- Copy the URL into the README's "Interactive dashboard" link.
