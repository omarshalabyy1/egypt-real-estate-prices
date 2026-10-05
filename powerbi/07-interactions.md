# 7. Interactions

## Report setting (once)

**File > Options and settings > Options > Current file > Report settings**: tick **Change default
visual interaction from cross highlighting to cross filtering**.

Why: clicking a bar or a bubble then filters the other visuals to it instead of greying out part of
each bar, so every card shows the selected area's or week's real numbers.

## How to set a cell

Select the source visual (the one you click), then **Format > Edit interactions**. Each other visual
shows icons in its top-right corner: **Filter** (funnel) or **None** (circle with a line). Click the
one the table below says. Click **Edit interactions** again to finish.

Numbers are the visual `#` in `04-pages.md`. Text boxes (#1) take no part. Cards are never a source:
clicking a card selects nothing.

## Page 1: Market position

| Source (click) | Site #2 | Area #3 | Cards #4-9 | Map #10 | Area bar #11 | Units table #12 |
|---|---|---|---|---|---|---|
| Site slicer #2 | | None | Filter | Filter | Filter | Filter |
| Area slicer #3 | None | | Filter | Filter | Filter | Filter |
| Map #10 | None | None | Filter | | Filter | Filter |
| Area bar #11 | None | None | Filter | Filter | | Filter |
| Units table #12 | None | None | None | None | None | |

Why None between the slicers and from the charts to the slicers: a click should not shrink a
slicer's list, so every site and every area stays pickable.

What a click changes:

- **A site in #2:** every card and chart recomputes against that site's listings only; Our units
  (#4) does not move, because our units are not on a site.
- **A bubble in #10 or a bar in #11:** the cards, the other chart and the units table show that
  area only, the same numbers as the Area slicer on that area (check C7 for New Cairo).
- **A row in #12:** nothing. The table is for reading.

## Page 2: Compounds and developers

| Source (click) | Site #2 | Area #3 | Cards #4-8 | Compound matrix #9 | Developer bar #10 | Market band #11 |
|---|---|---|---|---|---|---|
| Site slicer #2 | | None | Filter | Filter | Filter | Filter |
| Area slicer #3 | None | | Filter | Filter | Filter | Filter |
| Compound matrix #9 | None | None | None | | None | None |
| Developer bar #10 | None | None | Filter | Filter | | Filter |
| Market band #11 | None | None | None | None | None | |

What a click changes:

- **A developer in #10:** the cards, the matrix and the market band show that developer's listings
  only, so its compounds and prices can be read compound by compound. Every card reads
  `Listing Price` through `Compound`, so all five move together.
- **A cell in #9 or a row in #11:** nothing. They are for reading.

## Page 3: Weekly changes

| Source (click) | Site #2 | Area #3 | Listing #4 | Cards #5-8 | Card #9 | Weekly columns #10 | Price history #11 | Changes table #12 |
|---|---|---|---|---|---|---|---|---|
| Site slicer #2 | | None | Filter | Filter | Filter | Filter | Filter | Filter |
| Area slicer #3 | None | | Filter | Filter | Filter | Filter | Filter | Filter |
| Listing slicer #4 | None | None | | None | None | None | Filter | None |
| Weekly columns #10 | None | None | None | Filter | None | | None | Filter |
| Price history #11 | None | None | None | None | None | None | | None |
| Changes table #12 | None | None | None | None | None | None | None | |

Why the Site and Area slicers filter the Listing slicer: its list then holds only the ids on the
picked site and area, so an id is easier to find.

What a click changes:

- **A listing in #4:** only the price history follows it. The cards, the weekly columns and the
  table keep counting every listing on the sites and areas picked, so picking a listing to look at
  never changes the totals (check C15). The slicer filters `Listing Price` only, and `Price Change`
  is a separate table, so None on the table is also what the model would do.
- **A week in #10:** the change cards (#5 to #8) and the table show that run's changes. Listings
  seen this week (#9) does not move: it always counts the latest run week. The price history keeps
  its full timeline, so the week can be seen in context.
- **A point in #11 or a row in #12:** nothing. The chart and the table are for reading.

## Not used

- Drill-through pages: none. The Site and Area slicers are synced across the three pages, so an
  area picked on page 1 is already picked on page 2.
- Bookmarks and buttons: none.
- Tooltip pages: none. The map (page 1 #10), the area bar (page 1 #11) and the developer bar (page
  2 #10) use the default tooltip with the measures added to their Tooltips well.
- Filters pane: no visual-, page- or report-level filters. "The latest run week" is in the measures.
