# New client

This repo is a GitHub template for the offering "Weekly asking-price watch for a developer or
brokerage in Egypt". A new client gets a **private** repo from it (Use this template > Create a new
repository > Private); client data never goes into this public repo. Everything that changes per
client is in `config/client.yaml`, `.env` and `data/input/`. The weekly browser run for Bayut Egypt
and Aqarmap stays per-client work.

## Done in the template

What the client gets with no work. Hours are an estimate of building each part from scratch.

| Part | Estimate (hours) |
|---|---|
| Weekly Airflow pipeline in Docker: the warehouse, Airflow's own database, one run per week on the client's schedule and time zone, the run week as the watermark, retries (`dags/`, `docker-compose.yml`, `Dockerfile`) | 4 |
| Four sites read by Airflow (realestate.eg with its unit pages, Property Finder Egypt, Dubizzle Egypt, Nawy): contact fields removed before anything is kept, a pace per site, retries, a canary on page 1, saved pages and tests (`tracker.py`, `sites.py`, `tests/`) | 12 |
| Two sites read in a browser (Bayut Egypt, Aqarmap): the parsers, the browser script and their tests (`browser_sites.py`, `fetch_bayut_aqarmap.py`) | 5 |
| Silver: every row checked (area, type, price, size, the price per m² band), duplicates across sites and areas, quarantine with the reason, counts reconciled per site and area, one transaction (`tracker.py`) | 4 |
| Gold: a star rebuilt per week, the pooled views without Bayut's copies of Dubizzle ads, benchmarks, our units' gaps, price changes (`sql/schema.sql`) | 4 |
| Client settings: `config/client.yaml`, `config.py` (`load_config()`), the units file check, the Power BI theme written from the config (`theme.py`) | 2 |
| Analysis notebook: every number, nine insights with n per group, the 18 Power BI checks run as printed, the README and diagram slots filled (`analysis/analysis.ipynb`) | 6 |
| Power BI build pack: queries, model, measures, three pages, interactions, 18 checks, a build checklist (`powerbi/`) | 8 |
| README, diagrams and the input file guide (`data/input/README.md`) | 3 |
| **Total** | **48** |

## Configure

Per client, file by file. Hours are an estimate.

