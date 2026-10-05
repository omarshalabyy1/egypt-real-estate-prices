# 4. Pages and visuals

Canvas: 16:9, 1280 × 720 (the default). Set each visual's position and size in **Format > General >
Properties**. `x, y, w, h` are in pixels from the top-left corner. Apply the theme (`05-theme.json`)
first so colours and fonts are already right. Colours are named by theme slot: Theme colour 1 is the
blue, 2 the navy, 4 the slate grey, 6 the pale blue.

Rename the pages (double-click the tab) to **Market position**, **Compounds and developers** and
**Weekly changes**.

Number formats come from each measure's format string (`03-measures.dax`) and each column's format
(`02-model.md`), so no visual needs its own format. On every card set **Format > Visual > Callout
value > Display units: None**, so the card shows the full number as in `06-checks.md`. Visuals are
listed in build order; the `#` is used in `07-interactions.md`.

## Page 1: Market position

Where our units sit against the market per m², area by area.

| # | Visual | x, y, w, h | Fields | Settings |
|---|---|---|---|---|
| 1 | Text box | 24, 16, 900, 52 | "Where our units sit against the market" | Font 20, bold |
| 2 | Slicer | 1108, 12, 148, 56 | Field: `Area[name]` | Slicer settings > Style: Dropdown. Selection: multi-select with Ctrl, "Select all" on. Header text "Area" |
| 3 | Card | 24, 84, 198, 96 | `[Our Units]` | Category label on, renamed on the visual to "Our units" |
| 4 | Card | 230, 84, 198, 96 | `[Units Above Market]` | Category label "Above market" |
| 5 | Card | 436, 84, 198, 96 | `[Share Above Market]` | Category label "Share above market" |
| 6 | Card | 642, 84, 198, 96 | `[Average Gap]` | Category label "Average gap (above 0: we ask more)" |
| 7 | Card | 848, 84, 198, 96 | `[Widest Gap Area]` | Category label "Furthest from market"; callout value colour Theme colour 1 |
| 8 | Card | 1054, 84, 198, 96 | `[Listings Compared]` | Category label "Competitor listings this week" |
| 9 | Azure Maps | 24, 196, 420, 508 | Location: `Area[Map Name]`; Size: `[Listings Compared]`; Tooltips: `[Median Price Per m²]`, `[Our Price Per m²]`, `[Our Units]`, `[Average Gap]` | Title "Listings and our gap, by area". Map settings > Style: Road; Auto zoom on. Bubble layer > Size: Min 10, Max 40. Bubble layer > Colors > **fx** (conditional formatting): Format style Gradient, based on field `[Average Gap]`, tick "Add a middle color"; Minimum: Number -0.2, Theme colour 1; Middle: Number 0, Theme colour 6; Maximum: Number 0.2, Theme colour 4. Legend off |
| 10 | Clustered bar chart | 460, 196, 796, 240 | Y-axis: `Area[name]`; X-axis: `[Average Gap]`; Tooltips: `[Our Units]`, `[Listings Compared]`, `[Median Price Per m²]`, `[Our Price Per m²]` | Title "Average gap of our units, by area". Sort by Average Gap, descending. Data labels on. Bars > Color > **fx**: Format style Rules, based on field `[Average Gap]`; If value > 0 then Theme colour 4; If value < 0 then Theme colour 1 |
| 11 | Table | 460, 452, 796, 252 | `Unit Gap[unit_code]`, `Area[name]`, `Unit Gap[unit_type]`, `Unit Gap[size_m2]`, `Unit Gap[price_per_m2]`, `Unit Gap[median_price_per_m2]`, `Unit Gap[gap_pct]`, `Unit Gap[listings_compared]`, `Unit Gap[Position]` | Title "Our units against the area median". In the field well, set every numeric column to **Don't summarize** (arrow next to the field). Rename on the visual: unit_code "Unit", name "Area", unit_type "Type", size_m2 "m²", price_per_m2 "Ours per m²", median_price_per_m2 "Market median per m²", gap_pct "Gap %", listings_compared "Listings compared", Position "Position". Sort by Gap %, descending. Conditional formatting > Font color on **Position**: Format style Rules, based on field `Unit Gap[gap_pct]` (Summarization: Minimum); If value > 0 then Theme colour 4; If value < 0 then Theme colour 1. The same rule on **Gap %**. Totals off |

