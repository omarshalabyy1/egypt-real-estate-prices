# 6. Checks: the numbers the report must show

Every value below is filled in by `analysis/analysis.ipynb` after a weekly run (the values written
here are for the run week of <!--nb:latest_run_week-->4 October 2026<!--/nb-->): the notebook runs the SQL under each check as
printed and keeps the result in `analysis/numbers.json`, so the SQL gives the same value. Check
with no slicer selected unless a check says otherwise. If a card is off, the usual causes are a
missing relationship, a wrong column type in Power Query, or a filter left on a slicer.

Every query reads the gold layer only, as the report does. Where a gold view already holds the
answer pooled over every site, the check reads the view: with no slicer selected, the report's
measures must equal it. Where a check picks one site, the SQL recomputes from
`gold.fact_listing_price`, as the measures do. The share of listings cheaper than ours is
recomputed from the fact too: of the competing listings in the areas and unit types where we have
units, the share asking less per m² than our median unit of that type and area, the definition the
README uses; no gold view holds it. The README counts it over the listings pooled over sites, without
the Bayut Egypt rows that copy a Dubizzle ad; the report and the SQL here count every fact row, so
the two can differ by those rows.

**Building on a later date?** The sites show today's asking prices, so every weekly run changes the
latest week and the numbers move. Run the notebook once, or the SQL under each check, and compare
the report with those, not with the numbers written here.

**The first week:** checks C14 to C18 (page 3) need two weekly runs. After the first run they show
no changes at all, which is correct: one run has no earlier price to compare with.

Run the SQL in any SQL tool on `127.0.0.1:5451`, database `prices`, user `prices`, or with
`docker compose exec warehouse psql -U prices -d prices`.

## The warehouse, before Power BI

**C1.** The runs are in: <!--nb:run_weeks_phrase-->1 weekly run<!--/nb-->, the latest one the week
of <!--nb:latest_run_week-->4 October 2026<!--/nb-->, with <!--nb:listings_compared-->5,757<!--/nb--> asking prices in it (one per site and listing).

```sql
SELECT count(*) AS run_weeks, max(week_key) AS latest_week,
       (SELECT count(*) FROM gold.fact_listing_price
        WHERE week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS prices_latest_week
FROM gold.dim_week;
```

**C2.** Rows per table after **Close & apply** (Table view, bottom left): Site <!--nb:table_rows_site-->6<!--/nb--> ·
Area <!--nb:table_rows_area-->6<!--/nb--> · Compound <!--nb:table_rows_compound-->1,336<!--/nb--> · Property Type <!--nb:table_rows_property_type-->11<!--/nb--> ·
Week <!--nb:table_rows_week-->1<!--/nb--> · Listing Price <!--nb:table_rows_listing_price-->5,757<!--/nb--> · Our Unit <!--nb:table_rows_our_unit-->60<!--/nb--> ·
Price Change <!--nb:table_rows_price_change-->0<!--/nb--> · Area Benchmark <!--nb:table_rows_area_benchmark-->55<!--/nb--> ·
Area Site Benchmark <!--nb:table_rows_area_site_benchmark-->234<!--/nb--> · Unit Gap <!--nb:table_rows_unit_gap-->60<!--/nb--> ·
Area Gap <!--nb:table_rows_area_gap-->6<!--/nb-->.

```sql
SELECT (SELECT count(*) FROM gold.dim_site) AS site, (SELECT count(*) FROM gold.dim_area) AS area,
       (SELECT count(*) FROM gold.dim_compound) AS compound,
       (SELECT count(*) FROM gold.dim_property_type) AS property_type,
       (SELECT count(*) FROM gold.dim_week) AS week,
       (SELECT count(*) FROM gold.fact_listing_price) AS listing_price,
       (SELECT count(*) FROM gold.fact_our_unit) AS our_unit,
       (SELECT count(*) FROM gold.price_change) AS price_change,
       (SELECT count(*) FROM gold.area_benchmark) AS area_benchmark,
       (SELECT count(*) FROM gold.area_site_benchmark) AS area_site_benchmark,
       (SELECT count(*) FROM gold.unit_gap) AS unit_gap, (SELECT count(*) FROM gold.area_gap) AS area_gap;
```

## Page 1: Market position

