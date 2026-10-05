# Notebook slots

The notebook fills each slot below after a full run. This list moved here unchanged from the end of README.md.

```text
Notebook slots. Every nb:KEY marker pair in this file (and every <tspan id="nb-KEY"> in docs/*.svg)
holds the single character "…" until the notebook writes the measured value in its place. Each slot
holds the bare value only: no unit, no "%" sign and no "EGP" (those are written outside the slot).
Counts are whole numbers with thousands separators; percentages have one decimal; prices per m² are
whole EGP with thousands separators; dates are written like 4 October 2026. A slot marker never
starts a line (GitHub would end the paragraph there), so keep a word before it when reflowing. Unless a line says
otherwise, "latest run week" is the newest week in gold.dim_week.

README.md
listings_compared                 count of competing listings (gold.fact_listing_price rows) in the latest run week in the six areas
sites_read                        count of sites with at least one row in gold.fact_listing_price in the latest run week
areas_read                        count of areas with at least one row in gold.fact_listing_price in the latest run week
widest_gap_area                   area name (as in silver.area) where our units' median price per m² is furthest from the area median, latest run week
widest_gap_pct                    that gap in percent, signed (+ means we ask more than the area median)
price_observations                count of rows in silver.price_observation, all run weeks
run_weeks                         count of run weeks in silver.price_observation
first_run_week                    the earliest run week, as a date
latest_run_week                   the latest run week, as a date
compounds_covered                 count of distinct compounds in gold.dim_compound with at least one listing
developers_covered                count of distinct developers in gold.dim_compound with at least one listing
our_units                         count of rows in gold.fact_our_unit
share_listings_cheaper_than_ours  percent of competing listings, latest run week, whose price per m² is below that of our median unit of the same type in the same area
price_cuts                        count of listings in gold.price_change whose price per m² fell between the run week before the latest and the latest
quarantined_rows                  count of rows in silver.quarantine, all run weeks
quarantine_share_pct              quarantined rows as a percent of all rows read (silver.price_observation plus silver.quarantine)
run_minutes                       minutes of the latest successful DAG run, start to end

docs/header.svg
listings_compared, widest_gap_pct, widest_gap_area, sites_read, areas_read   as above

docs/price-gap-by-area.svg (the notebook redraws this file, positions included)
scale_min_m2                      left end of the shared price-per-m² scale, EGP
scale_max_m2                      right end of the shared price-per-m² scale, EGP
median_m2_<area>                  area median price per m² of competing listings, EGP, latest run week
gap_pct_<area>                    our units' median price per m² against that area median, percent, signed
share_cheaper_<area>              percent of that area's competing listings asking less per m² than our median unit
  where <area> is one of: new_cairo, new_capital, sheikh_zayed, sixth_october, north_coast, mostakbal_city
```
