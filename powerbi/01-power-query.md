# 1. Power Query

The report reads the local warehouse: PostgreSQL on `localhost:5451`, database `prices`, after
`docker compose up -d --build` and at least one run of the `egypt_real_estate_prices` DAG (steps 1
to 4 of [`08-build-checklist.md`](08-build-checklist.md)). Nothing is read from files.

Open Power BI Desktop, then **Home > Transform data** to open the Power Query editor. For each query
below: **Home > New source > Blank query**, rename it (right-click > Rename) to the name in the
heading, open **Home > Advanced editor**, delete what is there and paste the code.

| Query | Source | Columns | Renames | Load |
|---|---|---|---|---|
| `WarehouseServer` | parameter (text) | none | none | no (parameter) |
| `Area` | the `area` table | 3 (2 + `Map Name`) | none | yes |
| `Our Unit` | the `our_unit` table | 8 | none | yes |
| `Listing` | the `listing` table | 10 | none | yes |
| `Price Observation` | the `price_observation` table | 5 | none | yes |
| `Area Benchmark` | the `area_benchmark` view | 6 | none | yes |
| `Compound Benchmark` | the `compound_benchmark` view | 5 | none | yes |
| `Unit Gap` | the `unit_gap` view | 12 (11 + `Position`) | none | yes |
| `Price Change` | the `price_change` view | 8 (7 + `Direction`) | none | yes |
| `Date` | generated from `Price Observation[observed_on]` | 5 | none | yes |

Why no renames: the column names match [`sql/schema.sql`](../sql/schema.sql) and the SQL in
`06-checks.md`, so a number on a card can be checked against the warehouse word for word. Visuals
show friendly names, set on the visual (`04-pages.md`).

Why the views for the benchmarks, the gaps and the changes: the median per m², our units' gap and
each price change are written once in SQL and read the same way by the weekly report, the notebook
and this report. `area_benchmark`, `compound_benchmark` and `unit_gap` count only the listings seen
in the latest weekly run (`run_week = (SELECT max(run_week) FROM price_observation)`), so a unit
that left the site weeks ago does not hold the median up or down.

Why every column gets a type: Power BI then never guesses, so a refresh after a new weekly run
cannot turn a price into text.

## The first connection

The first query you create asks for credentials: choose **Database**, user `prices`, password =
`WAREHOUSE_PASSWORD` from the repo's `.env`, and apply them to `localhost:5451`. If Power BI says it
cannot connect with encryption, choose **OK** to connect without it: the warehouse listens on your
laptop only.

## WarehouseServer (parameter)

**Home > Manage parameters > New parameter**

- Name: `WarehouseServer`
- Type: Text
- Current value: `localhost:5451`

Why a parameter: if the port ever changes, it changes in one place.

## Area (loads)

The six areas we read: one row per area.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    area = Source{[Schema = "public", Item = "area"]}[Data],
    Kept = Table.SelectColumns(area, {"area_id", "name"}),
    Typed = Table.TransformColumnTypes(Kept, {{"area_id", type text}, {"name", type text}}),
    MapName = Table.AddColumn(Typed, "Map Name", each [name] & ", Egypt", type text)
in
    MapName
```

`Map Name` is the place name the map visual geocodes ("New Cairo, Egypt"): the area name alone
could match a place in another country. `location_id` is dropped: it is the site's id, used only by
the tracker to build the page address.

## Our Unit (loads)

The client's own units for sale: one row per unit.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    our_unit = Source{[Schema = "public", Item = "our_unit"]}[Data],
    Typed = Table.TransformColumnTypes(our_unit, {
        {"unit_code", type text}, {"area_id", type text}, {"compound", type text},
        {"unit_type", type text}, {"bedrooms", Int64.Type}, {"size_m2", type number},
        {"asking_price", Currency.Type}, {"price_per_m2", Currency.Type}})
in
    Typed
```

## Listing (loads)

Every competitor unit seen on the site: one row per listing, with its latest description.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    listing = Source{[Schema = "public", Item = "listing"]}[Data],
    Kept = Table.SelectColumns(listing, {
        "listing_id", "area_id", "compound", "developer", "unit_type", "bedrooms", "bathrooms",
        "size_m2", "first_seen", "last_seen"}),
    Typed = Table.TransformColumnTypes(Kept, {
        {"listing_id", Int64.Type}, {"area_id", type text}, {"compound", type text},
        {"developer", type text}, {"unit_type", type text}, {"bedrooms", Int64.Type},
        {"bathrooms", Int64.Type}, {"size_m2", type number}, {"first_seen", type date},
        {"last_seen", type date}})
in
    Typed
```

`url` is dropped: the report never links out, and the listing id already names the unit.

## Price Observation (loads)

Every asking price seen: one row per listing per day it was read.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    price_observation = Source{[Schema = "public", Item = "price_observation"]}[Data],
    Kept = Table.SelectColumns(price_observation, {
        "listing_id", "observed_on", "asking_price", "price_per_m2", "run_week"}),
    Typed = Table.TransformColumnTypes(Kept, {
        {"listing_id", Int64.Type}, {"observed_on", type date}, {"asking_price", Currency.Type},
        {"price_per_m2", Currency.Type}, {"run_week", type date}})
in
    Typed
```

