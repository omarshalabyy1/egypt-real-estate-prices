# 1. Power Query

The report reads the gold layer of the local warehouse, and nothing else: PostgreSQL on
`127.0.0.1:5451`, database `prices`, schema `gold`, after `docker compose up -d --build` and at least
one run of the `egypt_real_estate_prices` DAG (steps 1 to 4 of
[`08-build-checklist.md`](08-build-checklist.md)). Nothing is read from bronze, silver or files.

Open Power BI Desktop, then **Home > Transform data** to open the Power Query editor. For each query
below: **Home > New source > Blank query**, rename it (right-click > Rename) to the name in the
heading, open **Home > Advanced editor**, delete what is there and paste the code.

| Query | Source | Columns | Renames | Load |
|---|---|---|---|---|
| `WarehouseServer` | parameter (text) | none | none | no (parameter) |
| `Site` | the `gold.dim_site` table | 3 | none | yes |
| `Area` | the `gold.dim_area` table | 6 | none | yes |
| `Compound` | the `gold.dim_compound` table | 4 | none | yes |
| `Property Type` | the `gold.dim_property_type` table | 2 | none | yes |
| `Week` | the `gold.dim_week` table | 4 | none | yes |
| `Listing Price` | the `gold.pooled_listing_price` view | 10 | none | yes |
| `Our Unit` | the `gold.fact_our_unit` table | 7 | none | yes |
| `Price Change` | the `gold.price_change` view | 12 (11 + `Direction`) | none | yes |
| `Area Benchmark` | the `gold.area_benchmark` view | 7 | none | yes |
| `Area Site Benchmark` | the `gold.area_site_benchmark` view | 8 | none | yes |
| `Unit Gap` | the `gold.unit_gap` view | 10 | none | yes |
| `Area Gap` | the `gold.area_gap` view | 6 | none | yes |

Why gold only: the star is built for reading. Its dimensions carry surrogate keys that stay stable
from week to week, its facts carry those keys, and every name a slicer shows is already clean
(`Unknown` where a site names no compound or developer). The report needs no joins of its own.

Why no renames: the column names match [`sql/schema.sql`](../sql/schema.sql) and the SQL in
`06-checks.md`, so a number on a card can be checked against the warehouse word for word. Visuals
show friendly names, set on the visual (`04-pages.md`).

Why the five views load too: they are the warehouse's own answers, pooled over every site. The
measures in `03-measures.dax` recompute the same numbers on the star so the Site slicer can reach
them; with no slicer selected the two must agree, and the view tables are where you look to check.

Why every column gets a type: Power BI then never guesses, so a refresh after a new weekly run
cannot turn a price into text. Surrogate keys are whole numbers, `week_key` is a date, prices per m²
are numbers.

## The first connection

The first query you create asks for credentials: choose **Database**, user `prices`, password =
`WAREHOUSE_PASSWORD` from the repo's `.env`, and apply them to `127.0.0.1:5451`. If Power BI says it
cannot connect with encryption, choose **OK** to connect without it: the warehouse listens on your
laptop only.

## WarehouseServer (parameter)

**Home > Manage parameters > New parameter**

- Name: `WarehouseServer`
- Type: Text
- Current value: `127.0.0.1:5451`

Why a parameter: if the port ever changes, it changes in one place.

## Site (loads)

The listing sites: one row per site.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    dim_site = Source{[Schema = "gold", Item = "dim_site"]}[Data],
    Kept = Table.SelectColumns(dim_site, {"site_key", "source", "name"}),
    Typed = Table.TransformColumnTypes(Kept, {
        {"site_key", Int64.Type}, {"source", type text}, {"name", type text}})
in
    Typed
```

`base_url` and `read_by` are dropped: the report never links out, and who read a site does not
change a price.

## Area (loads)

The six areas we read: one row per area, with its coordinates for the map.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    dim_area = Source{[Schema = "gold", Item = "dim_area"]}[Data],
    Typed = Table.TransformColumnTypes(dim_area, {
        {"area_key", Int64.Type}, {"area_id", type text}, {"name", type text},
        {"map_name", type text}, {"lat", type number}, {"lon", type number}})
in
    Typed
```

`lat` and `lon` place each area on the map directly, so nothing is geocoded.

## Compound (loads)

One row per area, compound and developer as the sites write them; `Unknown` where a site names none.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    dim_compound = Source{[Schema = "gold", Item = "dim_compound"]}[Data],
    Typed = Table.TransformColumnTypes(dim_compound, {
        {"compound_key", Int64.Type}, {"area_id", type text}, {"compound", type text},
        {"developer", type text}})
in
    Typed
```

## Property Type (loads)

One row per residential unit type.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    dim_property_type = Source{[Schema = "gold", Item = "dim_property_type"]}[Data],
    Typed = Table.TransformColumnTypes(dim_property_type, {
        {"type_key", Int64.Type}, {"unit_type", type text}})
in
    Typed
```

## Week (loads)

One row per run week, keyed by the Sunday the week starts.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    dim_week = Source{[Schema = "gold", Item = "dim_week"]}[Data],
    Typed = Table.TransformColumnTypes(dim_week, {
        {"week_key", type date}, {"year", Int64.Type}, {"month", Int64.Type},
        {"week_of_year", Int64.Type}})
