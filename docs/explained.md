# The project explained, from zero

This page explains the whole project in plain words: what it does, what every word means, where every number comes from, and how to talk about it in an interview. You do not need to know SQL, Airflow or Power BI to read it.

[← Back to the README](../README.md)

## 1. The project in one minute

A company that sells flats and villas in Egypt has to set an asking price for each unit. The competing units are listed on six listing websites, in the same areas. Someone checks those websites by hand now and then, and nobody writes the old prices down. So nobody can answer simple questions:

- Is our price per square metre above or below the units around it?
- Which area has the widest gap?
- Who cut their price this week?

This project answers them. Once a week, a program reads the asking prices from six listing sites in six areas. It checks every row, sets aside the bad ones with the reason, and keeps every price with its week, so a cut can be shown later. Then it compares each of our units with the listings of the same type in the same area, and a Power BI report shows the result.

Think of it like walking past every estate agent's window in six neighbourhoods each Sunday, writing every price card into a notebook, and laying your own price tags next to them. Because the notebook keeps every week, you can see who lowered a price since last Sunday.

## 2. Words you will meet

| Word | What it means here |
|---|---|
| **EGP** | Egyptian pound, the currency of every price here. Prices are kept as the sites show them; a price in another currency is treated as no price. |
| **m², sqm** | Square metre, the unit of size. "139 m²" means 139 square metres. |
| **Asking price** | The price a seller puts on a listing. It is what the seller asks, not what a buyer finally paid. |
| **Price per m²** | Asking price divided by size. It lets a 100 m² flat and a 400 m² villa be compared on one scale. |
| **Listing** | One unit for sale on one site, with its own id on that site. |
| **Listing site** | A website where units are advertised. The six here: realestate.eg, Property Finder Egypt, Dubizzle (OLX) Egypt, Nawy, Bayut Egypt and Aqarmap. |
| **Area** | One of the six places watched: New Cairo, New Capital, Sheikh Zayed, 6th of October, North Coast and Mostakbal City. Each has an id, like `new-cairo`, in `config/client.yaml`. |
| **Compound** | A gated development with its own name, like "Villette". Names are kept as each site writes them. |
| **Developer** | The company that builds a compound, like SODIC. Only realestate.eg, Nawy and Aqarmap name one. |
| **Unit type** | Apartment, Villa, Town House, Twin House, Duplex, Penthouse, Chalet, Studio, iVilla, Cabin or Loft: the 11 types compared (`rules.unit_types`). |
| **Our units** | The client's units for sale, in `data/input/our_units.csv`. In this repo they are made up by `make_units.py`, because the client is not named. The competing listings are real. |
| **Median** | The middle value when all values are sorted. Half the listings ask more, half ask less. It is used instead of the average because one very expensive villa can pull an average up a lot. |
| **Percentile** | The 25th percentile is the value a quarter of listings sit below; the 75th, three quarters. The **middle half** is everything between the two. The 10th and 90th leave out the cheapest and dearest tenth. |
| **Gap** | How far one of our units is from the median price per m² of the same type in the same area, in percent. +10% means we ask 10% more. |
| **Scraping** | Reading web pages with a program instead of by eye. Here the program reads the data block the page already carries (JSON) rather than the visible text. |
| **HTML, JSON, JSON-LD** | HTML is the code of a web page. JSON is a text format for data, like `{"price": 15600000}`. JSON-LD is JSON a page embeds to describe itself to search engines; realestate.eg, Bayut and Aqarmap carry their prices there. |
| **Pace** | The wait between two requests to one site: 2.5 seconds for the four automated sites, 5 seconds for the two browser sites (`pace_seconds` in `config/client.yaml`). |
| **Browser run** | Bayut Egypt and Aqarmap refuse plain programs, so `fetch_bayut_aqarmap.py` opens them in a real, visible browser window before the weekly run and saves the pages. A person deals with any check or cookie banner. |
| **Bronze, silver, gold** | The three layers of the warehouse. **Bronze**: the pages exactly as read, saved on disk, plus a log of every page read. **Silver**: clean, checked rows, one table per thing. **Gold**: the star schema the report reads. See [layers.svg](layers.svg). |
| **Warehouse, PostgreSQL** | The database that holds silver and gold. PostgreSQL (often "Postgres") is a free, widely used database. Here it runs in Docker on port 5451. |
| **Schema** | A folder of tables inside the database: `bronze`, `silver` and `gold`. |
| **Run week** | The week a run belongs to, named by the Sunday it starts: "the week of 4 October 2026". Every saved price carries its run week. |
| **Watermark** | How the pipeline knows what it has done. Here it is the run week: a finished week's folder gets a `_done` file and is skipped next time. |
| **Canary** | A tripwire. If page 1 of a search gives no priced row, the site has probably changed its pages, so the run stops loudly instead of saving an empty week. |
| **Parse** | Turn a saved page into rows with the same columns: site, listing id, area, compound, developer, type, bedrooms, size, price. |
| **Skipped** | A row that is not a home (a shop, office, clinic) or is outside the six areas. Counted, not kept. |
| **Duplicate** | The same listing on the same site read a second time in one run, for example through two searches that overlap. Counted once. |
| **Quarantine** | Where a row that fails a check goes, kept with its reason: unknown type, price missing, size missing, or price per m² outside 10,000 to 400,000 EGP. Table `silver.quarantine`. |
| **Reconcile** | Prove the counts add up: rows parsed = skipped + duplicate + saved + quarantined, for every site and area. If not, the run fails. |
| **Append-only** | Rows are only ever added, never changed or deleted. Every asking price is kept with its week in `silver.price_observation`, so old prices are never lost. |
| **Pooled** | All sites counted together. The pooled view leaves out the Bayut Egypt rows that copy a Dubizzle ad (same listing id in the same week), so one ad is not counted twice. |
| **Twin** | A likely copy of one listing on another site: same area, compound and type, size within 2 m² and price within 2%. An estimate. |
| **Stated total, coverage** | The number of results a site's own search page says it has. Coverage = listings the run read / stated total. |
| **Developer index** | A developer's median price per m² against its area's median, where 100 = the area median. 219 means more than twice the area median. |
| **Size band** | A size group: under 100 m², 100 to 150, 150 to 200, 200 to 300, and 300 and over. |
| **Group of 10** | The insights leave out any group with fewer than 10 listings (`rules.min_group_size`), and say how many they left out. A median of 3 listings says little. |
| **Fact table** | The big table of events you count and measure. Here `gold.fact_listing_price`: one row per site, listing and run week, with the price. |
| **Dimension table** | A small lookup table that describes the facts: sites, areas, compounds, unit types and weeks. You filter and group by them. |
| **Star schema** | One fact table in the middle with dimension tables around it, like a star. See [data-model.svg](data-model.svg). |
| **Grain** | What one row of a table stands for. The grain of `gold.fact_listing_price` is "one site, one listing, one run week". |
| **Natural key, surrogate key** | A natural key exists in the data (the site plus its listing id). A surrogate key is a made-up number (1, 2, 3) the warehouse gives each dimension row, like `area_key`. |
| **Degenerate dimension** | A key kept in the fact table with no table of its own: `listing_id`, the site's own id. |
| **View** | A saved query that looks like a table. `gold.unit_gap`, `gold.area_gap` and `gold.price_change` are views, worked out fresh each time they are read. |
| **Airflow, DAG, task** | Apache Airflow runs the pipeline on a schedule. A DAG is one pipeline (`egypt_real_estate_prices`); a task is one step in it (`extract_nawy`, `load_silver`, ...). It runs every Sunday at midnight UTC. |
| **Docker, Docker Compose** | Docker runs programs in ready-made boxes called containers, so nobody installs PostgreSQL or Airflow by hand. `docker-compose.yml` starts three: the warehouse, Airflow's own database and Airflow (port 8101). |
| **`.env`** | A file for the database password. It is never committed; `.env.example` shows its shape. |
| **`config/client.yaml`** | Every value a client would change: the areas and each site's search address for them, the sites and their pace, the rules, the schedule, the colours. |
| **Notebook** | `analysis/analysis.ipynb`, a file that mixes code, its output and notes. It reads the warehouse, works out every number in the README, writes `analysis/numbers.json` and fills the README and the pictures from it. |
| **Power BI** | Microsoft's tool for interactive reports. The `powerbi/` folder rebuilds the report step by step. |

