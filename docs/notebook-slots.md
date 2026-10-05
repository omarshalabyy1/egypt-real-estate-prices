# Notebook slots

The notebook fills each slot below after a full run. This list moved here unchanged from the end of README.md.

```text
Notebook slots. Every nb:KEY marker pair in README.md and powerbi/06-checks.md (and its copies in
powerbi/08-build-checklist.md, and every
<tspan id="nb-KEY"> in docs/*.svg) holds the single character "…" until the notebook writes the
measured value in its place. Each slot holds the bare value only: no unit, no "%" sign and no currency
(those are written outside the slot). A text slot is the exception: an area name, a phrase built in
the notebook (run_weeks_phrase) or a list of rows for a Power BI check is written as it is, and a
value the warehouse has not got yet is written "(Blank)", as Power BI shows it.
Counts are whole numbers with thousands separators; percentages have one decimal; prices per m² are
whole units of client.currency with thousands separators; dates are written like 4 October 2026. A slot marker never
starts a line (GitHub would end the paragraph there), so keep a word before it when reflowing. Unless a line says
otherwise, "latest run week" is the newest week in gold.dim_week.

README.md
listings_compared                 count of distinct competing listings in the latest run week in the six areas, pooled over sites
                                  (gold.pooled_listing_price rows: without the Bayut Egypt rows that copy a Dubizzle ad);
                                  the notebook asserts it equals pooled_listings
asking_prices_kept                not a slot (numbers.json only): count of gold.fact_listing_price rows in the latest run week,
                                  one per site and listing, the Bayut Egypt copies of Dubizzle ads included
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
live_read_minutes_estimate        an estimate, not a measured time: for each automated site (realestate, propertyfinder,
                                  dubizzle, nawy) the pages it read in the latest run week (silver.run_log pages_read, summed
                                  over its areas) times its pace_seconds, over 60; the sites are read in parallel, so the
                                  slowest decides
live_read_request_seconds         seconds between two requests to that site, its pace_seconds in config/client.yaml

README.md, from the notebook's Insights (each slot i<n>_<key> is insights.<n>.<key> in numbers.json; latest run week,
pooled over sites in gold.pooled_listing_price; a group needs 10 or more listings)
i1_premium_pct, i1_dearest_area, i1_cheapest_area
                                  the areas with the highest and the lowest median asking price per m² over all types, and the
                                  first's median above the second's, percent
i5_types_lower_in_largest_band, i5_types_compared
                                  unit types with two or more size bands of 10 or more listings, and of those, the count whose
                                  largest band's median price per m² is below its smallest band's
i3_top_index, i3_top_developer, i3_bottom_index, i3_bottom_developer, i3_developers
                                  each developer's index: the median of its listings' price per m² over their area's median, times
                                  100 (whole number); the highest and the lowest, and the count of developers measured
i6_nawy_above_areas, i6_areas_compared
                                  areas where Nawy and Dubizzle Egypt each have 10 or more listings (each site's own rows), and of
                                  those, the count where Nawy's median price per m² is the higher
i7_twin_share_pct                 an estimate: percent of pooled listings with a named compound that match a listing on another site
                                  in the same area and compound (case ignored), of the same type, size within 2 m², asking price
                                  within 2% of the lower of the two
i10_widest_p90_over_p10_pct, i10_widest_area, i10_narrowest_p90_over_p10_pct, i10_narrowest_area
                                  per area, all types pooled: the 90th percentile of price per m² above the 10th, percent;
                                  the areas where it is the highest and the lowest
i11_lowest_read_pct, i11_lowest_site, i11_highest_read_pct, i11_highest_site
                                  per site, silver.run_log rows_parsed over stated_total summed over the areas asked, percent;
                                  the lowest and the highest, with the site
i12_top_reason, i12_top_reason_rows
                                  the quarantine reason with the most rows in silver.quarantine, latest run week, and its rows

docs/header.svg
listings_compared, widest_gap_pct, widest_gap_area, sites_read, areas_read   as above

docs/price-gap-by-area.svg (the notebook redraws this file, positions included)
scale_min_m2                      left end of the shared price-per-m² scale, EGP
scale_max_m2                      right end of the shared price-per-m² scale, EGP
median_m2_<area>                  area median price per m² of competing listings over all unit types, EGP, latest run week (the tick)
gap_pct_<area>                    gold.area_gap.median_gap_pct: the median of our units' gaps in that area, each unit against the
                                  median of the same type in the same area, percent, signed
share_cheaper_<area>              percent of that area's competing listings asking less per m² than our median unit
  where <area> is an area id in config/client.yaml with _ for -: new_cairo, new_administrative_capital, sheikh_zayed,
  sixth_october_city, north_coast, mostakbal_city for the demo. The notebook redraws the file only when its strips are
  the config's areas; another client's areas need their strips drawn once (docs/new-client.md)

powerbi/06-checks.md (each value is what the SQL under its check returns, run by the notebook as printed;
where a key above holds the same number, the notebook asserts that the two agree)
latest_run_week, run_weeks_phrase, our_units, widest_gap_area, units_without_comparison, listings_in_our_types,
share_listings_cheaper_than_ours
                                  as above
pooled_listings                   count of gold.pooled_listing_price rows in the latest run week (the table the report loads as
                                  Listing Price: without the Bayut Egypt rows that copy a Dubizzle ad)
price_changes                     rows of gold.price_change, all run weeks
table_rows_<table>                C2: rows of each gold table the report loads (site, area, compound, property_type, week,
                                  listing_price, our_unit, price_change, area_benchmark, area_site_benchmark, unit_gap, area_gap)
units_above_market_pct            C3: percent of our units with a comparison whose gap_pct is above 0 (gold.unit_gap)
units_below_market_pct            C3: the same, at or below 0
area_bar_labels                   C4: each area's median_gap_pct, highest first, as text
map_bubbles, map_biggest_area     C5: areas with listings in the latest run week and coordinates; the area with the most listings
units_top_by_gap                  C6: the five units with the highest gap_pct, as text
check_area_name                   the name of report.check_area in config/client.yaml (the demo: New Cairo); the pipeline
                                  sets it on the database as client.check_area, which the SQL of C7, C13 and C18 reads
check_area_our_units, check_area_units_above_pct, check_area_units_below_pct, check_area_listings,
check_area_share_cheaper_pct      C7: the C3 values for the check area (listings: its competing listings, latest run week;
                                  the share is share_cheaper_<area> of that area)
dubizzle_units_above_pct, dubizzle_units_below_pct, dubizzle_share_cheaper_pct, dubizzle_widest_gap_area, dubizzle_listings
                                  C8: the C3 values with every unit compared with Dubizzle Egypt's listings only
compounds_latest_week, developers_latest_week, cheapest_compound, dearest_compound
                                  C9: named compounds and developers with a listing in the latest run week; the compounds with
                                  the lowest and highest median price per m²
matrix_first_compounds            C10: the compounds of the first ten compound and type rows, sorted by compound
dearest_developers                C11: the three developers with the highest median price per m², latest run week
band_table_top_rows               C12: the five area and type rows of gold.area_benchmark with the most listings
check_area_compounds, check_area_developers, check_area_cheapest_compound, check_area_dearest_compound
                                  C13: the C9 values for the check area
cuts_all_weeks, rises_all_weeks, average_change_pct
                                  C14: cuts, rises and the average change_pct in gold.price_change, all run weeks
                                  (price_cuts above counts the latest run week only)
weeks_with_changes                C15: run weeks with at least one row in gold.price_change
deepest_cut_old_m2, deepest_cut_new_m2, deepest_cut_ours_m2
                                  C16: the deepest cut's price per m² before and after, and our units' median of its type and area
deepest_cuts                      C17: the five rows of gold.price_change with the lowest change_pct, as text
check_area_price_changes, check_area_cuts, check_area_rises
                                  C18: the C14 counts for the check area
```
