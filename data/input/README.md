# Input files

What the client supplies, as CSV with a header row, UTF-8. The file name is set in
`config/client.yaml` under `inputs`. Extra columns are ignored. `python tracker.py` (and the
`load_silver` task of every Airflow run) checks the file before the warehouse is touched and stops
with one line if:

- the file is missing (the line names `inputs.units`), or has no units;
- a column below is missing (the line names the columns);
- a unit's `area_id` is not an `id` under `areas` in `config/client.yaml`;
- a unit's `unit_type` is not in `rules.unit_types`;
- `size_m2` or `asking_price` is not a number above 0.

## units (`inputs.units`)

The client's units for sale: one row per unit. Each is compared with the competing listings of the
same type in the same area, by asking price per m².

| Column | Type | Example |
|---|---|---|
| unit_code | text, unique | NC-APT-01 |
| area_id | text: an area `id` in config/client.yaml | new-cairo |
| compound | text: the compound name as a listing site writes it (it groups the unit with that compound's listings) | Eastown |
| developer | text, empty if none | Sodic |
| unit_type | text: one of `rules.unit_types` | Apartment |
| bedrooms | whole number | 3 |
| size_m2 | number above 0, in m² | 150 |
| asking_price | number above 0, in `client.currency` | 9580000 |

One row as it appears in the file:

```csv
unit_code,area_id,compound,developer,unit_type,bedrooms,size_m2,asking_price
NC-APT-01,new-cairo,Eastown,,Apartment,3,150,9580000
```

The demo's 60 units in `our_units.csv` are made up by `make_units.py` (demo tooling: real compounds
seen on the sites, prices near the market median of their type and area). A client's file replaces it.

## Areas and sites (not files: `areas` and `sites` in config/client.yaml)

Each area is one entry with its `id`, `name`, map coordinates and, per site, the search pages to
read and how the site names the area in a listing. "Tell me the area and I'll add it" is this edit:
`docs/new-client.md` says how to find each site's address for a new area.