## 3. How it works, file by file

Run in this order (the commands are in the README's "Run it" section):

| Step | File | What it does |
|---|---|---|
| 0 | `docker-compose.yml`, `Dockerfile` | Starts the warehouse (PostgreSQL 17, port 5451), Airflow's own database, and Airflow 3 (port 8101). |
| 0 | `config/client.yaml`, `config.py` | Hold every client value; `config.py` reads and checks them, so no other file types a value by hand. |
| 1 | `fetch_bayut_aqarmap.py` | Run by hand before the weekly run. Opens Bayut Egypt and Aqarmap in a visible browser and saves each page under `data/raw/<site>/<run week>/`, with a `summary.csv` line per page and a `_done` file. |
| 2 | `dags/egypt_prices.py` → `extract_<site>` x4 | Airflow reads realestate.eg, Property Finder Egypt, Dubizzle Egypt and Nawy in parallel, each at its own pace. Every page is saved gzipped under `data/raw/`, with an `index.csv` line per page. The JSON sites keep only the page's data block, with every agent, broker and contact field removed first (`sites.py`). |
| 3 | `load_silver` in `tracker.py` | Checks the units file, runs `sql/schema.sql`, parses every saved page of the week (`tracker.py`, `sites.py`, `browser_sites.py`), checks each row, saves the good ones to silver, quarantines the rest with the reason, logs the counts per site and area in `silver.run_log`, and fails if they do not reconcile. All in one transaction. |
| 4 | `build_gold` → `gold.build()` in `sql/schema.sql` | Rebuilds the star for the week: dimensions first, then that week's fact rows. Checks that gold holds exactly silver's prices for the week less the quarantined ones. |
| 5 | `report` in `tracker.py` | Prints the week's price cuts and the areas ranked by our gap, in the Airflow log. |
| 6 | `analysis/analysis.ipynb` | Works out every number, draws every chart in `docs/`, writes `analysis/numbers.json` and fills the README and the SVG pictures. |
| 7 | `powerbi/` | Step-by-step instructions to build the Power BI report on gold, and the numbers each card must show (`06-checks.md`). |

`make_units.py` is demo tooling, run once: it made the 60 units in `data/input/our_units.csv`. `tests/` checks the page parsing for every site and the rules above on saved sample pages.

### One real listing, from web page to final number

Nawy listing **55420**, read for the run week of 4 October 2026. All of this is traced by running the repo's own parser and checks on the saved page; the notebook prints group totals, not this one row.

1. **Read (bronze).** The weekly run asked Nawy for page 1 of its New Cairo search (`areas=2` in `config/client.yaml`). The page said the search holds 6,696 results; page 1 carried 12. The run kept the page's data block, contact fields removed, as `data/raw/nawy/2026-10-04/new-cairo-all-page-1.json.gz`, and logged the read in `index.csv` at 02:55 UTC on 5 October. The run week is still 4 October, because the week is named by the Sunday it starts.
2. **Parse.** `parse_nawy` in `sites.py` turned it into one row: Apartment, 2 bedrooms, 139 m², asking price 15,600,000 EGP, compound Villette, developer SODIC. Nawy files it under "Golden Square", which is not one of our areas, so the parser takes its parent area, New Cairo.
3. **Check (silver).** It is a home type we compare, it is in our areas, it was not read before this run, it has a price and a size. Price per m²: 15,600,000 / 139 = **112,230.22 EGP**, inside the 10,000 to 400,000 band. So it is **saved**: one row in `silver.listing`, one row in `silver.price_observation` for the week. On the same page, listing 126197 is an "Administrative" unit, so it is **skipped**, and listing 110590 sits in Mostakbal City, so it gets Mostakbal City as its area even though the New Cairo search found it.
4. **A row that is set aside.** Nawy listing 4381, a 459 m² villa asking 228,500,000 EGP, works out at 497,821.35 EGP per m². That is above 400,000, so it goes to `silver.quarantine` with the reason "price per m² outside 10,000 to 400,000". It is kept, not deleted, and stays out of gold.
5. **Gold.** Listing 55420 becomes one row of `gold.fact_listing_price`, keyed by its site, its id and the week. It is a Nawy row, so the pooled view keeps it.
6. **Compare.** It is one of the 398 New Cairo apartments whose median is **63,818.18 EGP per m²** (`gold.area_benchmark`, notebook cell 10). It asks 75.9% more than that median (worked out here).
7. **Against our units.** Our unit NC-APT-01 is a 150 m² apartment in Eastown, New Cairo, asking 9,580,000 EGP: 9,580,000 / 150 = 63,866.67 EGP per m². Its gap is (63,866.67 − 63,818.18) / 63,818.18 = **+0.08%** (`gold.unit_gap`, notebook cell 13). Our four New Cairo apartments ask 62,324.32, 63,866.67, 70,700.00 and 71,407.41 per m², so their median is 67,283.335 (worked out here). Listing 55420, at 112,230.22, is not cheaper than that, so it counts in the 4,929 listings compared but not in the 2,485 that ask less than ours.

## 4. Every number, explained

All of these are printed by the notebook ([`analysis/analysis.ipynb`](../analysis/analysis.ipynb)) unless the row says otherwise. The cell numbers below count from 0, the first cell. Every number is for the run week of 4 October 2026, the only run week so far.

### The headline and the results list

| Number | What it means | How it is worked out | Where |
|---|---|---|---|
| **6 listing sites** | realestate.eg, Property Finder Egypt, Dubizzle (OLX) Egypt, Nawy, Bayut Egypt and Aqarmap. | Count of sites with at least one row in `gold.fact_listing_price` in the run week. | cell 3 |
| **6 areas** | New Cairo, New Capital, Sheikh Zayed, 6th of October, North Coast, Mostakbal City. | Count of areas with at least one row in the same table. | cell 3 |
| **4 October 2026** | The run week, named by its Sunday. The Airflow run itself ran on 5 October 2026. | The newest week in `gold.dim_week`. | cell 3 |
| **5,619 competing listings compared** | Every listing of the week, counted once. | 5,757 rows in gold less 138 Bayut Egypt rows that copy a Dubizzle ad: count of `gold.pooled_listing_price`. | cells 3, 32 |
| **6th of October, +7.4%** | The area where our units are furthest from their market. | Each unit's gap against the median of its type in its area, then the median of the 10 gaps per area. In 6th of October the sorted gaps are −13.97, −8.87, −1.39, −1.05, 5.70, 9.06, 9.23, 9.96, 12.50, 12.68; the middle two average (5.70 + 9.06) / 2 = 7.38. No other area is further from 0. | `gold.area_gap`; cells 13, 25 |
| **5,757 asking prices kept** | Every price saved, all run weeks. | Count of `silver.price_observation`. With one week, it equals the week's gold rows. | cell 3 |
| **1 weekly run, 4 October 2026 to 4 October 2026** | Only one week has been read so far, so the first and last week are the same. | Count, first and last of the run weeks in `silver.price_observation`. | cell 3 |
| **1,152 compound names** | Compounds named on at least one listing. | Distinct names, not "Unknown", with at least one listing; a name used in two areas counts once (1,171 area and compound pairs). | cell 20 |
| **307 developers** | Developers named on at least one listing. | Distinct names, not "Unknown". Only three sites name a developer, so 3,572 of the 5,757 listings have none. | cell 20 |
| **60 units** | Our units: 10 per area, made up by `make_units.py`. | Count of `gold.fact_our_unit`. | cell 13 |
| **50.4% of 4,929** | Half the competing listings ask less per m² than our typical unit. | 4,929 = pooled listings in an area and type where we have a unit. 2,485 of them ask less per m² than our median unit of that type and area. 2,485 / 4,929 = 50.4%. | cell 18 |
| **41 rows set aside (0.7%)** | Rows that failed a check, kept with their reason. | 41 / 5,798 rows checked, where 5,798 = 5,757 saved + 41 quarantined. | cell 27 |
| **"price per m² outside 10,000 to 400,000", 29 rows** | The most common reason. | 16 of the 29 came from Property Finder Egypt. The other reasons: "price missing or <= 0", 11 rows; "unknown type", 1 row. | cells 27, 56 |
| **114.2% more per m², North Coast against New Capital** | The dearest area against the cheapest. | Median price per m², all types and sites: North Coast 113,511.10 (n 1,000), New Capital 53,000.00 (n 850). 113,511.10 / 53,000 − 1 = 114.2%. | cell 34; same medians in cell 10 |
| **369.1% North Coast, 218.6% Mostakbal City** | How spread out prices are inside one area. | The 90th percentile over the 10th, minus 1. North Coast: 213,077.00 against 45,422.38. Mostakbal City: 102,693.50 against 32,235.71. | cell 52 |
| **7 of 9 unit types** | In most types, the biggest units ask less per m² than the smallest. | 9 types have two or more size bands with 10+ listings. In 7, the largest band's median per m² is below the smallest band's: apartments, for one, go from 63,330.42 under 100 m² to 40,000.00 at 300 m² and over. Chalet and iVilla go the other way. | cell 42 |
| **Index 219 for ADD Properties, of 48 developers; Amer Group 62** | The dearest and cheapest developer against their areas. | Each listing's price per m² / its area's median × 100, then the median per developer. Only the 48 developers with 10+ listings count (259 smaller ones left out). ADD Properties: 218.65 over 12 listings. Amer Group: 61.67 over 16. | cell 38 |
| **Nawy above Dubizzle in 6 of 6 areas** | Nawy's prices per m² are higher than Dubizzle's everywhere. | Each site's own rows, median per area, in areas where both have 10+ listings. Nawy is higher by +14.0% (New Capital) to +83.9% (Sheikh Zayed). | cell 44 |
| **0.1% to 12.5% of each site's own count** | How much of each site the run reads. | Rows read / the results the site's searches say they hold. Bayut Egypt: 144 of 123,108. realestate.eg: 1,650 of 13,242. | cells 8, 54 |
| **about 1.7% with a likely twin** | Listings that probably appear on two sites. | 84 of the 4,965 pooled listings with a named compound match a listing on another site (same area, compound and type, size within 2 m², price within 2%). An estimate. | cell 46 |
| **0 cuts in the latest run week** | No price cuts yet. | A cut needs the same listing in two run weeks. There is one. | cells 22, 50 |
| **at least 40 minutes, 2.5 seconds** | How long a live read of the sites takes, as an estimate, not a timing. | The slowest site, realestate.eg, read 969 pages this week. 969 × 2.5 seconds / 60 = 40.375 minutes. The sites' own answer time and the two browser sites are not in it, hence "at least". | cell 30 |
| **2.5 and 5 seconds** | The wait between requests: 2.5 seconds for the automated sites, 5 for the browser sites. | `pace_seconds` per site. | `config/client.yaml` |
| **10,000 to 400,000** | The band a price per m² must fall in. | `rules.price_per_m2_min` and `price_per_m2_max`. | `config/client.yaml` |
| **10 or more listings** | The smallest group an insight measures. | `rules.min_group_size`. | `config/client.yaml` |
| **ports 8101 and 5451** | Where Airflow and the warehouse listen on your machine. | The defaults, changeable in `.env`. | `docker-compose.yml` |

### The insights, one by one

Each chart in the README is drawn by the notebook. In plain words:

| Chart | What it shows | Why it matters |
|---|---|---|
| listings-by-area.png | The 5,757 rows by area and site. Every area has between 874 (New Capital) and 1,019 (North Coast). Dubizzle Egypt gives the most, 2,150. | The comparison stands on a similar number of listings in every area. (cell 5) |
| gap-by-area.png | The median gap of our units per area, from +7.4% in 6th of October to −0.7% in New Cairo. | The first question a sales manager asks: where are we priced high? (cell 14) |
| 1. Area ranking | North Coast is dearest per m², New Capital cheapest, 114.2% apart. | Areas cannot share one price list. (cell 34) |
| 2. Type by area | Median per m² for every type and area with 10+ listings. Widest within one area: North Coast duplexes at 171,058 against apartments at 52,667 per m², 224.8% apart (duplexes n 10). | An area median hides the type. That is why each unit is compared with its own type. (cell 36) |
| 3. Developer index | ADD Properties 219, Amer Group 62, where 100 is the area median. | The developer's name moves price per m² a lot. (cell 38) |
| 4. Compounds | The cheapest and dearest compound with 10+ listings in each area. Widest: North Coast, Dayz at 338,127 against Telal North Coast at 65,509, 416.2% apart (n 10 each). | Within one area, the compound matters as much as the area. (cell 40) |
| 5. Size and bedrooms | Price per m² by size band; price per bedroom. 1 bedroom: 5,235,000 EGP median (n 385). | Bigger units ask less per m² in 7 of 9 types. These are different listings side by side, so it does not prove that size lowers price. (cell 42) |
| 6. Site differences | Each site's median in each area. | Which sites you read changes the answer. Nawy is above Dubizzle in all 6 areas; the README gives the likely reason, Nawy mostly showing developers' launch prices and Dubizzle being a resale marketplace, and the notebook says it is not proven. (cell 44) |
| 7. Cross-site duplicates | About 1.7% of listings have a likely twin on another site. Property Finder Egypt has the highest share, 33 of 773 (4.3%). | Twins would count one unit twice. The share is small, and the exact copies (Bayut of Dubizzle) are already left out. (cell 46) |
| 8. Our units | Our ten units furthest above the median of their type and area, led by NC-VIL-02 at +15.0%. | The units a seller should look at first. Made-up units here. (cell 48) |
| 9. Week over week | Not drawn yet: it needs two run weeks. | From the second run it shows cuts, rises, new and dropped listings. (cell 50) |
| price-cuts-by-week.png | Cuts and rises per run week: 0 and 0 for the first week. | Answers "who cut prices", from the second week on. (cell 23) |
| 10. Price spread | Middle half and 10th to 90th percentile per area. North Coast widest, Mostakbal City narrowest. | A wide spread means one area median says little about a single unit. (cell 52) |
| 11. Coverage | Each site read against its own count, 0.1% to 12.5%. | It is a sample of each site, not all of it. A site is compared with itself week to week. (cell 54) |
| 12. Rows set aside | Of 6,854 rows parsed: 935 skipped, 121 duplicates, 41 quarantined, by reason and site. | Every row is accounted for; nothing disappears quietly. (cell 56) |
| 13. Site and type | Listings per site and type. Apartment is the most listed type on all 6 sites, 2,121 of 5,619 (37.7%). Bayut Egypt keeps only 5 pooled rows. | Shows which site feeds which type. (cell 58) |
| 14. Units against market | One dot per unit: 35 of 60 ask more than their market, 25 the same or less, from −14.9% (NCO-CH-05) to +15.0% (NC-VIL-02). | The spread of our own pricing at a glance. (cell 60) |

Things that can look wrong but are not:

- **5,757 rows but 5,619 listings.** Bayut Egypt shows many of Dubizzle's ads: 138 of Bayut's 143 rows have the same listing id as a Dubizzle row that week. They stay in the fact table and are left out of every pooled number.
- **6,854 rows read but 5,757 saved.** 935 were skipped, mostly shops, offices and clinics that realestate.eg (714) and Nawy (204) list beside homes; 121 were duplicates; 41 were quarantined. 935 + 121 + 5,757 + 41 = 6,854.
- **0.7% set aside, but 41 / 6,854 is 0.6%.** The share is over the 5,798 rows that reached the checks (saved or quarantined), not over every row read. Skipped and duplicate rows never reach the price checks.
- **Three kinds of duplicate.** 121 are the same listing read twice on the same site in one run, when two searches overlap: Aqarmap, for example, files Mostakbal City under New Cairo. 138 are Bayut copies of Dubizzle ads. 84 are estimated twins across sites. Each is handled in its own place.
- **1,152 compounds, but `dim_compound` has 1,291 rows.** A `dim_compound` row is one area, compound and developer, with "Unknown" when a site names none, and it also holds our units' compounds.
- **A dot left of the area median with a positive gap.** The band and tick on the strip cover all unit types; the gap compares a unit with its own type only. CAP-APT-02 asks 38,818.18 per m², far left of New Capital's all-type median of 53,000, yet it is +1.82% against New Capital apartments (38,122.64).
- **Two "listings cheaper" shares.** The README and the strip picture use the notebook's count (cell 18): 6th of October 50.9%. The `report` task prints `gold.area_gap.pct_listings_cheaper`, which compares every unit with every listing and adds them up: 50.96 for 6th of October. Both are kept, under their own names.
- **North Coast gap −0.1% on the picture.** The exact value is −0.05%; slots round half away from zero to one decimal.
- **Areas per site do not match `run_log`.** A listing gets the area from its own location, not from the search that found it. Nawy's New Cairo search found listing 110590 in Mostakbal City, so it counts there.

### The diagrams

| Number | Where you see it | What it means |
|---|---|---|
| **5,619**, **+7.4**, **6th of October**, **6 sites**, **6 areas** | header.svg | The same numbers as the headline above. |
| **30,000** and **170,000** | price-gap-by-area.svg | The ends of the shared price-per-m² scale: the lowest 25th percentile or unit price, and the highest 75th percentile or unit price, widened to the next 10,000 EGP. (cell 16) |
| **113,511, 76,142, 62,069, 58,149, 56,311, 53,000** | price-gap-by-area.svg | The tick: each area's median price per m² over all types, North Coast, New Cairo, Sheikh Zayed, 6th of October, Mostakbal City, New Capital. (cell 10) |
| **+7.4, +2.8, +1.9, −0.7, −0.6, −0.1** | price-gap-by-area.svg | The median gap of our units: 6th of October, Sheikh Zayed, New Capital, New Cairo, Mostakbal City, North Coast. (cell 13) |
| **52.9, 51.9, 50.9, 50.6, 49.5, 46.9** | price-gap-by-area.svg | Listings cheaper than our median unit, in percent: New Capital, New Cairo, 6th of October, Sheikh Zayed, North Coast, Mostakbal City. (cell 18) |
| **1,804** | data-flow.svg | Rows in `bronze.fetch_log`: every page read logged for the week, home pages included. Not printed by the notebook; counted for this page from the six `index.csv` and `summary.csv` files of the week (1,565 realestate.eg, 49 Property Finder, 48 Dubizzle, 92 Nawy, 7 Bayut, 43 Aqarmap). A page read more than once is logged each time: realestate.eg's 1,565 lines are 969 different pages. |
| **5,757** (x3) | data-flow.svg, data-model.svg | Rows in `silver.price_observation`, `silver.listing` and `gold.fact_listing_price`. With one run week, each saved listing has one listing row and one price row. |
| **41** | data-flow.svg | Rows in `silver.quarantine`. (cell 27) |
| **36** | data-flow.svg | Rows in `silver.run_log`: 6 sites × 6 areas, one row each. (cell 8, "0 of 36 searches") |
| **60** | data-flow.svg, data-model.svg | Our units in `silver.our_unit`, `gold.fact_our_unit` and the view `gold.unit_gap`. |
| **6** | data-flow.svg, data-model.svg | Rows in `silver.area`, `gold.dim_area`, `gold.dim_site` and the view `gold.area_gap`. |
| **1,291** | data-flow.svg, data-model.svg | Rows in `gold.dim_compound`: one per area, compound and developer. (cell 63) |
| **11** | data-flow.svg, data-model.svg | Rows in `gold.dim_property_type`: all 11 compared types appear. (cell 63) |
| **1** | data-flow.svg, data-model.svg | Rows in `gold.dim_week`: one run week. (cell 63) |
| **5,619** | data-flow.svg, data-model.svg | Rows in the view `gold.pooled_listing_price`. (cell 32) |
| **0** | data-flow.svg, data-model.svg | Rows in the view `gold.price_change`: no second week yet. (cell 63) |
| **55** | data-flow.svg, data-model.svg | Rows in `gold.area_benchmark`: one per area and type with listings. (cell 63) |
| **234** | data-flow.svg, data-model.svg | Rows in `gold.area_site_benchmark`: one per site, area and type with listings. (cell 63) |
| **x4** | data-flow.svg | Four extract tasks, one per automated site. |
| **1 to \*** | data-model.svg | One dimension row links to many fact rows: one area has many listings. |
| **01 to 05** | how-it-works.svg | The five steps: collect, check, store, compare, report. |

## 5. What the results mean for the business

- **Our units are made up, so the gap numbers show the method.** Each one was priced 15% below to 15% above its market on purpose, so "half the market is cheaper than us" is what you would expect. With a real client's units, the same numbers become the answer to "are we priced right?". The market numbers (medians, spreads, compounds, developers, coverage) are measured from the sites.
- **Price by area and type, never by one Egypt-wide number.** North Coast asks more than twice the New Capital median per m², and inside one area the dearest type can ask more than three times the cheapest.
- **The brand and the compound move price a lot.** One developer asks more than twice its area median, another about 60% of it. A seller should benchmark against the same compound or the same class of developer, not only the area.
- **Say which sites you read.** Nawy is above Dubizzle in every area. A report built on one site alone would tell a different story, so the report can show all sites together or one at a time.
- **A price cut can be shown, not guessed.** Every price is kept with its week. From the second weekly run, every listing that asks less per m² than the week before shows up with its old and new price.
- **Bad rows are visible.** 41 rows were set aside, each with its reason, so a client can see what was left out and why.

## 6. Interview questions you can expect

**Explain the project in 30 seconds.**
A developer cannot see how its asking price per m² compares with the competing listings, or who cut prices, because nobody keeps the old prices. I built a weekly Airflow pipeline that reads asking prices from six Egyptian listing sites in six areas, checks every row, keeps every price with its week in PostgreSQL in bronze, silver and gold layers, and compares each of our units with the median of its type in its area. Result: 5,619 competing listings compared in the first week, the widest gap in 6th of October at +7.4%, and every rejected row kept with its reason.

**Why bronze, silver and gold?**
Each layer has one job. Bronze keeps the pages as read, so I can re-parse them if a parser was wrong without reading the site again. Silver holds checked rows, one table per thing. Gold is the star schema the report reads. Any number in the report can be traced back to the page it came from.

**How do you know no row was lost?**
Every row parsed ends up in exactly one bucket: skipped, duplicate, saved or quarantined, and the counts must add up per site and area or the run fails. `silver.run_log` has the same rule as a database check. `build_gold` checks that gold holds silver's prices for the week less the quarantined ones. The notebook checks it again before it measures anything. An empty week, or page 1 of a search with no price (the canary), fails loudly.

**Why the median and not the average?**
Asking prices are skewed: a few very dear villas would pull an average up. The median is the middle listing, so one outlier cannot move it much. Every insight also states its n and leaves out groups under 10 listings.

**How do you handle duplicates?**
At three levels. The same listing read twice on one site in one run is counted once, by its site and id. A Bayut ad with the same id as a Dubizzle ad is left out of pooled numbers by a view. Twins across sites with different ids cannot be matched exactly, so I estimate them (about 1.7%) and say it is an estimate.

**How do you detect a price cut?**
`silver.price_observation` is append-only: one row per site, listing and run week, never updated. The view `gold.price_change` uses a window function (`lag`) to put each listing's price per m² next to its previous week's, and flags a cut when it fell.

**Why are two sites read by hand?**
Bayut Egypt and Aqarmap refuse plain programs. Rather than fight that in code, a visible browser opens them before the run, a person deals with any check, and the pages are saved to the same folder layout. `load_silver` treats them like any other site.

**Is a rerun safe?**
Yes. A finished week has a `_done` file and is skipped, a page already on disk is not read again, silver loads use `ON CONFLICT` so a row is never added twice, the week's quarantine is rebuilt from its pages, and `gold.build` deletes and rebuilds only that week's facts. A rerun gives the same rows.

**Why surrogate keys in gold but natural keys in silver?**
Silver keeps the data's own key, the site plus its listing id, because that is what identifies a listing. Gold gives each dimension a small integer key, upserted on the natural key so it stays stable between runs, because that is what Power BI joins on best. The listing id stays in the fact as a degenerate dimension.

**What about personal data?**
Contact fields (agent, broker, phone, email and similar) are removed from each site's JSON before anything is written. No warehouse table has a contact column. The raw pages stay on the machine that read them and are not committed.

## 7. Limits, in plain words

- There is one run week so far, so there are no price cuts or rises yet.
- Our 60 units are made up, so every gap number shows how the method works, not a real seller's position.
- The run reads a sample of each site: from 0.1% (Bayut Egypt) to 12.5% (realestate.eg) of what each says it has.
- These are asking prices, not the prices units actually sold for.
- Compound names are kept as each site writes them, so one compound spelt two ways counts as two.
- Only three sites name a developer, so the developer index rests on those three.
- The twin share is an estimate: different spellings hide some twins, and two different units can match by chance.
- The 10,000 to 400,000 EGP band is a rule. It can set aside a real but unusual listing, like the 497,821 per m² villa above.
- Skipped rows are kept as one count, without their reason.
- Nawy's price is the lowest price of the unit's payment plan, the price its unit page shows.
- Aqarmap marks 116 of its 721 rows (16.1%) as sponsored placements, so its numbers lean towards paid listings (cell 44).
- Bayut Egypt and Aqarmap need a person and a browser once a week.
