# 6. Checks: the numbers the report must show

Every number below is written `[from the notebook]` for now: a later step fills each one from
`analysis/analysis.ipynb`, run on the warehouse after a named weekly run, and the SQL under each
check gives the same value. Until then, run the SQL and compare the report with its result. Check
with no slicer selected unless a check says otherwise. If a card is off, the usual causes are a
missing relationship, a wrong column type in Power Query, or a filter left on a slicer.

Every query reads the gold layer only, as the report does. Where a gold view already holds the
answer pooled over every site, the check reads the view: with no slicer selected, the report's
measures must equal it. Where a check picks one site, the SQL recomputes from
`gold.fact_listing_price`, as the measures do.

**Building on a later date?** The sites show today's asking prices, so every weekly run changes the
latest week and the numbers move. Run the notebook once, or the SQL under each check, and compare
the report with those, not with the numbers written here.

**The first week:** checks C14 to C18 (page 3) need two weekly runs. After the first run they show
no changes at all, which is correct: one run has no earlier price to compare with.

Run the SQL in any SQL tool on `127.0.0.1:5451`, database `prices`, user `prices`, or with
`docker compose exec warehouse psql -U prices -d prices`.

## The warehouse, before Power BI

**C1.** The runs are in: [from the notebook] run weeks, the latest one the week of
[from the notebook], with [from the notebook] asking prices in it (one per site and listing).

```sql
SELECT count(*) AS run_weeks, max(week_key) AS latest_week,
       (SELECT count(*) FROM gold.fact_listing_price
        WHERE week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS prices_latest_week
FROM gold.dim_week;
```

**C2.** Rows per table after **Close & apply** (Table view, bottom left): Site [from the notebook] ·
Area [from the notebook] · Compound [from the notebook] · Property Type [from the notebook] · Week
[from the notebook] · Listing Price [from the notebook] · Our Unit [from the notebook] · Price Change
[from the notebook] · Area Benchmark [from the notebook] · Area Site Benchmark [from the notebook] ·
Unit Gap [from the notebook] · Area Gap [from the notebook].

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

**C3.** Cards, no slicer: Our units [from the notebook] · Above market [from the notebook] · At or
below market [from the notebook] · Listings cheaper than ours [from the notebook] · Widest gap
[from the notebook] · Competitor listings this week [from the notebook].

```sql
SELECT count(*) AS our_units,
       round(count(*) FILTER (WHERE gap_pct > 0) * 100.0 / nullif(count(gap_pct), 0), 1) AS share_above_pct,
       round(count(*) FILTER (WHERE gap_pct <= 0) * 100.0 / nullif(count(gap_pct), 0), 1) AS share_below_pct,
       round(sum(listings_cheaper) * 100.0 / nullif(sum(listings_compared), 0), 1) AS share_cheaper_pct,
       (SELECT a.name FROM gold.area_gap g JOIN gold.dim_area a USING (area_key)
        WHERE g.gap_rank = 1 ORDER BY a.name DESC LIMIT 1) AS widest_gap_area,
       (SELECT count(*) FROM gold.fact_listing_price
        WHERE week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.unit_gap;
```

**C4.** Area bar (#11) data labels, top to bottom: [from the notebook] (six areas, or fewer if an
area has no unit with a comparison).

```sql
SELECT a.name, g.units_compared, g.median_gap_pct
FROM gold.area_gap g JOIN gold.dim_area a USING (area_key)
ORDER BY g.median_gap_pct DESC NULLS LAST;
```

