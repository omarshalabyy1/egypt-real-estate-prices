# 6. Checks: the numbers the report must show

Every number below is written `[from the notebook]` for now: a later step fills each one from
`analysis/analysis.ipynb`, run on the warehouse after a named weekly run, and the SQL under each
check gives the same value. Until then, run the SQL and compare the report with its result. Check
with no slicer selected unless a check says otherwise. If a card is off, the usual causes are a
missing relationship, a wrong column type in Power Query, or a filter left on a slicer.

**Building on a later date?** The tracker reads the asking prices on the site on the day it runs, so
every weekly run changes the latest week and the numbers move. Run the notebook once, or the SQL
under each check, and compare the report with those, not with the numbers written here.

**The first week:** checks C12 to C16 (page 3) need two weekly runs. After the first run they show
no changes at all, which is correct: one run has no earlier price to compare with.

Run the SQL in any SQL tool on `localhost:5451`, database `prices`, user `prices`, or with
`docker compose exec warehouse psql -U prices -d prices`.

## The warehouse, before Power BI

**C1.** The runs are in: [from the notebook] weekly runs, the latest one the week of
[from the notebook], with [from the notebook] asking prices in it, one per listing (the two counts
are equal, so the views' medians and the report's `Median Price Per m²` read the same rows).

```sql
SELECT count(DISTINCT run_week) AS runs, max(run_week) AS latest_run,
       count(*) FILTER (WHERE run_week = (SELECT max(run_week) FROM price_observation)) AS prices_latest_run,
       count(DISTINCT listing_id) FILTER (WHERE run_week = (SELECT max(run_week) FROM price_observation)) AS listings_latest_run
FROM price_observation;
```

**C2.** Rows per table after **Close & apply** (Table view, bottom left): Area [from the notebook] ·
Our Unit [from the notebook] · Listing [from the notebook] · Date [from the notebook] · Price
Observation [from the notebook] · Area Benchmark [from the notebook] · Compound Benchmark
[from the notebook] · Unit Gap [from the notebook] · Price Change [from the notebook].

```sql
SELECT (SELECT count(*) FROM area) AS area, (SELECT count(*) FROM our_unit) AS our_unit,
       (SELECT count(*) FROM listing) AS listing,
       (SELECT max(observed_on) - min(observed_on) + 1 FROM price_observation) AS date,
       (SELECT count(*) FROM price_observation) AS price_observation,
       (SELECT count(*) FROM area_benchmark) AS area_benchmark,
       (SELECT count(*) FROM compound_benchmark) AS compound_benchmark,
       (SELECT count(*) FROM unit_gap) AS unit_gap, (SELECT count(*) FROM price_change) AS price_change;
```

## Page 1: Market position

**C3.** Cards, no slicer: Our units [from the notebook] · Above market [from the notebook] · Share
above market [from the notebook] · Average gap [from the notebook] · Furthest from market
[from the notebook] · Competitor listings this week [from the notebook].

```sql
SELECT count(*) AS our_units, count(*) FILTER (WHERE gap_pct > 0) AS above_market,
       round(count(*) FILTER (WHERE gap_pct > 0) * 100.0 / nullif(count(gap_pct), 0), 1) AS share_above_pct,
       round(avg(gap_pct), 1) AS average_gap_pct
FROM unit_gap;

SELECT a.name AS furthest_from_market, round(avg(g.gap_pct), 1) AS average_gap_pct
FROM unit_gap g JOIN area a USING (area_id)
GROUP BY a.name HAVING avg(g.gap_pct) IS NOT NULL
ORDER BY abs(avg(g.gap_pct)) DESC, a.name DESC LIMIT 1;

SELECT sum(listings) AS listings_compared FROM area_benchmark;
```

**C4.** Bar chart (#10) data labels, top to bottom: [from the notebook] (six areas, or fewer if an
area has no unit with a comparison).

```sql
SELECT a.name, count(*) AS our_units, round(avg(g.gap_pct), 1) AS average_gap_pct
FROM unit_gap g JOIN area a USING (area_id)
GROUP BY a.name ORDER BY avg(g.gap_pct) DESC NULLS LAST;
```

