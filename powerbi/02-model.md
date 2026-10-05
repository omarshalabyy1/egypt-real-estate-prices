# 2. The model

Open **Model view** (the third icon on the left).

## Tables

Row counts grow with every weekly run: the numbers to expect are in `06-checks.md` (check C2).

| Table | Role | Grain (one row per) | Key | Rows |
|---|---|---|---|---|
| `Site` | dimension | listing site | `site_key` (natural key `source`) | see 06-checks.md |
| `Area` | dimension | area we read | `area_key` (natural key `area_id`) | see 06-checks.md |
| `Compound` | dimension | area, compound and developer as the sites write them | `compound_key` (natural key `area_id` + `compound` + `developer`) | see 06-checks.md |
| `Property Type` | dimension | residential unit type | `type_key` (natural key `unit_type`) | see 06-checks.md |
| `Week` | dimension, date table | run week (the Sunday it starts) | `week_key` | see 06-checks.md |
| `Listing Price` | fact | site, listing and run week | `site_key` + `listing_id` + `week_key` | see 06-checks.md |
| `Our Unit` | fact | unit of ours for sale | `unit_code` | see 06-checks.md |
| `Price Change` | view | site and listing whose price per m² changed from its previous run week | `site_key` + `listing_id` + `week_key` | see 06-checks.md |
| `Area Benchmark` | view | area and unit type, latest run week, pooled over sites | `area_key` + `type_key` | see 06-checks.md |
| `Area Site Benchmark` | view | site, area and unit type, latest run week | `site_key` + `area_key` + `type_key` | see 06-checks.md |
| `Unit Gap` | view | unit of ours against the pooled latest-week median | `unit_code` | see 06-checks.md |
| `Area Gap` | view | area, our units' gap pooled over sites | `area_key` | see 06-checks.md |
| `_Measures` | holds the measures only | none | none | 1 (hidden) |

A Kimball star with two facts. `Listing Price` and `Our Unit` share the `Area`, `Compound` and
`Property Type` dimensions, so one Area or Type slicer filters the market and our units the same way.
The five views hang off the same dimensions wherever their grain carries the key. The `_Measures`
table is created in step 3 (`03-measures.dax`). There are no calculated columns and no calculated
tables: every column comes from Power Query.

Why the views load although the pages read the measures: the views are pooled over every site, so
the Site slicer cannot reach them. The measures recompute each number on `Listing Price` and
`Our Unit`, where the Site slicer does reach. With no slicer selected, a measure and its view must
agree; the checks in `06-checks.md` compare them.

`Compound` writes `Unknown` where a site names no compound or developer, so its columns are never
blank; the measures leave `Unknown` out when they count compounds and developers.

## Mark the date table

Select the `Week` table, then **Table tools > Mark as date table**, and pick the `week_key` column.

Why: `week_key` is the one date every fact and view is dated by, so marking it makes `Week` the
model's calendar and stops Power BI dating anything another way. Turn off **File > Options and
settings > Options > Current file > Data load > Auto date/time** so Power BI does not add hidden date
tables of its own.

Power BI checks that a date table holds unique dates with no blanks and no gaps from first to last.
`week_key` is one Sunday per run week: with one run week it passes; from the second run week on,
the Sundays are seven days apart, so re-check that **Mark as date table** still accepts it after the
second weekly run.

## Relationships

Drag each "one" column onto its "many" column, then open the relationship (double-click the line)
and check the settings. Every line is One to many, cross-filter direction Single, Active.

| From (one) | To (many) | Why |
|---|---|---|
| `Site[site_key]` | `Listing Price[site_key]` | The Site slicer filters the market |
| `Area[area_key]` | `Listing Price[area_key]` | The Area slicer and the map filter the market |
| `Compound[compound_key]` | `Listing Price[compound_key]` | Compounds and developers group the market |
| `Property Type[type_key]` | `Listing Price[type_key]` | Unit types group the market |
| `Week[week_key]` | `Listing Price[week_key]` | The run weeks date every price |
| `Area[area_key]` | `Our Unit[area_key]` | The Area slicer filters our units, the same way as the market |
| `Property Type[type_key]` | `Our Unit[type_key]` | ...and by unit type |
| `Compound[compound_key]` | `Our Unit[compound_key]` | ...and by compound. No Site and no Week line: our units are not on a site and have no run week |
| `Site[site_key]` | `Price Change[site_key]` | The view carries every key of the fact, so every dimension filters the changes |
| `Area[area_key]` | `Price Change[area_key]` | ... |
| `Compound[compound_key]` | `Price Change[compound_key]` | ... |
| `Property Type[type_key]` | `Price Change[type_key]` | ... |
| `Week[week_key]` | `Price Change[week_key]` | A change is dated by the run week that caught it; `old_week_key` stays a plain column, with no line |
| `Area[area_key]` | `Area Benchmark[area_key]` | Its grain is area, type and week |
| `Property Type[type_key]` | `Area Benchmark[type_key]` | ... |
| `Week[week_key]` | `Area Benchmark[week_key]` | ... No Site and no Compound line: the view pools them |
| `Site[site_key]` | `Area Site Benchmark[site_key]` | Its grain is site, area, type and week |
| `Area[area_key]` | `Area Site Benchmark[area_key]` | ... |
| `Property Type[type_key]` | `Area Site Benchmark[type_key]` | ... |
| `Week[week_key]` | `Area Site Benchmark[week_key]` | ... No Compound line: the view pools compounds |
| `Area[area_key]` | `Unit Gap[area_key]` | Its grain is our unit, which carries area, type and compound |
| `Property Type[type_key]` | `Unit Gap[type_key]` | ... |
| `Compound[compound_key]` | `Unit Gap[compound_key]` | ... No Site and no Week line: the view pools sites and has no week column |
| `Area[area_key]` | `Area Gap[area_key]` | Its grain is the area. Power BI proposes One to one here (both columns are unique): set Cardinality to **One to many** and direction **Single**, so the filter flows from `Area` only |