in
    Typed
```

Why weeks and not days: the warehouse prices each listing once per run week, so a day table would
hold six empty days for every day with data.

## Listing Price (loads)

The fact: one row per site, listing and run week, with the asking price, size and price per m².
It reads `gold.pooled_listing_price`, the fact's columns without the Bayut Egypt rows that copy a
Dubizzle ad, so the report counts the same listings as the README.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    pooled_listing_price = Source{[Schema = "gold", Item = "pooled_listing_price"]}[Data],
    Typed = Table.TransformColumnTypes(pooled_listing_price, {
        {"site_key", Int64.Type}, {"area_key", Int64.Type}, {"compound_key", Int64.Type},
        {"type_key", Int64.Type}, {"week_key", type date}, {"listing_id", type text},
        {"asking_price", Currency.Type}, {"size_m2", type number},
        {"price_per_m2", Currency.Type}, {"bedrooms", Int64.Type}})
in
    Typed
```

`listing_id` is text: it is the site's own id, and the same id can belong to different listings on
two sites, so a listing is named by its site and its id together.

## Our Unit (loads)

The client's own units for sale: one row per unit.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    fact_our_unit = Source{[Schema = "gold", Item = "fact_our_unit"]}[Data],
    Typed = Table.TransformColumnTypes(fact_our_unit, {
        {"unit_code", type text}, {"area_key", Int64.Type}, {"type_key", Int64.Type},
        {"compound_key", Int64.Type}, {"size_m2", type number},
        {"asking_price", Currency.Type}, {"price_per_m2", Currency.Type}})
in
    Typed
```

## Price Change (loads)

Every change of price per m²: one row per site and listing whose price per m² differs from its
previous run week.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    price_change = Source{[Schema = "gold", Item = "price_change"]}[Data],
    Typed = Table.TransformColumnTypes(price_change, {
        {"site_key", Int64.Type}, {"listing_id", type text}, {"area_key", Int64.Type},
        {"compound_key", Int64.Type}, {"type_key", Int64.Type}, {"old_week_key", type date},
        {"week_key", type date}, {"old_price_per_m2", Currency.Type},
        {"new_price_per_m2", Currency.Type}, {"change_pct", type number},
        {"is_cut", type logical}}),
    Direction = Table.AddColumn(Typed, "Direction", each if [is_cut] then "Cut" else "Rise", type text)
in
    Direction
```

`Direction` says whether the change lowered or raised the price, for the Cuts and Rises measures.
Until the second weekly run this query returns no rows: one run has no previous price to compare
with.

## Area Benchmark (loads)

The market in the latest run week, pooled over sites: one row per area and unit type.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    area_benchmark = Source{[Schema = "gold", Item = "area_benchmark"]}[Data],
    Typed = Table.TransformColumnTypes(area_benchmark, {
        {"area_key", Int64.Type}, {"type_key", Int64.Type}, {"week_key", type date},
        {"listings", Int64.Type}, {"median_price_per_m2", type number},
        {"p25_price_per_m2", type number}, {"p75_price_per_m2", type number}})
in
    Typed
```

## Area Site Benchmark (loads)

The market in the latest run week, site by site: one row per site, area and unit type.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    area_site_benchmark = Source{[Schema = "gold", Item = "area_site_benchmark"]}[Data],
    Typed = Table.TransformColumnTypes(area_site_benchmark, {
        {"site_key", Int64.Type}, {"area_key", Int64.Type}, {"type_key", Int64.Type},
        {"week_key", type date}, {"listings", Int64.Type}, {"median_price_per_m2", type number},
        {"p25_price_per_m2", type number}, {"p75_price_per_m2", type number}})
in
    Typed
```

## Unit Gap (loads)

Each of our units against the latest week's pooled median of its area and type: one row per unit.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    unit_gap = Source{[Schema = "gold", Item = "unit_gap"]}[Data],
    Typed = Table.TransformColumnTypes(unit_gap, {
        {"unit_code", type text}, {"area_key", Int64.Type}, {"type_key", Int64.Type},
        {"compound_key", Int64.Type}, {"price_per_m2", type number},
        {"median_price_per_m2", type number}, {"gap_pct", type number},
        {"listings_compared", Int64.Type}, {"listings_cheaper", Int64.Type},
        {"pct_listings_cheaper", type number}})
in
    Typed
```

## Area Gap (loads)

Our units' gap, area by area, pooled over sites: one row per area; `gap_rank` 1 is the widest gap.

```m
let
    Source = PostgreSQL.Database(WarehouseServer, "prices"),
    area_gap = Source{[Schema = "gold", Item = "area_gap"]}[Data],
    Typed = Table.TransformColumnTypes(area_gap, {
        {"area_key", Int64.Type}, {"units", Int64.Type}, {"units_compared", Int64.Type},
        {"median_gap_pct", type number}, {"pct_listings_cheaper", type number},
        {"gap_rank", Int64.Type}})
in
    Typed
```

**Home > Close & apply.** Then go to [`02-model.md`](02-model.md).

Every amount is in the client's currency (`client.currency` in `config/client.yaml`; the demo: Egyptian
pounds, EGP). The report compares units by price per m², never by
summing asking prices: a sum of flat prices across areas and types would mean nothing.
