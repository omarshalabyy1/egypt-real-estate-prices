# 8. Build checklist

Follow in order. A **Check** line is a number to verify before going on (all in `06-checks.md`); if
it is off, fix that step first.

## Prepare the warehouse

1. Start Docker Desktop. In the repo folder, if there is no `.env` yet, copy `.env.example` to `.env`
   and set `WAREHOUSE_PASSWORD` to a password of your choice. Then run `docker compose up -d --build`.
2. Open Airflow at http://127.0.0.1:8101 and switch `egypt_real_estate_prices` on (the toggle left
   of its name). The DAG does not catch up on past weeks (the site only shows today's prices), so
   start the first run yourself: click the DAG's name, then **Trigger** (the play button) and
   confirm. A run reads up to 8 index pages and up to 150 unit pages for each of the six areas, 2.5
   seconds apart (`MAX_PAGES_PER_AREA`, `CARDS_PER_AREA` and `DELAY` in `tracker.py`), so it takes
   up to about 40 minutes.
3. **Check:** in Airflow the run of `egypt_real_estate_prices` is green (`load_reference`, `collect`
   and `report`). Then **C1** with the SQL in `06-checks.md`.
4. Page 3 (Weekly changes) needs a second run, the next Sunday's scheduled one. You can build the
   whole report after the first run; page 3 then shows no changes until the second run (see "The
   first week" in `04-pages.md`), and checks C12 to C16 wait for it.

## Power BI settings

5. Open Power BI Desktop, then **Blank report**.
6. **File > Options and settings > Options > Current file**:
   - **Data load:** untick **Auto date/time**.
   - **Report settings:** tick **Change default visual interaction from cross highlighting to cross
     filtering**.
7. **View > Themes > Browse for themes**, pick `powerbi/05-theme.json`.

## Power Query (`01-power-query.md`)

8. **Home > Transform data**. Create the `WarehouseServer` parameter (`localhost:5451`).
9. Create the queries in this order, pasting each one's M code: `Area`, `Our Unit`, `Listing`,
   `Price Observation`, `Area Benchmark`, `Compound Benchmark`, `Unit Gap`, `Price Change`, `Date`.
   The first asks for credentials: Database, user `prices`, the password from `.env`.
10. **Home > Close & apply**.
11. Open **Table view** (second icon on the left) and click each table; the row count is at the
    bottom left.
    **Check C2:** Area [from the notebook] · Our Unit [from the notebook] · Listing
    [from the notebook] · Date [from the notebook] · Price Observation [from the notebook] · Area
    Benchmark [from the notebook] · Compound Benchmark [from the notebook] · Unit Gap
    [from the notebook] · Price Change [from the notebook].

## Model (`02-model.md`)

12. **Model view**: delete any relationship Power BI made on its own (above all `Our Unit` to
    `Unit Gap` on `unit_code`), then create the nine relationships in the table, each One to many,
    Single, Active.
13. Mark `Date` as the date table (column `Date`).
14. Hide the columns listed under "Hide columns".
15. Sort `Date[Month]` by `Month Number`.
16. Set `Area[Map Name]` to Data category **Place**.
17. Set the column formats.

## Measures (`03-measures.dax`)

18. **Home > Enter data**, name the table `_Measures`, **Load**.
19. Paste the 20 measures one by one into `_Measures`, setting each one's format string and display
    folder. Hide the empty column.
20. On a blank page, drop a card with `[Listings Compared]` and one with `[Listings]` (Display
    units: None).
    **Check:** both show the same number, [from the notebook] (C3 and C8). Delete both cards.

## Page 1: Market position (`04-pages.md`)

21. Rename the page to **Market position**. Build visuals 1 to 11 in order, with their position and
    size. For the map (#9), pick **Azure Maps** in the Visualizations pane.
22. **Check C3:** the six cards.
23. **Check C4:** the bar chart's labels, top to bottom.
24. **Check C5:** [from the notebook] bubbles on the map, each on its area. If one is missing or
    outside Egypt, stop and note which area.
25. **Check C6:** the units table's top rows and its row count.

## Page 2: Compounds and developers (`04-pages.md`)

26. Add a page, rename it **Compounds and developers**. Build visuals 1 to 10 in order.
27. **Check C8:** the five cards; Listings this week equals Competitor listings this week on page 1.
28. **Check C9:** the matrix's first rows.
29. **Check C10:** the three dearest developers at the top of the bar chart.

## Page 3: Weekly changes (`04-pages.md`)

30. Add a page, rename it **Weekly changes**. Build visuals 1 to 12 in order.
31. **Check C12:** the six cards (after the first run only: four "(Blank)" change cards, and New this
    week equal to Listings seen this week).
32. **Check C13:** the column chart's bars, one per weekly run that caught a change.

## Slicers and interactions

33. **View > Sync slicers**: set each slicer as in the table under "Sync the slicers" in
    `04-pages.md`.
34. Set every interaction as in `07-interactions.md`, page by page.
35. **Check C7:** on page 1, the Area slicer on New Cairo. Then clear it and click New Cairo in the
    bar chart: the cards show the same numbers. Click it again to clear.
36. **Check C11:** on page 2, the Area slicer on New Cairo (it is synced, so pages 1 and 3 show New
    Cairo too). Clear it.
37. **Check C14:** on page 3, the Area slicer on New Cairo. Clear it.
38. **Check C15:** pick the listing named in C15 in the Listing slicer: its line and the dashed line
    for our units, cards unchanged. Clear the slicer.
39. **Check C16:** the table's top rows, sorted by Change % ascending, and its row count.

## Save and screenshots

40. **File > Save as** `powerbi/egypt-real-estate-prices.pbix`.
41. Export each page at 1280 × 720 (**File > Export > Export to PDF**, or a screenshot of the page)
    to `powerbi/screenshots/market-position.png` and
    `powerbi/screenshots/compounds-and-developers.png` (no slicer selected), and
    `powerbi/screenshots/weekly-changes.png` (the listing named in C15 picked in the Listing slicer,
    so the price history shows a line; the cards still show every listing). Take the weekly-changes
    image only after the second weekly run: before it, the page has no changes to show.
42. In the main `README.md`, add the three images to the "Power BI" section. Commit and push.