| File | Key | Example | Estimate (hours) |
|---|---|---|---|
| `config/client.yaml` | `client.name`, `report.title`, `report.colours`, `report.chart_colours` | `Nile Crest Homes`, `"#0F766E"` | 0.5 |
| `.env` | `WAREHOUSE_PASSWORD`; `WAREHOUSE_PORT` and `AIRFLOW_PORT` only if 5451 or 8101 is taken | a new password | 0.25 |
| `data/input/` units | `inputs.units` | `units.csv`: unit code, area, compound as the sites write it, type, bedrooms, m², asking price ([columns](../data/input/README.md)) | 2 |
| `config/client.yaml` areas | `areas` (keep the entries of the client's areas among the six set up), `report.check_area` | `sheikh-zayed`, `north-coast` | 0.25 |
| `config/client.yaml` rules, agreed with the client on a sample | `rules.unit_types`, `rules.price_per_m2_min`, `rules.price_per_m2_max`, `rules.min_group_size` | `[Apartment, Chalet, Town House, Twin House, Studio]`, `12000`, `350000`, `5` | 0.5 |
| `config/client.yaml` schedule | `schedule.cron`, `schedule.timezone` | `"0 1 * * 0"`, `Africa/Cairo` | 0.25 |
| First run: the browser run, the Airflow run, `theme.py` and the notebook; fix what the checks report | | | 1.5 |
| Power BI: build from `powerbi/08-build-checklist.md`; the notebook writes the numbers into `powerbi/06-checks.md` | | | 3 |
| **Total** | | | **8.25** |

`client.currency` stays `EGP`: the sites price in EGP. Property Finder, Nawy, Bayut and Aqarmap drop a
price in another currency and realestate.eg and Dubizzle name none, so another currency is not a label
change but a conversion (custom work, not estimated here).

## Custom

Typical work for one client beyond the template. Hours are an estimate.

| Work | Estimate (hours) |
|---|---|
| **The browser run for Bayut Egypt and Aqarmap** (`python fetch_bayut_aqarmap.py`, on the client's machine or mine): the first run with its cookie banners and logins handled by hand. After that it is about seven minutes by hand each week before the run, not counted here | 1 |
| README, the header and how-it-works diagrams, and the strips of `docs/price-gap-by-area.svg` for the client's areas (the notebook redraws the strips only when they are the config's areas, and says so when they are not) | 3 |
| Hosting the weekly run (a small server or the client's machine) and the Power BI refresh | 3 |
| **Total** | **7** |

## Share already done (estimate)

Template hours ÷ (template + configure + custom) hours = 48 ÷ (48 + 8.25 + 7) = 48 ÷ 63.25 = **76%**
(75.9%), an estimate.

**A client in a city the sites cover but the template does not** (Alexandria, say): each new area is
one more entry under `areas`, with its address on every site (below), about 1.75 hours an area (six
sites at 0.25 hours each, its map coordinates, and a check that page 1 of each search gives rows in
that area). With two new areas, configure grows by 3.5 hours to 11.75, and custom by 0.5 hours to 7.5
for unit labels the parsers do not know yet (a label `sites.py` does not know is quarantined as
"unknown type" until it is added to `UNIT_TYPES`): 48 ÷ (48 + 11.75 + 7.5) = 48 ÷ 67.25 = **71%**
(71.4%), an estimate.

## Adding an area ("tell me the area and I'll add it")

An area is one entry under `areas` in `config/client.yaml`; no code changes. Copy an existing entry
and set, for each site:

| Site | `searches` (`{page}` is the page number) | `locations`: how the site names the area in a listing |
|---|---|---|
| realestate.eg | the area's listings page, `https://realestate.eg/en/listings/<slug>?location=<id>&page={page}`, `max_pages: 8` | the `<slug>` in a card's location link |
| Property Finder | the area's for-sale search page with `?page={page}`, `max_pages: 9` | the area's slug in a listing's `location_tree` (one area can have two spellings) |
| Dubizzle | two searches, apartments and villas (vacation homes on the coast), with `?page={page}`, `max_pages: 4` each | the city's location slug |
| Nawy | `https://www.nawy.com/search?category=property&areas=<id>&page_number={page}`, `max_pages: 17` | the area id `<id>` |
| Bayut | `page`: the area's for-sale page | the `addressLocality` in the page's listings |
| Aqarmap | `path`: the area's part of a for-sale address, `aqarmap.com.eg/en/for-sale/apartment/<path>/` | the same path (a path inside another area's path wins) |

Then `python tracker.py` checks the units file against the new areas, the first extract fails loudly
if page 1 of a search gives no priced row, and `silver.run_log` shows the rows read, saved and set
aside for the area. A site that does not cover the area is left out of its entry.

## Steps

1. Create the private repo from the template and clone it.
2. `cp .env.example .env` and set `WAREHOUSE_PASSWORD` (and the two ports if 5451 or 8101 is taken).
3. Edit `config/client.yaml`: client, areas, rules, schedule, report.
4. Put the units file in `data/input/` ([columns and an example](../data/input/README.md)), delete the
   demo's `our_units.csv`, and run `python tracker.py` to check it.
5. Run `python fetch_bayut_aqarmap.py` (the browser run) before the first weekly run.
6. `docker compose up -d --build`, switch `egypt_real_estate_prices` on in Airflow and trigger it; then
   `python theme.py` and run the notebook.
7. Build the Power BI report from `powerbi/`.

## Nothing hard-coded

This search over the code (`tracker.py`, `sites.py`, `browser_sites.py`, `fetch_bayut_aqarmap.py`,
`config.py`, `theme.py`, `dags/egypt_prices.py`, `sql/schema.sql`, `powerbi/03-measures.dax`), the Power
Query M code in `powerbi/01-power-query.md`, the SQL in `powerbi/06-checks.md` and the notebook's code
cells, for the demo's areas, their names and every site's address token for them, the currency, the
band, the group size, the colours, the units file, the schedule, the client's name and title and the
request pace, finds nothing (it finds 78 lines in the same files before the template, at 49a295e):

```bash
python -c "import json, re
nb = json.load(open('analysis/analysis.ipynb', encoding='utf-8'))
print('\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code'))
for md, lang in (('powerbi/01-power-query.md', 'm'), ('powerbi/06-checks.md', 'sql')):
    print('\n'.join(re.findall(rf'\`\`\`{lang}\n(.*?)\`\`\`', open(md, encoding='utf-8').read(), re.S)))" > /tmp/searched.txt
grep -nE 'new-cairo|new-administrative-capital|sheikh-zayed|sixth-october-city|north-coast|mostakbal-city|New Cairo|New Capital|Sheikh Zayed|6th of October|North Coast|Mostakbal|lmstqbl|el-sheikh-zayed|6-october-city|new-capital-city|new-cairo-city|location=[0-9]|areas=[0-9]|properties-for-sale-in-|\bEGP\b|400_?,?000|10,000 to|MIN_N = [0-9]|PRICE_PER_M2_MIN, PRICE_PER_M2_MAX = [0-9]|#[0-9A-Fa-f]{6}|our_units\.csv|areas\.csv|site_areas|0 0 \* \* 0|\bUTC\b|Demo developer|Egypt real estate prices|DELAY = [0-9]|PACE = [0-9]|sleep\([0-9]' \
  tracker.py sites.py browser_sites.py fetch_bayut_aqarmap.py config.py theme.py dags/egypt_prices.py \
  sql/schema.sql powerbi/03-measures.dax /tmp/searched.txt
# exit code 1: nothing found
```

On purpose outside the search: the ports (5451, 8101) and the database name and user (`prices`) are
infrastructure, set in `docker-compose.yml` with the ports overridable from `.env`; each parser knows
its own site (its labels, its JSON, the time zone of its dates); `make_units.py` made the demo's units;
`tests/` test the demo's parsers on saved pages; the README, the diagrams in `docs/`, the prose of the
Power BI pack and the notebook's markdown cells describe the demo run and keep its values.

## The numbers did not change

The refactor was replayed on the demo's saved pages of week 2026-10-04 (1,804 pages, `data/raw/`) in a
scratch clone, first with the code before the template (49a295e), then with the template code, each in
an empty warehouse. Every table and view gave the same count, sums and md5 over its rows ordered by
natural key (19 of 19), and a second load of the week gave the same again:

| Table | Rows | Sum | md5 |
|---|---|---|---|
| silver.price_observation | 5,757 | asking_price 99,950,577,904 | `3654952e089b82640cefbab2416a89c4` |
| silver.listing | 5,757 | size_m2 1,248,704 | `13b7179ff15dec9d89c19e993c168f7f` |
| silver.quarantine | 41 | | `761b0cd9b09960fa3a5b20eb48d03aaf` |
| silver.run_log | 36 | rows_saved 5,757, rows_quarantined 41 | `fc07f4fa5aa57e63316c94bf877d5723` |
| gold.fact_listing_price | 5,757 | asking_price 99,950,577,904 | `535819a789e3ca7df97de08d972567f1` |
| gold.pooled_listing_price | 5,619 | asking_price 98,228,898,938 | |
| gold.unit_gap | 60 | gap_pct 100.65 | `12349485358745fc48f8979aad45b470` |

The notebook, run on each, wrote the same `numbers.json` (137 keys; the template's under its renamed
keys). Against the published file only two values differ, both from the published warehouse's earlier
loads of the week rather than from the code: `price_observations` (5,786 published, 5,757 on a fresh
load: silver keeps the prices an earlier load saved) and `table_rows_compound` (1,336 against 1,291:
compounds are never deleted). The Airflow run time is not in a replay.

## Second-client drill (2026-10-05)

The acceptance test of the template: a fresh clone from GitHub, a made-up second client, a run in
Airflow from scratch, and every unit's numbers checked against a calculation by hand.

**Client B (drill):** Nile Crest Homes, made up. Two areas, named its own way: Zayed (`sheikh-zayed`)
and Sahel (`north-coast`, also the check area). Compares Apartment, Chalet, Town House, Twin House and
Studio only (a villa, duplex or penthouse listing is skipped); band 12,000 to 350,000 per m²; groups of
5 or more; runs Sundays at 1am Cairo time (`"0 1 * * 0"`, `Africa/Cairo`); teal colours (`#0F766E`
main, page `#F0FDFA`), title "Nile Crest market watch". Units: 8 rows in `units.csv`, with two extra
columns (`code_ignored` first, `floor` last). Pages: the demo's week 2026-10-04 cut down to what this
client's own run would read, 564 of 1,804 pages (realestate.eg 483 of 1,565, Property Finder 16 of 49,
Dubizzle 16 of 48, Nawy 31 of 92, Bayut 3 of 7, Aqarmap 15 of 43). Its own Docker project
(`-p re-drill`, ports 5461 and 8111), removed with `down -v` afterwards.