**C3.** Cards, no slicer: Our units <!--nb:our_units-->60<!--/nb--> · Above market <!--nb:units_above_market_pct-->58.3<!--/nb-->% · At or
below market <!--nb:units_below_market_pct-->41.7<!--/nb-->% · Listings cheaper than ours <!--nb:report_share_cheaper_pct-->50.7<!--/nb-->%
(measure `Share Of Listings Cheaper Than Ours`: of the <!--nb:report_listings_in_our_types-->5,066<!--/nb--> competing listings in
the areas and types where we have units, the share asking less per m² than our median unit of that
type and area) · Widest gap <!--nb:widest_gap_area-->6th of October<!--/nb--> · Competitor listings this week <!--nb:listings_compared-->5,757<!--/nb-->.

```sql
WITH ours AS (
    SELECT area_key, type_key, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS our_median
    FROM gold.fact_our_unit GROUP BY area_key, type_key
), compared AS (
    SELECT count(*) AS listings_in_our_types,
           count(*) FILTER (WHERE f.price_per_m2 < o.our_median) AS listings_cheaper
    FROM gold.fact_listing_price f JOIN ours o USING (area_key, type_key)
    WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
)
SELECT count(*) AS our_units,
       round(count(*) FILTER (WHERE gap_pct > 0) * 100.0 / nullif(count(gap_pct), 0), 1) AS share_above_pct,
       round(count(*) FILTER (WHERE gap_pct <= 0) * 100.0 / nullif(count(gap_pct), 0), 1) AS share_below_pct,
       (SELECT listings_in_our_types FROM compared) AS listings_in_our_types,
       (SELECT listings_cheaper FROM compared) AS listings_cheaper,
       (SELECT round(listings_cheaper * 100.0 / nullif(listings_in_our_types, 0), 1) FROM compared) AS share_cheaper_pct,
       (SELECT a.name FROM gold.area_gap g JOIN gold.dim_area a USING (area_key)
        WHERE g.gap_rank = 1 ORDER BY a.name DESC LIMIT 1) AS widest_gap_area,
       (SELECT count(*) FROM gold.fact_listing_price
        WHERE week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.unit_gap;
```

**C4.** Area bar (#11) data labels, top to bottom: <!--nb:area_bar_labels-->6th of October 7.4%, Sheikh Zayed 2.8%, New Capital 1.9%, North Coast -0.1%, Mostakbal City -0.6%, New Cairo -0.7%<!--/nb--> (six areas, or fewer if
an area has no unit with a comparison).

```sql
SELECT a.name, g.units_compared, g.median_gap_pct
FROM gold.area_gap g JOIN gold.dim_area a USING (area_key)
ORDER BY g.median_gap_pct DESC NULLS LAST;
```