**C5.** Map (#10): [from the notebook] bubbles, one on each area, the biggest on [from the notebook].
Hover each bubble: its Listings is the `listings` below. If a bubble is missing, its `lat` or `lon`
is blank below: note the area and say so before going on.

```sql
SELECT a.name, a.lat, a.lon, count(f.listing_id) AS listings
FROM gold.dim_area a
LEFT JOIN gold.fact_listing_price f
       ON f.area_key = a.area_key AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
GROUP BY a.name, a.lat, a.lon ORDER BY listings DESC;
```

**C6.** Units table (#12), sorted by Gap descending: the top rows are [from the notebook]. Its
[from the notebook] rows match Our units in C3, and [from the notebook] of them have a blank Gap.

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

**C7.** Area slicer (#3) on **New Cairo**: Our units [from the notebook] · Above market
[from the notebook] · At or below market [from the notebook] · Listings cheaper than ours
[from the notebook] · Competitor listings this week [from the notebook]. Clear the slicer.

```sql
SELECT count(*) AS our_units,
       round(count(*) FILTER (WHERE g.gap_pct > 0) * 100.0 / nullif(count(g.gap_pct), 0), 1) AS share_above_pct,
       round(count(*) FILTER (WHERE g.gap_pct <= 0) * 100.0 / nullif(count(g.gap_pct), 0), 1) AS share_below_pct,
       round(sum(g.listings_cheaper) * 100.0 / nullif(sum(g.listings_compared), 0), 1) AS share_cheaper_pct,
       (SELECT count(*) FROM gold.fact_listing_price f JOIN gold.dim_area fa USING (area_key)
        WHERE fa.area_id = 'new-cairo'
          AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.unit_gap g JOIN gold.dim_area a USING (area_key)
WHERE a.area_id = 'new-cairo';
```

**C8.** Site slicer (#2) on **Dubizzle Egypt**: Our units [from the notebook] (unchanged: our units
are not on a site) · Above market [from the notebook] · At or below market [from the notebook] ·
Listings cheaper than ours [from the notebook] · Widest gap [from the notebook] · Competitor listings
this week [from the notebook]. Every unit is now compared with Dubizzle's listings only, so this is
recomputed from the fact. Clear the slicer.

```sql
WITH latest AS (
    SELECT f.area_key, f.type_key, f.price_per_m2
    FROM gold.fact_listing_price f JOIN gold.dim_site s USING (site_key)
    WHERE s.source = 'dubizzle' AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
), per_unit AS (
    SELECT u.unit_code, u.area_key, u.price_per_m2,
           (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price_per_m2) FROM latest l
            WHERE l.area_key = u.area_key AND l.type_key = u.type_key) AS market,
           (SELECT count(*) FROM latest l
            WHERE l.area_key = u.area_key AND l.type_key = u.type_key) AS compared,
           (SELECT count(*) FROM latest l
            WHERE l.area_key = u.area_key AND l.type_key = u.type_key
              AND l.price_per_m2 < u.price_per_m2) AS cheaper
    FROM gold.fact_our_unit u
), by_area AS (
    SELECT a.name, percentile_cont(0.5) WITHIN GROUP (ORDER BY (p.price_per_m2 - p.market) / p.market) AS median_gap
    FROM per_unit p JOIN gold.dim_area a USING (area_key)
    WHERE p.market IS NOT NULL GROUP BY a.name
)
SELECT count(*) AS our_units, count(market) AS units_compared,
       round(count(*) FILTER (WHERE price_per_m2 > market) * 100.0 / nullif(count(market), 0), 1) AS share_above_pct,
       round(count(*) FILTER (WHERE price_per_m2 <= market) * 100.0 / nullif(count(market), 0), 1) AS share_below_pct,
       round(sum(cheaper) * 100.0 / nullif(sum(compared), 0), 1) AS share_cheaper_pct,
       (SELECT name FROM by_area ORDER BY abs(median_gap) DESC, name DESC LIMIT 1) AS widest_gap_area,
       (SELECT count(*) FROM latest) AS listings
FROM per_unit;
```

## Page 2: Compounds and developers

**C9.** Cards, no slicer: Listings this week [from the notebook] (equal to Competitor listings this
week in C3) · Compounds [from the notebook] · Developers [from the notebook] · Cheapest compound per
m² [from the notebook] · Dearest compound per m² [from the notebook].

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

**C10.** Matrix (#9), sorted by compound: the first rows are [from the notebook], with their median
per m² by unit type as below.

```sql
SELECT c.compound, t.unit_type, count(*) AS listings,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.price_per_m2))::numeric, 0) AS median_per_m2
FROM gold.fact_listing_price f
JOIN gold.dim_compound c USING (compound_key)
JOIN gold.dim_property_type t USING (type_key)
WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
GROUP BY c.compound, t.unit_type ORDER BY c.compound, t.unit_type LIMIT 10;
```

**C11.** Developer bar (#10), top to bottom: the dearest three are [from the notebook].

```sql
SELECT c.developer, count(*) AS listings,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.price_per_m2))::numeric, 0) AS median_per_m2
FROM gold.fact_listing_price f JOIN gold.dim_compound c USING (compound_key)
WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)
GROUP BY c.developer ORDER BY median_per_m2 DESC LIMIT 3;
```

**C12.** Market band table (#11), sorted by Listings descending: the top rows are
[from the notebook], with their lower quarter, median and upper quarter per m² as below.

```sql
SELECT a.name AS area, t.unit_type, b.listings, b.p25_price_per_m2, b.median_price_per_m2,
       b.p75_price_per_m2
FROM gold.area_benchmark b
JOIN gold.dim_area a USING (area_key)
JOIN gold.dim_property_type t USING (type_key)
ORDER BY b.listings DESC, a.name, t.unit_type LIMIT 5;
```

**C13.** Area slicer (#3) on **New Cairo**: Listings this week [from the notebook] · Compounds
[from the notebook] · Developers [from the notebook] · Cheapest compound per m² [from the notebook] ·
Dearest compound per m² [from the notebook]. Clear the slicer.

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

**C14.** Cards, no slicer: Price changes [from the notebook] · Cuts [from the notebook] · Rises
[from the notebook] · Average change [from the notebook] · Listings seen this week
[from the notebook].

```sql
SELECT count(*) AS price_changes, count(*) FILTER (WHERE is_cut) AS cuts,
       count(*) FILTER (WHERE NOT is_cut) AS rises, round(avg(change_pct), 1) AS average_change_pct,
       (SELECT count(*) FROM gold.fact_listing_price
        WHERE week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.price_change;
```

**C15.** Column chart (#10): [from the notebook] run weeks have a bar; per run week, cuts and rises
as below.

```sql
SELECT week_key, count(*) FILTER (WHERE is_cut) AS cuts, count(*) FILTER (WHERE NOT is_cut) AS rises
FROM gold.price_change GROUP BY week_key ORDER BY week_key;
```

**C16.** Site slicer (#2) on the site and Listing slicer (#4) on the id named in C17 (the deepest
cut): the line chart (#11) shows its price per m² at [from the notebook] before and
[from the notebook] after, and the dashed line for our units of the same type and area is at
[from the notebook] (missing if we have none). The cards do not change (C14). Clear both slicers:
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

**C17.** Table (#12), sorted by Change % ascending: the top rows are [from the notebook], the
deepest cuts. Its [from the notebook] rows match Price changes in C14.

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

**C18.** Area slicer (#3) on **New Cairo**: Price changes [from the notebook] · Cuts
[from the notebook] · Rises [from the notebook] · Listings seen this week [from the notebook]. Clear
the slicer.

```sql
SELECT count(*) AS price_changes, count(*) FILTER (WHERE c.is_cut) AS cuts,
       count(*) FILTER (WHERE NOT c.is_cut) AS rises,
       (SELECT count(*) FROM gold.fact_listing_price f JOIN gold.dim_area fa USING (area_key)
        WHERE fa.area_id = 'new-cairo'
          AND f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price)) AS listings
FROM gold.price_change c JOIN gold.dim_area a USING (area_key)
WHERE a.area_id = 'new-cairo';
```