`fetched_at` is dropped: `observed_on` and `run_week` already date each price.

## Area Benchmark (loads)

The market in the latest run: one row per area and unit type.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    area_benchmark = Source{[Schema = "public", Item = "area_benchmark"]}[Data],
    Typed = Table.TransformColumnTypes(area_benchmark, {
        {"area_id", type text}, {"unit_type", type text}, {"listings", Int64.Type},
        {"median_price_per_m2", type number}, {"min_price_per_m2", Currency.Type},
        {"max_price_per_m2", Currency.Type}})
in
    Typed
```

## Compound Benchmark (loads)

The market in the latest run: one row per area, compound and developer.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    compound_benchmark = Source{[Schema = "public", Item = "compound_benchmark"]}[Data],
    Typed = Table.TransformColumnTypes(compound_benchmark, {
        {"area_id", type text}, {"compound", type text}, {"developer", type text},
        {"listings", Int64.Type}, {"median_price_per_m2", type number}})
in
    Typed
```

## Unit Gap (loads)

Each of our units against the latest run's median of the same type in its area: one row per unit.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    unit_gap = Source{[Schema = "public", Item = "unit_gap"]}[Data],
    Typed = Table.TransformColumnTypes(unit_gap, {
        {"unit_code", type text}, {"area_id", type text}, {"compound", type text},
        {"unit_type", type text}, {"size_m2", type number}, {"asking_price", Currency.Type},
        {"price_per_m2", Currency.Type}, {"median_price_per_m2", type number},
        {"gap_pct", type number}, {"listings_compared", Int64.Type},
        {"pct_listings_cheaper", type number}}),
    Position = Table.AddColumn(Typed, "Position", each
        if [gap_pct] = null then "No comparison" else if [gap_pct] > 0 then "Above market" else "Below market", type text)
in
    Position
```

`Position` is the readable label for each unit: "No comparison" when no listing of the same type was
seen in its area in the latest run (`gap_pct` is null), "Above market" when our price per m² is over
the median, otherwise "Below market". A gap of exactly 0.0 counts as below: the
`Units Above Market` measure uses the same `gap_pct > 0` test.

## Price Change (loads)

Every asking price change: one row per listing per day its price differed from the price before.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    price_change = Source{[Schema = "public", Item = "price_change"]}[Data],
    Kept = Table.SelectColumns(price_change, {
        "listing_id", "observed_on", "old_price", "new_price", "change_pct", "caught_week", "is_cut"}),
    Typed = Table.TransformColumnTypes(Kept, {
        {"listing_id", Int64.Type}, {"observed_on", type date}, {"old_price", Currency.Type},
        {"new_price", Currency.Type}, {"change_pct", type number}, {"caught_week", type date},
        {"is_cut", type logical}}),
    Direction = Table.AddColumn(Typed, "Direction", each if [is_cut] then "Cut" else "Rise", type text)
in
    Direction
```

`Direction` says whether the change lowered or raised the price, for the Cuts and Rises measures.
The view's `area_id`, `compound`, `developer` and `unit_type` are dropped: `Listing` carries them,
so every slicer reaches the changes through one table. Until the second weekly run this query
returns no rows: one run has no previous price to compare with.

## Date (loads)

One row per day from the first to the last asking price, with no gaps.

```m
let
    FirstDay = List.Min(#"Price Observation"[observed_on]),
    LastDay = List.Max(#"Price Observation"[observed_on]),
    Days = List.Dates(FirstDay, Duration.Days(LastDay - FirstDay) + 1, #duration(1, 0, 0, 0)),
    AsTable = Table.FromList(Days, Splitter.SplitByNothing(), {"Date"}),
    Typed = Table.TransformColumnTypes(AsTable, {{"Date", type date}}),
    Year = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),
    Month = Table.AddColumn(Year, "Month", each Date.ToText([Date], "MMM yyyy", "en-US"), type text),
    MonthNumber = Table.AddColumn(Month, "Month Number", each Date.Year([Date]) * 100 + Date.Month([Date]), Int64.Type),
    WeekStart = Table.AddColumn(MonthNumber, "Week Start", each Date.StartOfWeek([Date], Day.Sunday), type date)
in
    WeekStart
```

Why the weeks start on Sunday: the tracker dates each run by the Sunday its week starts
(`run_week`), so a week here is the same week as a run.

Why from `Price Observation` only: every price change is also an observation, so the days of
`Price Change[observed_on]` are always inside this range.

**Home > Close & apply.** Then go to [`02-model.md`](02-model.md).

Every amount is in Egyptian pounds (EGP). The report compares units by price per m², never by
summing asking prices: a sum of flat prices across areas and types would mean nothing.
