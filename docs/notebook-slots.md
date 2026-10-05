# Notebook slots

The notebook fills each slot below after a full run. This list moved here unchanged from the end of README.md.

```text
Notebook slots. Every nb:KEY marker pair in README.md and powerbi/06-checks.md (and its copies in
powerbi/08-build-checklist.md, and every
<tspan id="nb-KEY"> in docs/*.svg) holds the single character "…" until the notebook writes the
measured value in its place. Each slot holds the bare value only: no unit, no "%" sign and no "EGP"
(those are written outside the slot). A text slot is the exception: an area name, a phrase built in
the notebook (run_weeks_phrase) or a list of rows for a Power BI check is written as it is, and a
value the warehouse has not got yet is written "(Blank)", as Power BI shows it.
Counts are whole numbers with thousands separators; percentages have one decimal; prices per m² are
whole EGP with thousands separators; dates are written like 4 October 2026. A slot marker never
starts a line (GitHub would end the paragraph there), so keep a word before it when reflowing. Unless a line says
otherwise, "latest run week" is the newest week in gold.dim_week.

README.md
listings_compared                 count of competing listings (gold.fact_listing_price rows) in the latest run week in the six areas
sites_read                        count of sites with at least one row in gold.fact_listing_price in the latest run week
areas_read                        count of areas with at least one row in gold.fact_listing_price in the latest run week
widest_gap_area                   area name (as in silver.area) whose gold.area_gap.median_gap_pct is furthest from 0: the median of
                                  each unit's gap against the median of the same type in the same area, latest run week
widest_gap_pct                    that gap in percent, signed (+ means we ask more than the median of the same type in the same area)
price_observations                count of rows in silver.price_observation, all run weeks
run_weeks_phrase                  count of run weeks in silver.price_observation with its noun, built in the notebook:
                                  "1 weekly run", "2 weekly runs"
first_run_week                    the earliest run week, as a date
latest_run_week                   the latest run week, as a date
compounds_covered                 count of distinct compound names (as the sites write them) in gold.dim_compound with at least
                                  one listing, any run week
developers_covered                count of distinct developers in gold.dim_compound with at least one listing
our_units                         count of rows in gold.fact_our_unit
listings_in_our_types             count of competing listings, latest run week, in the areas and unit types where we have a unit,
                                  pooled over sites (gold.pooled_listing_price: without the Bayut Egypt rows that copy a Dubizzle ad)
share_listings_cheaper_than_ours  percent of those listings whose price per m² is below that of our median unit of that type and area
price_cuts                        count of listings in gold.price_change whose price per m² fell between the run week before the latest and the latest
quarantined_rows                  count of rows in silver.quarantine, all run weeks
quarantine_share_pct              quarantined rows as a percent of all rows read (silver.price_observation plus silver.quarantine)
live_read_minutes_estimate        an estimate, not a measured time: the most pages one automated site (realestate, propertyfinder,
                                  dubizzle, nawy) read in the latest run week (silver.run_log pages_read, summed over its areas),
                                  times live_read_request_seconds, over 60; the sites are read in parallel, so the slowest decides
live_read_request_seconds         seconds between two requests, DELAY in tracker.py and sites.py

README.md, from the notebook's Insights (each slot i<n>_<key> is insights.<n>.<key> in numbers.json; latest run week,
pooled over sites in gold.pooled_listing_price; a group needs 10 or more listings)
i1_premium_pct, i1_dearest_area, i1_cheapest_area
                                  the areas with the highest and the lowest median asking price per m² over all types, and the
                                  first's median above the second's, percent
i2_gap_pct, i2_area, i2_dearest_type, i2_cheapest_type
                                  the area whose dearest and cheapest unit type (median price per m²) are furthest apart, the two
                                  types, and the dearest's median above the cheapest's, percent
i3_top_index, i3_top_developer, i3_bottom_index, i3_bottom_developer, i3_developers
                                  each developer's index: the median of its listings' price per m² over their area's median, times
                                  100 (whole number); the highest and the lowest, and the count of developers measured
i6_nawy_above_areas, i6_areas_compared
                                  areas where Nawy and Dubizzle Egypt each have 10 or more listings (each site's own rows), and of
                                  those, the count where Nawy's median price per m² is the higher
i7_twin_share_pct                 an estimate: percent of pooled listings with a named compound that match a listing on another site
                                  in the same area and compound (case ignored), of the same type, size within 2 m², asking price
                                  within 2% of the lower of the two

docs/header.svg
listings_compared, widest_gap_pct, widest_gap_area, sites_read, areas_read   as above

docs/price-gap-by-area.svg (the notebook redraws this file, positions included)
scale_min_m2                      left end of the shared price-per-m² scale, EGP
scale_max_m2                      right end of the shared price-per-m² scale, EGP
median_m2_<area>                  area median price per m² of competing listings over all unit types, EGP, latest run week (the tick)
gap_pct_<area>                    gold.area_gap.median_gap_pct: the median of our units' gaps in that area, each unit against the
                                  median of the same type in the same area, percent, signed
share_cheaper_<area>              percent of that area's competing listings asking less per m² than our median unit
  where <area> is one of: new_cairo, new_capital, sheikh_zayed, sixth_october, north_coast, mostakbal_city

powerbi/06-checks.md (each value is what the SQL under its check returns, run by the notebook as printed;
where a key above holds the same number, the notebook asserts that the two agree)
latest_run_week, run_weeks_phrase, listings_compared, our_units, widest_gap_area, units_without_comparison
                                  as above
report_share_cheaper_pct, report_listings_in_our_types
                                  C3: share_listings_cheaper_than_ours and listings_in_our_types as the report counts them, over
                                  every gold.fact_listing_price row (the Bayut Egypt copies of Dubizzle ads included)
report_share_cheaper_new_cairo_pct
                                  C7: share_cheaper_new_cairo counted the same way
price_changes                     rows of gold.price_change, all run weeks
table_rows_<table>                C2: rows of each gold table the report loads (site, area, compound, property_type, week,
                                  listing_price, our_unit, price_change, area_benchmark, area_site_benchmark, unit_gap, area_gap)
units_above_market_pct            C3: percent of our units with a comparison whose gap_pct is above 0 (gold.unit_gap)
units_below_market_pct            C3: the same, at or below 0
area_bar_labels                   C4: each area's median_gap_pct, highest first, as text
map_bubbles, map_biggest_area     C5: areas with listings in the latest run week and coordinates; the area with the most listings
units_top_by_gap                  C6: the five units with the highest gap_pct, as text
new_cairo_our_units, new_cairo_units_above_pct, new_cairo_units_below_pct, new_cairo_listings
                                  C7: the C3 values for New Cairo (listings: its competing listings, latest run week)
dubizzle_units_above_pct, dubizzle_units_below_pct, dubizzle_share_cheaper_pct, dubizzle_widest_gap_area, dubizzle_listings
                                  C8: the C3 values with every unit compared with Dubizzle Egypt's listings only
compounds_latest_week, developers_latest_week, cheapest_compound, dearest_compound
                                  C9: named compounds and developers with a listing in the latest run week; the compounds with
                                  the lowest and highest median price per m²
matrix_first_compounds            C10: the compounds of the first ten compound and type rows, sorted by compound
dearest_developers                C11: the three developers with the highest median price per m², latest run week
band_table_top_rows               C12: the five area and type rows of gold.area_benchmark with the most listings
new_cairo_compounds, new_cairo_developers, new_cairo_cheapest_compound, new_cairo_dearest_compound
                                  C13: the C9 values for New Cairo
cuts_all_weeks, rises_all_weeks, average_change_pct
                                  C14: cuts, rises and the average change_pct in gold.price_change, all run weeks
                                  (price_cuts above counts the latest run week only)
weeks_with_changes                C15: run weeks with at least one row in gold.price_change
deepest_cut_old_m2, deepest_cut_new_m2, deepest_cut_ours_m2
                                  C16: the deepest cut's price per m² before and after, and our units' median of its type and area
deepest_cuts                      C17: the five rows of gold.price_change with the lowest change_pct, as text
new_cairo_price_changes, new_cairo_cuts, new_cairo_rises
                                  C18: the C14 counts for New Cairo
```