24 relationships. Power BI may create some of these on its own when you close Power Query. Delete
any other relationship it made, above all:

- `Compound[area_id]` to `Area[area_id]`: a second path from `Area` to the facts (through `Compound`
  as well as directly) makes the model ambiguous. `Compound[area_id]` stays a plain column.
- `Our Unit[unit_code]` to `Unit Gap[unit_code]`: Power BI proposes it One to one, both directions.
  `Area` already filters both tables, so that line is a second path from `Area` to `Unit Gap`.
- Any line between two facts or two views: they meet only through the dimensions.

Why single direction everywhere: filters flow from the dimensions to the facts and views, never
back, so every number has one meaning and no fact can filter another.

## Hide columns

Hide the columns a report builder should not pick, so slicers and axes always use the dimension
(right-click > Hide in report view):

- Every surrogate key: `site_key`, `area_key`, `compound_key` and `type_key` in every table, the
  dimensions included. They are join keys, not labels.
- `week_key` in `Listing Price`, `Price Change`, `Area Benchmark` and `Area Site Benchmark`: use
  `Week[week_key]`.
- `Area[area_id]`, `Compound[area_id]` and `Area[map_name]`: use `Area[name]`; the map reads
  `lat` and `lon`.
- `Price Change[is_cut]`: use `Price Change[Direction]`.
- The empty column of `_Measures` (after step 3).

`Listing Price[listing_id]` and `Price Change[listing_id]` stay visible: page 3 picks a listing by
its id and lists each change by its id. `Price Change[old_week_key]` stays visible: the changes
table shows it as the week of the old price.

## Data category

Set in **Column tools > Data category** with the column selected, and set **Summarization: Don't
summarize** on both:

- `Area[lat]`: **Latitude**.
- `Area[lon]`: **Longitude**.

Why: the map visual then places each area on its coordinates, with no geocoding, and never sums two
latitudes.

## Column formats

Set in **Column tools > Format** with the column selected.

| Column | Format | Why |
|---|---|---|
| `Listing Price[asking_price]`, `Our Unit[asking_price]` | Whole number, thousands separator on, no currency symbol | Egyptian asking prices run to millions of EGP; the piastres add nothing to a reader |
| `Listing Price[price_per_m2]`, `Our Unit[price_per_m2]`, `Price Change[old_price_per_m2]`, `Price Change[new_price_per_m2]`, `Unit Gap[price_per_m2]`, `Unit Gap[median_price_per_m2]`, and `median_price_per_m2`, `p25_price_per_m2`, `p75_price_per_m2` in `Area Benchmark` and `Area Site Benchmark` | Whole number, thousands separator on | Price per m² in EGP, read as a whole number |
| `Price Change[change_pct]`, `Unit Gap[gap_pct]`, `Unit Gap[pct_listings_cheaper]`, `Area Gap[median_gap_pct]`, `Area Gap[pct_listings_cheaper]` | Decimal number, 2 decimals | Already in percent: -5.00 means 5% lower, as the warehouse rounds it |
| `Listing Price[size_m2]`, `Our Unit[size_m2]` | Whole number, thousands separator on | Square metres |
| `Week[week_key]`, `Price Change[old_week_key]` | Short date (`yyyy-mm-dd`) | Same as the warehouse and the checks |
| `Week[year]`, `Week[month]`, `Week[week_of_year]` | Whole number, thousands separator off | Calendar numbers, not counts |

## Display folders

Set on each measure in step 3 (**Properties pane > Display folder**):

| Folder | Measures |
|---|---|
| Market position | Listings, Median Price Per m², P25 Price Per m², P75 Price Per m², Our Units, Our Price Per m², Market Median Per m², Units Compared, Share Above Market, Share Below Market, Median Gap, Widest Gap Area, Listings Compared, Listings Cheaper Than Ours, Share Of Listings Cheaper Than Ours |
| Compounds | Compounds Covered, Developers Covered, Cheapest Compound, Dearest Compound |
| Weekly changes | Price Changes, Price Cuts, Price Rises, Average Change, Competitor Price Per m², Our Same-Type Price Per m² |
