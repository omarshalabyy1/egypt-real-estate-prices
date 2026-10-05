# 2. The model

Open **Model view** (the third icon on the left).

## Tables

Row counts grow with every weekly run: the numbers to expect are in `06-checks.md` (check C2).

| Table | Grain (one row per) | Key | Rows |
|---|---|---|---|
| `Area` | area we read | `area_id` | see 06-checks.md |
| `Our Unit` | unit of ours for sale | `unit_code` | see 06-checks.md |
| `Listing` | competitor unit seen on the site | `listing_id` | see 06-checks.md |
| `Date` | day, first to last asking price | `Date` | see 06-checks.md |
| `Price Observation` | asking price of one listing on one day | `listing_id` + `observed_on` | see 06-checks.md |
| `Area Benchmark` | area and unit type, latest run | `area_id` + `unit_type` | see 06-checks.md |
| `Compound Benchmark` | area, compound and developer, latest run | `area_id` + `compound` + `developer` | see 06-checks.md |
| `Unit Gap` | unit of ours against its market | `unit_code` | see 06-checks.md |
| `Price Change` | price change of one listing | `listing_id` + `observed_on` | see 06-checks.md |
| `_Measures` | holds the measures only | none | 1 (hidden) |

A small star with one snowflake arm: the price history (`Price Observation`) and the changes
(`Price Change`) hang off `Listing`, which hangs off `Area`; the benchmarks and our units hang off
`Area` directly. The `_Measures` table is created in step 3 (`03-measures.dax`). There are no
calculated columns and no calculated tables: every column comes from Power Query.

`Compound Benchmark` keeps a null `compound` or `developer` as its own row (the site does not always
show them), so its key columns can be blank; the measures leave blanks out when they count.

## Mark the date table

Select the `Date` table, then **Table tools > Mark as date table**, and pick the `Date` column.

Why: the `Date` table has one row per day with no gaps, so days, weeks and months group correctly.
Turn off **File > Options and settings > Options > Current file > Data load > Auto date/time** so
Power BI does not add hidden date tables of its own.

## Relationships

Drag each "one" column onto its "many" column, then open the relationship (double-click the line)
and check the settings.

| From (one) | To (many) | Cardinality | Cross-filter direction | Active | Why |
|---|---|---|---|---|---|
| `Area[area_id]` | `Listing[area_id]` | One to many | Single | Yes | The Area slicer filters the listings, and through them the prices and the changes |
| `Area[area_id]` | `Our Unit[area_id]` | One to many | Single | Yes | ...our units |
| `Area[area_id]` | `Area Benchmark[area_id]` | One to many | Single | Yes | ...the area medians |
| `Area[area_id]` | `Compound Benchmark[area_id]` | One to many | Single | Yes | ...the compound medians |
| `Area[area_id]` | `Unit Gap[area_id]` | One to many | Single | Yes | ...and our units' gaps |
| `Listing[listing_id]` | `Price Observation[listing_id]` | One to many | Single | Yes | A listing's description (compound, developer, type) filters its prices |
| `Listing[listing_id]` | `Price Change[listing_id]` | One to many | Single | Yes | ...and its changes |
| `Date[Date]` | `Price Observation[observed_on]` | One to many | Single | Yes | The price history runs on the Date table |
| `Date[Date]` | `Price Change[observed_on]` | One to many | Single | Yes | A change is dated by the day the new price was read |

Power BI may create some of these on its own when you close Power Query. Delete any other
relationship it made. In particular it will find `Our Unit[unit_code]` and `Unit Gap[unit_code]`
unique on both sides and join them one to one, in both directions: delete it. With `Area` already
filtering both tables, that line is a second path from `Area` to `Unit Gap`, which makes the model
ambiguous, and `Unit Gap` already carries every column of `Our Unit` the report needs. Do not join
`Price Observation` to `Price Change` either: both are facts, and `Listing` and `Date` already
connect them.

Why single direction everywhere: filters flow from the small tables (Area, Listing, Date) to the
facts, never back, so every number has one meaning. `Area` reaches `Price Observation` and
`Price Change` through `Listing`: a single-direction chain carries the filter all the way down.

Why the benchmarks and `Unit Gap` have no Date relationship: they hold the latest run only, so they
answer "where does the market stand now"; filtering them by a past date would mean nothing.

## Hide columns

Hide the columns a report builder should not pick, so slicers and axes always use the dimension
(right-click > Hide in report view):

- `area_id` in `Listing`, `Our Unit`, `Area Benchmark`, `Compound Benchmark` and `Unit Gap`, and
  `Area[area_id]` itself: use `Area[name]`.
- `listing_id` in `Price Observation` and `Price Change`: use `Listing[listing_id]`.
- `Price Observation[observed_on]`: use the `Date` columns.
- `Price Observation[run_week]`: used inside the measures only.
- `Price Change[is_cut]`: use `Price Change[Direction]`.
- `Date[Month Number]`: used only for sorting.
- The empty column of `_Measures` (after step 3).

`Price Change[observed_on]` and `Price Change[caught_week]` stay visible: the changes page shows
them as the date of each change and the run that caught it.

## Sort by column

Select `Date[Month]`, then **Column tools > Sort by column > Month Number**, so months run in
calendar order, not alphabetically.

## Data category

Select `Area[Map Name]`, then **Column tools > Data category > Place**, so the map visual reads it as
a place name to geocode.

## Column formats

Set in **Column tools > Format** with the column selected.

| Column | Format | Why |
|---|---|---|
| `Our Unit[asking_price]`, `Price Observation[asking_price]`, `Unit Gap[asking_price]`, `Price Change[old_price]`, `Price Change[new_price]` | Whole number, thousands separator on, no currency symbol | Egyptian asking prices run to millions of EGP; the piastres add nothing to a reader |
| `Our Unit[price_per_m2]`, `Price Observation[price_per_m2]`, `Unit Gap[price_per_m2]`, `Unit Gap[median_price_per_m2]`, `Area Benchmark[median_price_per_m2]`, `Area Benchmark[min_price_per_m2]`, `Area Benchmark[max_price_per_m2]`, `Compound Benchmark[median_price_per_m2]` | Whole number, thousands separator on | Price per m² in EGP, read as a whole number |
| `Unit Gap[gap_pct]`, `Unit Gap[pct_listings_cheaper]`, `Price Change[change_pct]` | Decimal number, 1 decimal | Already in percent: -5.0 means 5% lower |
| `Our Unit[size_m2]`, `Listing[size_m2]`, `Unit Gap[size_m2]` | Whole number, thousands separator on | Square metres |
| `Date[Date]`, `Date[Week Start]`, `Listing[first_seen]`, `Listing[last_seen]`, `Price Change[observed_on]`, `Price Change[caught_week]` | Short date (`yyyy-mm-dd`) | Same as the warehouse and the checks |
| `Date[Year]`, `Listing[listing_id]` | Whole number, thousands separator off | A year and an id, not counts |

## Display folders

Set on each measure in step 3 (**Properties pane > Display folder**):

| Folder | Measures |
|---|---|
| Market position | Listings Compared, Compounds Covered, Developers Covered, Our Units, Units Above Market, Share Above Market, Average Gap, Widest Gap Area, Median Price Per m², Our Price Per m² |
| Compounds | Listings, Cheapest Compound, Dearest Compound |
| Weekly changes | Price Changes, Price Cuts, Price Rises, Average Change, New Listings This Week, Competitor Price Per m², Our Same-Type Price Per m² |
