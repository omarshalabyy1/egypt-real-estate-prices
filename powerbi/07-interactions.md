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

| Source (click) | Area #2 | Cards #3-8 | Map #9 | Area bar #10 | Units table #11 |
|---|---|---|---|---|---|
| Area slicer #2 | | Filter | Filter | Filter | Filter |
| Map #9 | None | Filter | | Filter | Filter |
| Area bar #10 | None | Filter | Filter | | Filter |
| Units table #11 | None | None | None | None | |

Why None on the slicer: a click on a chart should not shrink the slicer's list, so every area stays
pickable.

What a click changes:

- **A bubble in #9 or a bar in #10:** the cards, the other chart and the units table show that area
  only, the same numbers as the Area slicer on that area (check C7 for New Cairo).
- **A row in #11:** nothing. The table is for reading.

## Page 2: Compounds and developers

| Source (click) | Area #2 | Cards #3-7 | Compound matrix #8 | Developer bar #9 | Compound table #10 |
|---|---|---|---|---|---|
| Area slicer #2 | | Filter | Filter | Filter | Filter |
| Compound matrix #8 | None | None | | None | None |
| Developer bar #9 | None | None | Filter | | None |
| Compound table #10 | None | None | None | None | |

Why None from the charts to the cards: `Compounds` and `Developers` count `Compound Benchmark`,
which a click on `Listing` columns cannot reach, so filtering only some of the cards would show
numbers that do not belong together. The Area slicer filters every card the same way (check C11).

What a click changes:

- **A developer in #9:** the matrix shows only that developer's compounds and unit types, so its
  prices can be read compound by compound. The cards and the table keep the whole area.
- **A cell in #8 or a row in #10:** nothing. They are for reading.

## Page 3: Weekly changes

| Source (click) | Area #2 | Listing #3 | Cards #4-9 | Weekly columns #10 | Price history #11 | Changes table #12 |
|---|---|---|---|---|---|---|
| Area slicer #2 | | Filter | Filter | Filter | Filter | Filter |
| Listing slicer #3 | None | | None | None | Filter | Filter |
| Weekly columns #10 | None | None | Filter | | None | Filter |
| Price history #11 | None | None | None | None | | None |
| Changes table #12 | None | None | None | None | None | |

What a click changes:

- **A listing in #3:** only the price history and the table follow it; the cards and the weekly
  columns keep counting every listing in the area, so picking a listing to look at never changes the
  totals (check C15).
- **A week in #10:** the change cards (#4 to #7) and the table show that run's changes. Listings
  seen this week (#8) and New this week (#9) do not move: they count listings, which a week of
  `Price Change` cannot filter. The price history keeps its full timeline, so the week can be seen
  in context.
- **A point in #11 or a row in #12:** nothing. The chart and the table are for reading.

## Not used

- Drill-through pages: none. The Area slicer is synced across the three pages, so an area picked on
  page 1 is already picked on page 2.
- Bookmarks and buttons: none.
- Tooltip pages: none. The map (page 1 #9), the area bar (page 1 #10) and the developer bar (page 2
  #9) use the default tooltip with the measures added to their Tooltips well.
- Filters pane: no visual-, page- or report-level filters. "The latest run" is in the views and the
  measures.