Why #11 is a Table and not a matrix: a matrix must aggregate its values, while a table shows each
unit's own numbers with **Don't summarize**, exactly as `unit_gap` holds them; there is one row per
unit, so there is nothing to subtotal.

On the map and the bar, blue is where our units ask less per m² than the market median of their
type, the darker the cheaper; grey is where we ask more. A unit with "No comparison" in #11 had no
listing of its type in its area in the latest run, so it has no colour and is left out of the gap
cards.

The map geocodes `Area[Map Name]` (Data category Place, `02-model.md`). If a bubble lands in the
wrong place, check C5 in `06-checks.md` says what to do.

## Page 2: Compounds and developers

Which compounds and developers are dearest and cheapest per m² in each area.

| # | Visual | x, y, w, h | Fields | Settings |
|---|---|---|---|---|
| 1 | Text box | 24, 16, 900, 52 | "Compounds and developers, dearest to cheapest" | Font 20, bold |
| 2 | Slicer | 1108, 12, 148, 56 | Field: `Area[name]` | Same as page 1 #2 (it is synced, see below) |
| 3 | Card | 24, 84, 240, 96 | `[Listings]` | Category label "Listings this week" |
| 4 | Card | 272, 84, 240, 96 | `[Compounds Covered]` | Category label "Compounds" |
| 5 | Card | 520, 84, 240, 96 | `[Developers Covered]` | Category label "Developers" |
| 6 | Card | 768, 84, 240, 96 | `[Cheapest Compound]` | Category label "Cheapest compound per m²"; callout value font size 12, Theme colour 1 |
| 7 | Card | 1016, 84, 240, 96 | `[Dearest Compound]` | Category label "Dearest compound per m²"; callout value font size 12, Theme colour 4 |
| 8 | Matrix | 24, 196, 820, 300 | Rows: `Listing[compound]`; Columns: `Listing[unit_type]`; Values: `[Median Price Per m²]` | Title "Median asking price per m², by compound and unit type". Row and column subtotals off. Sort by `compound`, ascending. Conditional formatting > Background color on `Median Price Per m²`: Format style Gradient; Minimum: Lowest value, White; Maximum: Highest value, Theme colour 1. Search on the row header (matrix menu `...` > Search) |
| 9 | Clustered bar chart | 860, 196, 396, 508 | Y-axis: `Listing[developer]`; X-axis: `[Median Price Per m²]`; Tooltips: `[Listings]` | Title "Median per m², by developer". Sort by Median Price Per m², descending. Data labels on. Bars Theme colour 1 |
| 10 | Table | 24, 512, 820, 192 | `Area[name]`, `Compound Benchmark[compound]`, `Compound Benchmark[developer]`, `Compound Benchmark[listings]`, `Compound Benchmark[median_price_per_m2]` | Title "Every compound this week". Set `listings` and `median_price_per_m2` to **Don't summarize**. Rename on the visual: name "Area", compound "Compound", developer "Developer", listings "Listings", median_price_per_m2 "Median per m²". Sort by Median per m², descending. Totals off |

The matrix shows a cell only where a compound had a listing of that type in the latest run, so most
cells are empty. A compound or developer the site did not name shows as "(Blank)" in #8, #9 and #10;
the cards leave it out. A compound with one listing has that listing's price per m² as its median:
hover the bar or read the Listings column in #10 before quoting it.

## Page 3: Weekly changes

What changed week by week and who cut prices.

**The first week:** this page stays empty until the second weekly run. One run has no earlier price
to compare with, so `Price Change` has no rows, the change cards show "(Blank)", the column chart
and the table are empty, and `New Listings This Week` equals `Listings` (every listing is new).

