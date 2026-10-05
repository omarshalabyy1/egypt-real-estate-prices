# 8. Build checklist

Follow in order. A **Check** line is a number to verify before going on (all in `06-checks.md`); if
it is off, fix that step first.

## Prepare the warehouse

1. Start Docker Desktop. In the repo folder, if there is no `.env` yet, copy `.env.example` to `.env`
   and set `WAREHOUSE_PASSWORD` to a password of your choice. Then run `docker compose up -d --build`.
   The warehouse listens on `127.0.0.1:5451`.
2. Open Airflow at http://127.0.0.1:8101 and switch `egypt_real_estate_prices` on (the toggle left
   of its name). The DAG does not catch up on past weeks (the sites only show today's prices), so
   start the first weekly run yourself: click the DAG's name, then **Trigger** (the play button) and
   confirm.
3. **Check:** in Airflow the run of `egypt_real_estate_prices` is green. Then **C1** with the SQL in
   `06-checks.md`: one run week, with its asking prices in `gold.fact_listing_price`.
4. Page 3 (Weekly changes) needs a second run, the next Sunday's scheduled one. You can build the
   whole report after the first run; page 3 then shows no changes until the second run (see "The
   first week" in `04-pages.md`), and checks C14 to C18 wait for it.

## Power BI settings

5. Open Power BI Desktop, then **Blank report**.
6. **File > Options and settings > Options > Current file**:
   - **Data load:** untick **Auto date/time**.
   - **Report settings:** tick **Change default visual interaction from cross highlighting to cross
     filtering**.
7. **View > Themes > Browse for themes**, pick `powerbi/05-theme.json`.

## Power Query (`01-power-query.md`)

8. **Home > Transform data**. Create the `WarehouseServer` parameter (`127.0.0.1:5451`).
9. Create the queries in this order, pasting each one's M code: `Site`, `Area`, `Compound`,
   `Property Type`, `Week`, `Listing Price`, `Our Unit`, `Price Change`, `Area Benchmark`,
   `Area Site Benchmark`, `Unit Gap`, `Area Gap`. Every one reads schema `gold`. The first asks for
   credentials: Database, user `prices`, the password from `.env`.
10. **Home > Close & apply**.
11. Open **Table view** (second icon on the left) and click each table; the row count is at the
    bottom left.
    **Check C2:** Site <!--nb:table_rows_site-->6<!--/nb--> · Area <!--nb:table_rows_area-->6<!--/nb--> · Compound <!--nb:table_rows_compound-->1,336<!--/nb--> ·
    Property Type <!--nb:table_rows_property_type-->11<!--/nb--> · Week <!--nb:table_rows_week-->1<!--/nb--> · Listing Price <!--nb:table_rows_listing_price-->5,757<!--/nb--> ·
    Our Unit <!--nb:table_rows_our_unit-->60<!--/nb--> · Price Change <!--nb:table_rows_price_change-->0<!--/nb--> ·
    Area Benchmark <!--nb:table_rows_area_benchmark-->55<!--/nb--> · Area Site Benchmark <!--nb:table_rows_area_site_benchmark-->234<!--/nb--> · Unit Gap <!--nb:table_rows_unit_gap-->60<!--/nb--> ·
    Area Gap <!--nb:table_rows_area_gap-->6<!--/nb-->.

## Model (`02-model.md`)

12. **Model view**: delete any relationship Power BI made on its own (above all `Compound` to `Area`
    on `area_id`, and `Our Unit` to `Unit Gap` on `unit_code`), then create the 24 relationships in
    the table, each One to many, Single, Active. For `Area` to `Area Gap`, change the proposed One to
    one to One to many.
13. Mark `Week` as the date table (column `week_key`).
14. Hide the columns listed under "Hide columns".
15. Set `Area[lat]` to Data category **Latitude** and `Area[lon]` to **Longitude**, both
    **Don't summarize**.
16. Set the column formats.

## Measures (`03-measures.dax`)

17. **Home > Enter data**, name the table `_Measures`, **Load**.
18. Paste the 25 measures one by one into `_Measures`, setting each one's format string and display
    folder. Hide the empty column.
19. On a blank page, drop a card with `[Listings]` and one with `[Units Compared]` (Display units:
    None).
    **Check:** `[Listings]` is <!--nb:listings_compared-->5,757<!--/nb--> (C1 `prices_latest_week`) and `[Units Compared]`
    equals Our units minus the units with no comparison (C6). Delete both cards.

## Page 1: Market position (`04-pages.md`)

20. Rename the page to **Market position**. Build visuals 1 to 12 in order, with their position and
    size. For the map (#10), pick **Azure Maps** in the Visualizations pane.
21. **Check C3:** the six cards. Widest gap equals `gap_rank` 1 in `Area Gap`, and Listings cheaper
    than ours equals `report_share_cheaper_pct` in `analysis/numbers.json` (each listing of an
    area and type where we have units, against our median unit of that type and area); it is not the
    pooled `pct_listings_cheaper` of the views, which compares every unit with every listing.
22. **Check C4:** the bar chart's labels, top to bottom.
23. **Check C5:** <!--nb:map_bubbles-->6<!--/nb--> bubbles on the map, each on its area. If one is missing, stop
    and note which area.
24. **Check C6:** the units table's top rows and its row count.

## Page 2: Compounds and developers (`04-pages.md`)

25. Add a page, rename it **Compounds and developers**. Build visuals 1 to 11 in order.
26. **Check C9:** the five cards; Listings this week equals Competitor listings this week on page 1.
27. **Check C10:** the matrix's first rows.
28. **Check C11:** the three dearest developers at the top of the bar chart.
29. **Check C12:** the market band table's top rows.

## Page 3: Weekly changes (`04-pages.md`)

30. Add a page, rename it **Weekly changes**. Build visuals 1 to 12 in order.
31. **Check C14:** the five cards (after the first run only: four "(Blank)" change cards).
32. **Check C15:** the column chart's bars, one per run week that caught a change.

## Slicers and interactions

33. **View > Sync slicers**: set each slicer as in the table under "Sync the slicers" in
    `04-pages.md`.
34. Set every interaction as in `07-interactions.md`, page by page.
35. **Check C7:** on page 1, the Area slicer on New Cairo. Then clear it and click New Cairo in the
    bar chart: the cards show the same numbers. Click it again to clear.
36. **Check C8:** on page 1, the Site slicer on Dubizzle Egypt: the share cards and Widest gap move,
    Our units does not. Clear it.
37. **Check C13:** on page 2, the Area slicer on New Cairo (it is synced, so pages 1 and 3 show New
    Cairo too). Clear it.
38. **Check C18:** on page 3, the Area slicer on New Cairo. Clear it.
39. **Check C16:** pick the site and listing named in C16 in the Site and Listing slicers: its line
    and the dashed line for our units, cards unchanged. Clear both slicers.
40. **Check C17:** the table's top rows, sorted by Change % ascending, and its row count.

## Save and screenshots

41. **File > Save as** `powerbi/egypt-real-estate-prices.pbix`.
42. Export each page at 1280 × 720 (**File > Export > Export to PDF**, or a screenshot of the page)
    to `powerbi/screenshots/market-position.png` and
    `powerbi/screenshots/compounds-and-developers.png` (no slicer selected), and
    `powerbi/screenshots/weekly-changes.png` (the site and listing named in C16 picked, so the price
    history shows a line; the cards still show every listing). Take the weekly-changes image only
    after the second weekly run: before it, the page has no changes to show.
43. In the main `README.md`, add the three images to the "Power BI" section. Commit and push.
