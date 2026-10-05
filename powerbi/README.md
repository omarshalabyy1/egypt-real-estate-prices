# Power BI: build the report step by step

The report reads the gold layer of the local warehouse, a Kimball star, and answers three
questions, for every listing site together or one site at a time:

1. **Market position:** where our units sit against the market per m², area by area: what share
   asks more than the median of their type in their area, and how many listings ask less than ours.
2. **Compounds and developers:** which compounds and developers are dearest and cheapest per m² in
   each area, and the price band of each area and unit type.
3. **Weekly changes:** what changed week by week, which weekly run caught it, who cut prices, and one
   listing's price per m² over time against ours.

Everything below is copy and paste. **Start with [`08-build-checklist.md`](08-build-checklist.md)**:
43 numbered steps from starting the warehouse to the last screenshot, with a check number at each
point. It points to the other files:

| File | What it holds |
|---|---|
| [`01-power-query.md`](01-power-query.md) | The `WarehouseServer` parameter and twelve queries (M code), one per gold table and view |
| [`02-model.md`](02-model.md) | Tables with grain and keys, the date table, 24 relationships, hidden columns, data category, formats, display folders, with the reason for each |
| [`03-measures.dax`](03-measures.dax) | The `_Measures` table and 25 measures, grouped by page |
| [`04-pages.md`](04-pages.md) | Three pages, 35 visuals: type, fields, position and size, settings, slicer sync |
| [`05-theme.json`](05-theme.json) | The theme: **View > Themes > Browse for themes**, pick this file |
| [`06-checks.md`](06-checks.md) | Checks C1 to C18: the numbers every card and chart must show, with the gold SQL behind each |
| [`07-interactions.md`](07-interactions.md) | Which visual filters which, per page |
| [`08-build-checklist.md`](08-build-checklist.md) | The build, step by step |

The model: five dimensions (`Site`, `Area`, `Compound`, `Property Type`, `Week`), two facts
(`Listing Price`, one row per site, listing and run week; `Our Unit`, one row per unit of ours) and
the five gold views. Every measure reads the facts, so the Site slicer on each page reaches every
number; the views are pooled over sites and serve as the cross-check.

The theme is `05-theme.json`, written by `python theme.py` from `report.title` and `report.colours` in
`config/client.yaml`; the demo's colours are the ones every portfolio project report shares, so the
reports look like one family. The pages name colours by theme slot
(Theme colour 1 is the blue), never by hex code. The site's font, Geist, is not in Power BI's font
list, so the theme uses Segoe UI.

The warehouse must be running (`docker compose up -d` in the repo root, PostgreSQL on
`127.0.0.1:5451`) while you build or refresh the report. After each Sunday's run of
`egypt_real_estate_prices`, press **Refresh** in Power BI: that is the one click. The Weekly changes
page stays empty until the second weekly run: one run has no earlier price to compare with.

When the report is built:

- Save it as `powerbi/egypt-real-estate-prices.pbix`.
- Export one image per page to `powerbi/screenshots/market-position.png`,
  `powerbi/screenshots/compounds-and-developers.png` and `powerbi/screenshots/weekly-changes.png`.
- Add the three images to the "Power BI" section of the main README.