**C5.** Map (#9): [from the notebook] bubbles, one on each area, the biggest on [from the notebook].
Hover each bubble: its Listings Compared is the `listings` below. If a bubble is missing or lands
outside Egypt, Azure Maps could not place that `Map Name`: note the area and say so before going on.

```sql
SELECT a.name, a.name || ', Egypt' AS map_name, sum(b.listings) AS listings
FROM area a LEFT JOIN area_benchmark b USING (area_id)
GROUP BY a.name ORDER BY listings DESC NULLS LAST;
```

**C6.** Units table (#11), sorted by Gap % descending: the top rows are [from the notebook]. Its
[from the notebook] rows match Our units in C3, and [from the notebook] of them say "No comparison".

```sql
SELECT unit_code, area_id, unit_type, price_per_m2, median_price_per_m2, gap_pct, listings_compared
FROM unit_gap ORDER BY gap_pct DESC NULLS LAST LIMIT 5;

SELECT count(*) FILTER (WHERE gap_pct IS NULL) AS no_comparison FROM unit_gap;
```

**C7.** Area slicer (#2) on **New Cairo**: Our units [from the notebook] · Above market
[from the notebook] · Share above market [from the notebook] · Average gap [from the notebook] ·
Competitor listings this week [from the notebook]. Clear the slicer.

```sql
SELECT count(*) AS our_units, count(*) FILTER (WHERE gap_pct > 0) AS above_market,
       round(count(*) FILTER (WHERE gap_pct > 0) * 100.0 / nullif(count(gap_pct), 0), 1) AS share_above_pct,
       round(avg(gap_pct), 1) AS average_gap_pct,
       (SELECT sum(listings) FROM area_benchmark WHERE area_id = 'new-cairo') AS listings_compared
FROM unit_gap WHERE area_id = 'new-cairo';
```

## Page 2: Compounds and developers

**C8.** Cards, no slicer: Listings this week [from the notebook] (equal to Competitor listings this
week in C3) · Compounds [from the notebook] · Developers [from the notebook] · Cheapest compound per
m² [from the notebook] · Dearest compound per m² [from the notebook].

```sql
WITH latest AS (
    SELECT l.compound, o.listing_id, o.price_per_m2
    FROM price_observation o JOIN listing l USING (listing_id)
    WHERE o.run_week = (SELECT max(run_week) FROM price_observation)
), by_compound AS (
    SELECT compound, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS median_per_m2
    FROM latest WHERE compound IS NOT NULL GROUP BY compound
)
SELECT (SELECT count(DISTINCT listing_id) FROM latest) AS listings,
       (SELECT count(DISTINCT compound) FROM compound_benchmark) AS compounds,
       (SELECT count(DISTINCT developer) FROM compound_benchmark) AS developers,
       (SELECT compound FROM by_compound ORDER BY median_per_m2, compound DESC LIMIT 1) AS cheapest_compound,
       (SELECT compound FROM by_compound ORDER BY median_per_m2 DESC, compound DESC LIMIT 1) AS dearest_compound;
```

**C9.** Matrix (#8), sorted by compound: the first rows are [from the notebook], with their median
per m² by unit type as below.

```sql
SELECT l.compound, l.unit_type, count(*) AS listings,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY o.price_per_m2))::numeric, 0) AS median_per_m2
FROM price_observation o JOIN listing l USING (listing_id)
WHERE o.run_week = (SELECT max(run_week) FROM price_observation)
GROUP BY l.compound, l.unit_type ORDER BY l.compound NULLS LAST, l.unit_type LIMIT 10;
```

**C10.** Developer bar (#9), top to bottom: the dearest three are [from the notebook].

```sql
SELECT l.developer, count(*) AS listings,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY o.price_per_m2))::numeric, 0) AS median_per_m2
FROM price_observation o JOIN listing l USING (listing_id)
WHERE o.run_week = (SELECT max(run_week) FROM price_observation)
GROUP BY l.developer ORDER BY median_per_m2 DESC LIMIT 3;
```

**C11.** Area slicer (#2) on **New Cairo**: Listings this week [from the notebook] · Compounds
[from the notebook] · Developers [from the notebook] · Cheapest compound per m² [from the notebook] ·
Dearest compound per m² [from the notebook]. Clear the slicer.

```sql
WITH latest AS (
    SELECT l.compound, o.listing_id, o.price_per_m2
    FROM price_observation o JOIN listing l USING (listing_id)
    WHERE o.run_week = (SELECT max(run_week) FROM price_observation) AND l.area_id = 'new-cairo'
), by_compound AS (
    SELECT compound, percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS median_per_m2
    FROM latest WHERE compound IS NOT NULL GROUP BY compound
)
SELECT (SELECT count(DISTINCT listing_id) FROM latest) AS listings,
       (SELECT count(DISTINCT compound) FROM compound_benchmark WHERE area_id = 'new-cairo') AS compounds,
       (SELECT count(DISTINCT developer) FROM compound_benchmark WHERE area_id = 'new-cairo') AS developers,
       (SELECT compound FROM by_compound ORDER BY median_per_m2, compound DESC LIMIT 1) AS cheapest_compound,
       (SELECT compound FROM by_compound ORDER BY median_per_m2 DESC, compound DESC LIMIT 1) AS dearest_compound;
```

## Page 3: Weekly changes

From the second weekly run on. After the first run, C12 shows "(Blank)" on the four change cards and
New this week equals Listings seen this week.

**C12.** Cards, no slicer: Price changes [from the notebook] · Cuts [from the notebook] · Rises
[from the notebook] · Average change [from the notebook] · Listings seen this week
[from the notebook] · New this week [from the notebook].

```sql
SELECT count(*) AS price_changes, count(*) FILTER (WHERE is_cut) AS cuts,
       count(*) FILTER (WHERE NOT is_cut) AS rises, round(avg(change_pct), 1) AS average_change_pct,
       (SELECT count(*) FROM listing
        WHERE first_seen >= (SELECT max(run_week) FROM price_observation)) AS new_this_week
FROM price_change;
```

**C13.** Column chart (#10): [from the notebook] weekly runs have a bar; per run, cuts and rises as
below.

```sql
SELECT caught_week, count(*) FILTER (WHERE is_cut) AS cuts, count(*) FILTER (WHERE NOT is_cut) AS rises
FROM price_change GROUP BY caught_week ORDER BY caught_week;
```

**C14.** Area slicer (#2) on **New Cairo**: Price changes [from the notebook] · Cuts
[from the notebook] · Rises [from the notebook] · New this week [from the notebook]. Clear the slicer.

```sql
SELECT count(*) AS price_changes, count(*) FILTER (WHERE c.is_cut) AS cuts,
       count(*) FILTER (WHERE NOT c.is_cut) AS rises,
       (SELECT count(*) FROM listing WHERE area_id = 'new-cairo'
          AND first_seen >= (SELECT max(run_week) FROM price_observation)) AS new_this_week
FROM price_change c JOIN listing l USING (listing_id) WHERE l.area_id = 'new-cairo';
```

**C15.** Listing slicer (#3) on [from the notebook] (the deepest cut in C16): the line chart (#11)
shows its price per m² at [from the notebook] before and [from the notebook] after, and the dashed
line for our units of the same type and area is at [from the notebook] (missing if we have none).
The cards do not change (C12). Clear the slicer: the line chart is empty again.

```sql
-- Replace 0 with the listing id picked.
SELECT o.observed_on, o.price_per_m2,
       (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY u.price_per_m2)
        FROM our_unit u WHERE u.area_id = l.area_id AND u.unit_type = l.unit_type) AS ours_same_type_per_m2
FROM price_observation o JOIN listing l USING (listing_id)
WHERE o.listing_id = 0 ORDER BY o.observed_on;
```

**C16.** Table (#12), sorted by Change % ascending: the top rows are [from the notebook], the deepest
cuts. Its [from the notebook] rows match Price changes in C12.

```sql
SELECT c.listing_id, a.name AS area, l.compound, l.developer, l.unit_type, c.observed_on,
       c.old_price, c.new_price, c.change_pct, c.caught_week
FROM price_change c JOIN listing l USING (listing_id) JOIN area a ON a.area_id = l.area_id
ORDER BY c.change_pct LIMIT 5;
```