| What | Demo (replay) | Client B (drill) |
|---|---|---|
| Schedule as Airflow parsed it | Sundays 12am, UTC | `0 1 * * 0`, next interval 2026-10-03 22:00 to 2026-10-10 22:00 UTC (Sunday 1am Cairo) |
| Run | | triggered for 2026-10-05 00:00 UTC: interval end 2026-10-03 22:00 UTC, week 2026-10-04; 7 tasks succeeded in 55.323 s, the four extracts skipped (week already read) |
| Rows parsed = skipped + duplicate + saved + quarantined | 6,854 = 935 + 121 + 5,757 + 41 | 2,147 = 732 + 1 + 1,391 + 23 |
| Quarantined, by reason | 11 price missing, 29 outside 10,000 to 400,000, 1 unknown type | 6 price missing, 17 outside 12,000 to 350,000 |
| Asking prices kept, competing listings (pooled) | 5,757, 5,619 | 1,391 (sum 21,193,834,180 EGP), 1,367 |
| Our units | 60 in 6 areas | 8 in 2 areas (sum of asking prices 134,200,000 EGP, 1,275 m²) |
| Area gaps (median of our units' gaps) | widest 6th of October +7.38% | Sahel -9.76% over 5 units, Zayed +0.19% over 3 units; widest Sahel |
| Power BI theme | "Egypt real estate prices", `#2563EB` | "Nile Crest market watch", `#0F766E`, page `#F0FDFA` |
| Notebook | | 0 errors; client name, EGP and groups of 5 in the text; 18 checks run; README 36, 06-checks 71, checklist 17 and header 5 slots filled; the checks name Sahel; the price-gap strips (the demo's six areas) left as they are, with a note |
| Second run of the same week | the same 19 fingerprints | the same 19 fingerprints |

**By hand:** each unit's price per m², the median of the pooled listings of its type in its area
(silver prices, Bayut's copies of Dubizzle ads left out, one plain SQL query and Python's
`statistics.median`), its gap and the listings cheaper than it, against `gold.unit_gap`. Every saved
row is in the two areas, of a compared type, and priced from 12,345.68 to 331,479.95 per m².

| Unit | Area | Type | Ours per m² | Listings | Median per m² | Gap by hand | `gold.unit_gap` | Cheaper by hand | Gold |
|---|---|---|---|---|---|---|---|---|---|
| Z-001 | Zayed | Apartment | 50,714.29 | 382 | 50,616.46 | 0.19% | 0.19% | 192 | 192 |
| Z-002 | Zayed | Apartment | 80,000.00 | 382 | 50,616.46 | 58.05% | 58.05% | 286 | 286 |
| Z-003 | Zayed | Town House | 56,818.18 | 99 | 69,166.67 | -17.85% | -17.85% | 33 | 33 |
| S-001 | Sahel | Chalet | 154,545.45 | 454 | 94,086.06 | 64.26% | 64.26% | 400 | 400 |
| S-002 | Sahel | Chalet | 84,210.53 | 454 | 94,086.06 | -10.50% | -10.50% | 188 | 188 |
| S-003 | Sahel | Twin House | 115,384.62 | 89 | 128,047.96 | -9.89% | -9.89% | 40 | 40 |
| S-004 | Sahel | Apartment | 184,615.38 | 72 | 52,666.83 | 250.53% | 250.53% | 60 | 60 |
| S-005 | Sahel | Town House | 130,000.00 | 78 | 144,061.30 | -9.76% | -9.76% | 25 | 25 |

8 of 8 match. The area medians follow: Sahel's five gaps (-10.50, -9.89, -9.76, 64.26, 250.53) have
median -9.76, Zayed's three (-17.85, 0.19, 58.05) median 0.19.

**Clear failures**, run on the client B copy, each with one line before the warehouse is touched:

```
data/input/units.csv is missing column(s): asking_price
data/input/units.csv line 6 (S-002): area new-cairo is not an id under areas in config/client.yaml
data/input/units.csv line 7 (S-003): unit type Villa is not in rules.unit_types in config/client.yaml
data/input/units.csv line 6 (S-002): size_m2 and asking_price must be numbers above 0
missing input file data/input/units.csv (inputs.units in config/client.yaml)
config/client.yaml report.check_area new-cairo is not an id under areas
config/client.yaml is missing rules.min_group_size
config/client.yaml rules.unit_types: Bungalow is not a type sites.py knows
config/client.yaml is not valid YAML near line 81 (quote a value with # or :)
WAREHOUSE_PASSWORD is not set (copy .env.example to .env; outside Docker, export it)
```

An empty week fails loudly and leaves the warehouse as it was (the same 19 fingerprints after):
week 2026-10-11, never read, stops with `RuntimeError: ...data/raw/realestate/2026-10-11 has no
_done: its extract did not finish`; week 2026-10-18, read but with no page, stops with
`RuntimeError: No asking price saved for 2026-10-18`.

One test did not fail: with `currency: USD`, Property Finder, Nawy, Bayut and Aqarmap gave no prices
but realestate.eg and Dubizzle kept theirs (738 saved, 676 quarantined), which is why `currency`
stays EGP above. The drill's warehouse was reloaded with EGP afterwards and gave the same 19
fingerprints again.

## Gaps against the template standard

- **No `warehouse` group in `client.yaml`, no `db_url`, no `.env` loaded by `load_config()`.** The
  ports are infrastructure and come from `.env` with today's values as defaults (`WAREHOUSE_PORT`,
  `AIRFLOW_PORT`); the database name and user stay `prices`; `tracker.py` reads the password from the
  environment (Compose sets it, outside Docker it is exported) and the notebook reads `.env` itself.
  Loading `.env` in `load_config()` would turn the warehouse tests on for anyone without the stack up.
- **Areas are in `client.yaml`, not an input file with a foreign key**, as asked for this template; a
  unit's area is checked against them before the warehouse is touched instead.
- **No header spellings (`columns`) and no value map** for the units file: it needs the column names
  in `data/input/README.md`, and `bedrooms` is not checked (a non-number stops the load in Postgres).
- **`make_units.py` stays at the root** (demo tooling) instead of `data/demo/`; it is named as outside
  the search instead.
- **No alert e-mail key:** nothing in this repo sends e-mail, and a key exists only if something reads it.
- **Two report keys beyond the standard's slots:** `report.check_area` (the area of checks C7, C13 and
  C18, like the standard's `report.check_month`, set on the database as `client.check_area` by the
  first database task of every run) and `report.chart_colours` (the notebook's dark chart palette).
- **`client.currency` is not free to change** (above).
- **The strips of `docs/price-gap-by-area.svg` are drawn once per client** by hand; the notebook moves
  them only when they are the config's areas.
