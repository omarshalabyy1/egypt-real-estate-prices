# Power BI: build the report step by step

The report reads the local warehouse and answers three questions:

1. **Market position:** where our units sit against the market per m², area by area: how many ask
   more than the median of their type in their area, and by how much.
2. **Compounds and developers:** which compounds and developers are dearest and cheapest per m² in
   each area.
3. **Weekly changes:** what changed week by week, which weekly run caught it, who cut prices, and one
   listing's price per m² over time against ours.

Everything below is copy and paste. **Start with [`08-build-checklist.md`](08-build-checklist.md)**:
42 numbered steps from starting the warehouse to the last screenshot, with a check number at each
point. It points to the other files:

| File | What it holds |
|---|---|
| [`01-power-query.md`](01-power-query.md) | The `WarehouseServer` parameter and nine queries (M code) |
| [`02-model.md`](02-model.md) | Tables, date table, nine relationships, hidden columns, sort, data category, formats, display folders, with the reason for each |
| [`03-measures.dax`](03-measures.dax) | The `_Measures` table and 20 measures, grouped by page |
| [`04-pages.md`](04-pages.md) | Three pages, 33 visuals: type, fields, position and size, settings, slicer sync |
| [`05-theme.json`](05-theme.json) | The theme: **View > Themes > Browse for themes**, pick this file |
| [`06-checks.md`](06-checks.md) | Checks C1 to C16: the numbers every card and chart must show, with the SQL behind each |
| [`07-interactions.md`](07-interactions.md) | Which visual filters which, per page |
| [`08-build-checklist.md`](08-build-checklist.md) | The build, step by step |

The theme is the one every portfolio project report shares (navy `#0E1630`, blue `#2563EB`, soft
grey page `#F4F6FB`), so the reports look like one family. The pages name colours by theme slot
(Theme colour 1 is the blue), never by hex code. The site's font, Geist, is not in Power BI's font
list, so the theme uses Segoe UI.

The warehouse must be running (`docker compose up -d` in the repo root) while you build or refresh
the report. After each Sunday's run, press **Refresh** in Power BI: that is the one click. The
Weekly changes page stays empty until the second weekly run: one run has no earlier price to
compare with.

When the report is built:

- Save it as `powerbi/egypt-real-estate-prices.pbix`.
- Export one image per page to `powerbi/screenshots/market-position.png`,
  `powerbi/screenshots/compounds-and-developers.png` and `powerbi/screenshots/weekly-changes.png`.
- Add the three images to the "Power BI" section of the main README.