**C5.** Map (#10): one bubble on each area, <!--nb:map_bubbles-->6<!--/nb--> in all, the biggest on <!--nb:map_biggest_area-->North Coast<!--/nb-->.
Hover each bubble: its Listings is the `listings` below. If a bubble is missing, its `lat` or `lon`
is blank below: note the area and say so before going on.

```sql
SELECT a.name, a.lat, a.lon, count(f.listing_id) AS listings
FROM gold.dim_area a
LEFT JOIN gold.fact_listing_price f
       ON f.area_key = a.area_key AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
GROUP BY a.name, a.lat, a.lon ORDER BY listings DESC;
```

**C6.** Units table (#12), sorted by Gap descending: the top rows are <!--nb:units_top_by_gap-->NC-VIL-02 (15.0%), NC-VIL-01 (14.4%), SZ-APT-03 (13.9%), MC-TH-01 (13.8%), NCO-VIL-01 (13.7%)<!--/nb-->.
Its <!--nb:our_units-->60<!--/nb--> rows match Our units in C3, and <!--nb:units_without_comparison-->0<!--/nb--> of them have a blank Gap.

```sql
SELECT g.unit_code, a.name AS area, t.unit_type, c.compound, g.price_per_m2, g.median_price_per_m2,
       g.gap_pct, g.listings_compared, g.pct_listings_cheaper
FROM gold.unit_gap g
JOIN gold.dim_area a USING (area_key)
JOIN gold.dim_property_type t USING (type_key)
JOIN gold.dim_compound c USING (compound_key)
ORDER BY g.gap_pct DESC NULLS LAST LIMIT 5;

SELECT count(*) AS units, count(*) FILTER (WHERE gap_pct IS NULL) AS no_comparison FROM gold.unit_gap;
```

**C7.** Area slicer (#3) on **New Cairo**: Our units <!--nb:new_cairo_our_units-->10<!--/nb--> · Above
market <!--nb:new_cairo_units_above_pct-->50.0<!--/nb-->% · At or below market <!--nb:new_cairo_units_below_pct-->50.0<!--/nb-->% · Listings cheaper
than ours <!--nb:report_share_cheaper_new_cairo_pct-->52.2<!--/nb-->% · Competitor listings this week <!--nb:new_cairo_listings-->939<!--/nb-->. Clear the
slicer.

```sql
WITH ours AS (
    SELECT u.area_key, u.type_key, percentile_cont(0.5) WITHIN GROUP (ORDER BY u.price_per_m2) AS our_median
    FROM gold.fact_our_unit u JOIN gold.dim_area a USING (area_key)
    WHERE a.area_id = 'new-cairo' GROUP BY u.area_key, u.type_key
)
SELECT count(*) AS our_units,
       round(count(*) FILTER (WHERE g.gap_pct > 0) * 100.0 / nullif(count(g.gap_pct), 0), 1) AS share_above_pct,
       round(count(*) FILTER (WHERE g.gap_pct <= 0) * 100.0 / nullif(count(g.gap_pct), 0), 1) AS share_below_pct,
       (SELECT round(count(*) FILTER (WHERE f.price_per_m2 < o.our_median) * 100.0 / nullif(count(*), 0), 1)
        FROM gold.fact_listing_price f JOIN ours o USING (area_key, type_key)
        WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS share_cheaper_pct,
       (SELECT count(*) FROM gold.fact_listing_price f JOIN gold.dim_area fa USING (area_key)
        WHERE fa.area_id = 'new-cairo'
          AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.unit_gap g JOIN gold.dim_area a USING (area_key)
WHERE a.area_id = 'new-cairo';
```

**C8.** Site slicer (#2) on **Dubizzle Egypt**: Our units <!--nb:our_units-->60<!--/nb--> (unchanged: our units
are not on a site) · Above market <!--nb:dubizzle_units_above_pct-->91.5<!--/nb-->% · At or below
market <!--nb:dubizzle_units_below_pct-->8.5<!--/nb-->% · Listings cheaper than ours <!--nb:dubizzle_share_cheaper_pct-->63.7<!--/nb-->% · Widest
gap <!--nb:dubizzle_widest_gap_area-->Mostakbal City<!--/nb--> · Competitor listings this week <!--nb:dubizzle_listings-->2,150<!--/nb-->. Every unit is now
compared with Dubizzle's listings only, and only Dubizzle's listings are counted as cheaper, so this
is recomputed from the fact. Clear the slicer.

```sql
WITH latest AS (
    SELECT f.area_key, f.type_key, f.price_per_m2
    FROM gold.fact_listing_price f JOIN gold.dim_site s USING (site_key)
    WHERE s.source = 'dubizzle' AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
), ours AS (
    SELECT area_key, type_key, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS our_median
    FROM gold.fact_our_unit GROUP BY area_key, type_key
), per_unit AS (
    SELECT u.unit_code, u.area_key, u.price_per_m2,
           (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price_per_m2) FROM latest l
            WHERE l.area_key = u.area_key AND l.type_key = u.type_key) AS market
    FROM gold.fact_our_unit u
), by_area AS (
    SELECT a.name, percentile_cont(0.5) WITHIN GROUP (ORDER BY (p.price_per_m2 - p.market) / p.market) AS median_gap
    FROM per_unit p JOIN gold.dim_area a USING (area_key)
    WHERE p.market IS NOT NULL GROUP BY a.name
)
SELECT count(*) AS our_units, count(market) AS units_compared,
       round(count(*) FILTER (WHERE price_per_m2 > market) * 100.0 / nullif(count(market), 0), 1) AS share_above_pct,
       round(count(*) FILTER (WHERE price_per_m2 <= market) * 100.0 / nullif(count(market), 0), 1) AS share_below_pct,
       (SELECT round(count(*) FILTER (WHERE l.price_per_m2 < o.our_median) * 100.0 / nullif(count(*), 0), 1)
        FROM latest l JOIN ours o USING (area_key, type_key)) AS share_cheaper_pct,
       (SELECT name FROM by_area ORDER BY abs(median_gap) DESC, name DESC LIMIT 1) AS widest_gap_area,
       (SELECT count(*) FROM latest) AS listings
FROM per_unit;
```

## Page 2: Compounds and developers

**C9.** Cards, no slicer: Listings this week <!--nb:listings_compared-->5,757<!--/nb--> (equal to Competitor listings
this week in C3) · Compounds <!--nb:compounds_latest_week-->1,152<!--/nb--> · Developers <!--nb:developers_latest_week-->307<!--/nb--> ·
Cheapest compound per m² <!--nb:cheapest_compound-->Haram City Compound<!--/nb--> · Dearest compound per m² <!--nb:dearest_compound-->Yemm Views<!--/nb-->.

```sql
WITH latest AS (
    SELECT c.compound, c.developer, f.price_per_m2
    FROM gold.fact_listing_price f JOIN gold.dim_compound c USING (compound_key)
    WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
), by_compound AS (
    SELECT compound, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS median_per_m2
    FROM latest WHERE compound <> 'Unknown' GROUP BY compound
)
SELECT (SELECT count(*) FROM latest) AS listings,
       (SELECT count(DISTINCT compound) FROM latest WHERE compound <> 'Unknown') AS compounds,
       (SELECT count(DISTINCT developer) FROM latest WHERE developer <> 'Unknown') AS developers,
       (SELECT compound FROM by_compound ORDER BY median_per_m2, compound DESC LIMIT 1) AS cheapest_compound,
       (SELECT compound FROM by_compound ORDER BY median_per_m2 DESC, compound DESC LIMIT 1) AS dearest_compound;
```

**C10.** Matrix (#9), sorted by compound: the first rows are <!--nb:matrix_first_compounds-->11th District, 13th District, 16th District, 1st District, 205 Arkan Palm, 205 Towers, 2nd District, 31 West<!--/nb-->, with
their median per m² by unit type as below.

```sql
SELECT c.compound, t.unit_type, count(*) AS listings,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.price_per_m2))::numeric, 0) AS median_per_m2
FROM gold.fact_listing_price f
JOIN gold.dim_compound c USING (compound_key)
JOIN gold.dim_property_type t USING (type_key)
WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
GROUP BY c.compound, t.unit_type ORDER BY c.compound, t.unit_type LIMIT 10;
```

**C11.** Developer bar (#10), top to bottom: the dearest three are <!--nb:dearest_developers-->Mercon Developments, Melee Development, Mercon<!--/nb-->.

```sql
SELECT c.developer, count(*) AS listings,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.price_per_m2))::numeric, 0) AS median_per_m2
FROM gold.fact_listing_price f JOIN gold.dim_compound c USING (compound_key)
WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
GROUP BY c.developer ORDER BY median_per_m2 DESC LIMIT 3;
```

**C12.** Market band table (#11), sorted by Listings descending: the top rows
are <!--nb:band_table_top_rows-->North Coast Chalet (458 listings), Mostakbal City Apartment (448 listings), New Capital Apartment (423 listings), New Cairo Apartment (398 listings), 6th of October Apartment (395 listings)<!--/nb-->, with their lower quarter, median and upper quarter per m² as below.

```sql
SELECT a.name AS area, t.unit_type, b.listings, b.p25_price_per_m2, b.median_price_per_m2,
       b.p75_price_per_m2
FROM gold.area_benchmark b
JOIN gold.dim_area a USING (area_key)
JOIN gold.dim_property_type t USING (type_key)
ORDER BY b.listings DESC, a.name, t.unit_type LIMIT 5;
```

**C13.** Area slicer (#3) on **New Cairo**: Listings this week <!--nb:new_cairo_listings-->939<!--/nb--> ·
Compounds <!--nb:new_cairo_compounds-->295<!--/nb--> · Developers <!--nb:new_cairo_developers-->81<!--/nb--> · Cheapest compound per
m² <!--nb:new_cairo_cheapest_compound-->Shalya Taj City<!--/nb--> · Dearest compound per m² <!--nb:new_cairo_dearest_compound-->WBR1<!--/nb-->. Clear the slicer.

```sql
WITH latest AS (
    SELECT c.compound, c.developer, f.price_per_m2
    FROM gold.fact_listing_price f
    JOIN gold.dim_compound c USING (compound_key)
    JOIN gold.dim_area a USING (area_key)
    WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price) AND a.area_id = 'new-cairo'
), by_compound AS (
    SELECT compound, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS median_per_m2
    FROM latest WHERE compound <> 'Unknown' GROUP BY compound
)
SELECT (SELECT count(*) FROM latest) AS listings,
       (SELECT count(DISTINCT compound) FROM latest WHERE compound <> 'Unknown') AS compounds,
       (SELECT count(DISTINCT developer) FROM latest WHERE developer <> 'Unknown') AS developers,
       (SELECT compound FROM by_compound ORDER BY median_per_m2, compound DESC LIMIT 1) AS cheapest_compound,
       (SELECT compound FROM by_compound ORDER BY median_per_m2 DESC, compound DESC LIMIT 1) AS dearest_compound;
```

## Page 3: Weekly changes

From the second weekly run on. After the first run, C14 shows "(Blank)" on the four change cards.

**C14.** Cards, no slicer: Price changes <!--nb:price_changes-->0<!--/nb--> · Cuts <!--nb:cuts_all_weeks-->0<!--/nb--> ·
Rises <!--nb:rises_all_weeks-->0<!--/nb--> · Average change, in percent, <!--nb:average_change_pct-->(Blank)<!--/nb--> · Listings seen this
week <!--nb:listings_compared-->5,757<!--/nb-->.

```sql
SELECT count(*) AS price_changes, count(*) FILTER (WHERE is_cut) AS cuts,
       count(*) FILTER (WHERE NOT is_cut) AS rises, round(avg(change_pct), 1) AS average_change_pct,
       (SELECT count(*) FROM gold.fact_listing_price
        WHERE week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.price_change;
```

**C15.** Column chart (#10): run weeks with a bar, <!--nb:weeks_with_changes-->0<!--/nb-->; per run week, cuts and
rises as below.

```sql
SELECT week_key, count(*) FILTER (WHERE is_cut) AS cuts, count(*) FILTER (WHERE NOT is_cut) AS rises
FROM gold.price_change GROUP BY week_key ORDER BY week_key;
```

**C16.** Site slicer (#2) on the site and Listing slicer (#4) on the id named in C17 (the deepest
cut): the line chart (#11) shows its price per m² at <!--nb:deepest_cut_old_m2-->(Blank)<!--/nb--> before
and <!--nb:deepest_cut_new_m2-->(Blank)<!--/nb--> after, and the dashed line for our units of the same type and area is
at <!--nb:deepest_cut_ours_m2-->(Blank)<!--/nb--> (missing if we have none). The cards do not change (C14). Clear both slicers:
the line chart is empty again.

```sql
-- Replace 'dubizzle' and '0' with the site and the listing id picked.
SELECT f.week_key, f.price_per_m2,
       (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY u.price_per_m2)
        FROM gold.fact_our_unit u
        WHERE u.area_key = f.area_key AND u.type_key = f.type_key) AS ours_same_type_per_m2
FROM gold.fact_listing_price f JOIN gold.dim_site s USING (site_key)
WHERE s.source = 'dubizzle' AND f.listing_id = '0'
ORDER BY f.week_key;
```

**C17.** Table (#12), sorted by Change % ascending: the top rows are <!--nb:deepest_cuts-->no rows yet<!--/nb-->, the
deepest cuts. Its <!--nb:price_changes-->0<!--/nb--> rows match Price changes in C14.

```sql
SELECT c.listing_id, s.name AS site, a.name AS area, k.compound, k.developer, t.unit_type,
       c.old_week_key, c.week_key, c.old_price_per_m2, c.new_price_per_m2, c.change_pct
FROM gold.price_change c
JOIN gold.dim_site s USING (site_key)
JOIN gold.dim_area a USING (area_key)
JOIN gold.dim_compound k USING (compound_key)
JOIN gold.dim_property_type t USING (type_key)
ORDER BY c.change_pct LIMIT 5;
```

**C18.** Area slicer (#3) on **New Cairo**: Price changes <!--nb:new_cairo_price_changes-->0<!--/nb--> ·
Cuts <!--nb:new_cairo_cuts-->0<!--/nb--> · Rises <!--nb:new_cairo_rises-->0<!--/nb--> · Listings seen this week <!--nb:new_cairo_listings-->939<!--/nb-->.
Clear the slicer.

```sql
SELECT count(*) AS price_changes, count(*) FILTER (WHERE c.is_cut) AS cuts,
       count(*) FILTER (WHERE NOT c.is_cut) AS rises,
       (SELECT count(*) FROM gold.fact_listing_price f JOIN gold.dim_area fa USING (area_key)
        WHERE fa.area_id = 'new-cairo'
          AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.price_change c JOIN gold.dim_area a USING (area_key)
WHERE a.area_id = 'new-cairo';
```