| # | Visual | x, y, w, h | Fields | Settings |
|---|---|---|---|---|
| 1 | Text box | 24, 16, 760, 52 | "What changed this week, and who cut prices" | Font 20, bold |
| 2 | Slicer | 952, 12, 148, 56 | Field: `Area[name]` | Same as page 1 #2 (synced) |
| 3 | Slicer | 1108, 12, 148, 56 | Field: `Listing[listing_id]` | Style: Dropdown. Selection: **Single select** on. Search on (slicer menu `...` > Search). Header text "Listing (history)" |
| 4 | Card | 24, 84, 198, 96 | `[Price Changes]` | Category label "Price changes" |
| 5 | Card | 230, 84, 198, 96 | `[Price Cuts]` | Category label "Cuts"; callout value colour Theme colour 1 |
| 6 | Card | 436, 84, 198, 96 | `[Price Rises]` | Category label "Rises" |
| 7 | Card | 642, 84, 198, 96 | `[Average Change]` | Category label "Average change" |
| 8 | Card | 848, 84, 198, 96 | `[Listings]` | Category label "Listings seen this week" |
| 9 | Card | 1054, 84, 198, 96 | `[New Listings This Week]` | Category label "New this week" |
| 10 | Stacked column chart | 24, 196, 620, 250 | X-axis: `Price Change[caught_week]`; Y-axis: `[Price Cuts]`, `[Price Rises]` | Title "Changes caught by each weekly run". X-axis type: Categorical, sorted by `caught_week` ascending. Colours: Price Cuts Theme colour 1, Price Rises Theme colour 4. Legend: top. Data labels on |
| 11 | Line chart | 660, 196, 596, 250 | X-axis: `Date[Date]`; Y-axis: `[Competitor Price Per m²]` | Title "Price per m² of the picked listing". X-axis type: Continuous. Markers on. Line Theme colour 1. Analytics pane > Y-axis constant line > Add > Value: fx > Field value `[Our Same-Type Price Per m²]`; line colour Theme colour 2, style Dashed; Data label on, Text "Name", Name "Our units, same type and area" |
| 12 | Table | 24, 462, 1232, 242 | `Listing[listing_id]`, `Area[name]`, `Listing[compound]`, `Listing[developer]`, `Listing[unit_type]`, `Price Change[observed_on]`, `Price Change[old_price]`, `Price Change[new_price]`, `Price Change[change_pct]`, `Price Change[Direction]`, `Price Change[caught_week]` | Title "Every change". Set `listing_id`, `old_price`, `new_price` and `change_pct` to **Don't summarize**. Rename on the visual: listing_id "Listing", name "Area", compound "Compound", developer "Developer", unit_type "Type", observed_on "Date", old_price "Was (EGP)", new_price "Now (EGP)", change_pct "Change %", Direction "Direction", caught_week "Caught in week". Sort by Change %, ascending (the deepest cuts first). Conditional formatting > Font color on Change %: Format style Rules; If value < 0 then Theme colour 1; If value > 0 then Theme colour 4. Totals off |

The line chart stays empty until a listing is picked in slicer #3 (`Competitor Price Per m²` returns
blank for more than one listing). To pick one, read its number in the table (#12) and type it in the
slicer's search box. The dashed line is missing when we have no unit of the listing's type in its
area. The line has one point per weekly run, so it needs two runs before it is a line.

## Sync the slicers

**View > Sync slicers**. For each slicer, tick **Sync** and **Visible** on the pages below:

| Slicer | Market position | Compounds and developers | Weekly changes | Why |
|---|---|---|---|---|
| Area (`Area[name]`) | yes | yes | yes | One choice of area for all three pages |
| Listing (`Listing[listing_id]`) | no | no | yes | Page 3 only: it drives the price history |

## Not used

No drill-through, bookmarks, buttons or tooltip pages, and no filters in the Filters pane (visual,
page or report level). "The latest run" is applied in the views and in the measures, where a filter
cannot be cleared by accident. Three pages, two slicers and the interactions in
`07-interactions.md` answer the three questions.
