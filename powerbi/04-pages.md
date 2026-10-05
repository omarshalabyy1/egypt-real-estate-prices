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

Every page has a **Site** slicer, synced across the three pages. It reaches every card and chart:
the measures read `Listing Price`, `Our Unit` and `Price Change`, never the pooled views. With one
site picked, our units are compared with that site's listings only.

## Page 1: Market position

Where our units sit against the market per m², area by area.

| # | Visual | x, y, w, h | Fields | Settings |
|---|---|---|---|---|
| 1 | Text box | 24, 16, 760, 52 | "Where our units sit against the market" | Font 20, bold |
| 2 | Slicer | 952, 12, 148, 56 | Field: `Site[name]` | Slicer settings > Style: Dropdown. Selection: multi-select with Ctrl, "Select all" on. Header text "Site" |
| 3 | Slicer | 1108, 12, 148, 56 | Field: `Area[name]` | Style: Dropdown. Multi-select with Ctrl, "Select all" on. Header text "Area" |
| 4 | Card | 24, 84, 198, 96 | `[Our Units]` | Category label on, renamed on the visual to "Our units" |
| 5 | Card | 230, 84, 198, 96 | `[Share Above Market]` | Category label "Above market"; callout value colour Theme colour 4 |
| 6 | Card | 436, 84, 198, 96 | `[Share Below Market]` | Category label "At or below market"; callout value colour Theme colour 1 |
| 7 | Card | 642, 84, 198, 96 | `[Share Of Listings Cheaper Than Ours]` | Category label "Listings cheaper than ours" |
| 8 | Card | 848, 84, 198, 96 | `[Widest Gap Area]` | Category label "Widest gap"; callout value font size 20, Theme colour 1 |
| 9 | Card | 1054, 84, 198, 96 | `[Listings]` | Category label "Competitor listings this week" |
| 10 | Azure Maps | 24, 196, 420, 508 | Latitude: `Area[lat]`; Longitude: `Area[lon]`; Size: `[Listings]`; Tooltips: `Area[name]` (First), `[Median Price Per m²]`, `[Our Price Per m²]`, `[Our Units]`, `[Median Gap]` | Title "Listings and our gap, by area". Map settings > Style: Road; Auto zoom on. Bubble layer > Size: Min 10, Max 40. Bubble layer > Colors > **fx** (conditional formatting): Format style Gradient, based on field `[Median Gap]`, tick "Add a middle color"; Minimum: Number -0.1, Theme colour 1; Middle: Number 0, Theme colour 6; Maximum: Number 0.1, Theme colour 4. Legend off |
| 11 | Clustered bar chart | 460, 196, 796, 240 | Y-axis: `Area[name]`; X-axis: `[Median Gap]`; Tooltips: `[Units Compared]`, `[Listings Compared]`, `[Median Price Per m²]`, `[Our Price Per m²]` | Title "Median gap of our units, by area". Sort by Median Gap, descending. Data labels on. Bars > Color > **fx**: Format style Rules, based on field `[Median Gap]`; If value > 0 then Theme colour 4; If value < 0 then Theme colour 1 |
| 12 | Table | 460, 452, 796, 252 | `Our Unit[unit_code]`, `Area[name]`, `Property Type[unit_type]`, `Compound[compound]`, `Our Unit[price_per_m2]`, `[Market Median Per m²]`, `[Median Gap]`, `[Listings Compared]`, `[Share Of Listings Cheaper Than Ours]` | Title "Our units against the market median". Set `price_per_m2` to **Don't summarize** (arrow next to the field). Rename on the visual: unit_code "Unit", name "Area", unit_type "Type", compound "Compound", price_per_m2 "Ours per m²", Market Median Per m² "Market median per m²", Median Gap "Gap", Listings Compared "Listings compared", Share Of Listings Cheaper Than Ours "Cheaper than ours". Sort by Gap, descending. Conditional formatting > Font color on **Gap**: Format style Rules, based on field `[Median Gap]`; If value > 0 then Theme colour 4; If value < 0 then Theme colour 1. Totals off |

Why the map reads `lat` and `lon`: the warehouse stores each area's coordinates in `dim_area`, so
every bubble lands on its area with no geocoding and no wrong guess between two places of the same
name.

Why #12 is a Table and not a matrix: there is one row per unit, so there is nothing to subtotal,
and each measure on a row is that unit's own number (its market median, its gap).

On the map and the bar, blue is where our units ask less per m² than the market median of their
type, the darker the cheaper; grey is where we ask more. A unit whose Gap is blank in #12 has no
listing of its type in its area on the sites picked, so it is left out of the share cards.

## Page 2: Compounds and developers

Which compounds and developers are dearest and cheapest per m² in each area.

| # | Visual | x, y, w, h | Fields | Settings |
|---|---|---|---|---|
| 1 | Text box | 24, 16, 760, 52 | "Compounds and developers, dearest to cheapest" | Font 20, bold |
| 2 | Slicer | 952, 12, 148, 56 | Field: `Site[name]` | Same as page 1 #2 (it is synced, see below) |
| 3 | Slicer | 1108, 12, 148, 56 | Field: `Area[name]` | Same as page 1 #3 (synced) |
| 4 | Card | 24, 84, 240, 96 | `[Listings]` | Category label "Listings this week" |
| 5 | Card | 272, 84, 240, 96 | `[Compounds Covered]` | Category label "Compounds" |
| 6 | Card | 520, 84, 240, 96 | `[Developers Covered]` | Category label "Developers" |
| 7 | Card | 768, 84, 240, 96 | `[Cheapest Compound]` | Category label "Cheapest compound per m²"; callout value font size 12, Theme colour 1 |
| 8 | Card | 1016, 84, 240, 96 | `[Dearest Compound]` | Category label "Dearest compound per m²"; callout value font size 12, Theme colour 4 |
| 9 | Matrix | 24, 196, 820, 300 | Rows: `Compound[compound]`; Columns: `Property Type[unit_type]`; Values: `[Median Price Per m²]` | Title "Median asking price per m², by compound and unit type". Row and column subtotals off. Sort by `compound`, ascending. Conditional formatting > Background color on `Median Price Per m²`: Format style Gradient; Minimum: Lowest value, Theme colour 6; Maximum: Highest value, Theme colour 1. Search on the row header (matrix menu `...` > Search) |
| 10 | Clustered bar chart | 860, 196, 396, 508 | Y-axis: `Compound[developer]`; X-axis: `[Median Price Per m²]`; Tooltips: `[Listings]` | Title "Median per m², by developer". Sort by Median Price Per m², descending. Data labels on. Bars Theme colour 1 |
| 11 | Table | 24, 512, 820, 192 | `Area[name]`, `Property Type[unit_type]`, `[Listings]`, `[P25 Price Per m²]`, `[Median Price Per m²]`, `[P75 Price Per m²]` | Title "Market band per m², by area and unit type". Rename on the visual: name "Area", unit_type "Type", Listings "Listings", P25 Price Per m² "Lower quarter", Median Price Per m² "Median", P75 Price Per m² "Upper quarter". Sort by Listings, descending. Totals off |

The matrix shows a cell only where a compound had a listing of that type in the latest run week, so
most cells are empty. A compound or developer the site did not name shows as "Unknown" in #9, #10
and #11; the cards leave it out. A compound with one listing has that listing's price per m² as its
median: hover the bar or read the Listings column before quoting it. #11 is the same band as the
`area_site_benchmark` view, recomputed so the Site slicer reaches it; with no site picked it equals
`area_benchmark`.

## Page 3: Weekly changes

What changed week by week and who cut prices.

**The first week:** this page stays empty until the second weekly run. One run has no earlier price
to compare with, so `Price Change` has no rows, the change cards show "(Blank)", the column chart
and the table are empty, and the price history has one point.

| # | Visual | x, y, w, h | Fields | Settings |
|---|---|---|---|---|
| 1 | Text box | 24, 16, 600, 52 | "What changed this week, and who cut prices" | Font 20, bold |
| 2 | Slicer | 796, 12, 148, 56 | Field: `Site[name]` | Same as page 1 #2 (synced) |
| 3 | Slicer | 952, 12, 148, 56 | Field: `Area[name]` | Same as page 1 #3 (synced) |
| 4 | Slicer | 1108, 12, 148, 56 | Field: `Listing Price[listing_id]` | Style: Dropdown. Selection: **Single select** on. Search on (slicer menu `...` > Search). Header text "Listing (history)" |
| 5 | Card | 24, 84, 240, 96 | `[Price Changes]` | Category label "Price changes" |
| 6 | Card | 272, 84, 240, 96 | `[Price Cuts]` | Category label "Cuts"; callout value colour Theme colour 1 |
| 7 | Card | 520, 84, 240, 96 | `[Price Rises]` | Category label "Rises"; callout value colour Theme colour 4 |
| 8 | Card | 768, 84, 240, 96 | `[Average Change]` | Category label "Average change" |
| 9 | Card | 1016, 84, 240, 96 | `[Listings]` | Category label "Listings seen this week" |
| 10 | Stacked column chart | 24, 196, 620, 250 | X-axis: `Week[week_key]`; Y-axis: `[Price Cuts]`, `[Price Rises]` | Title "Changes caught by each weekly run". X-axis type: Categorical, sorted by `week_key` ascending. Colours: Price Cuts Theme colour 1, Price Rises Theme colour 4. Legend: top. Data labels on |
| 11 | Line chart | 660, 196, 596, 250 | X-axis: `Week[week_key]`; Y-axis: `[Competitor Price Per m²]` | Title "Price per m² of the picked listing". X-axis type: Continuous. Markers on. Line Theme colour 1. Analytics pane > Y-axis constant line > Add > Value: fx > Field value `[Our Same-Type Price Per m²]`; line colour Theme colour 2, style Dashed; Data label on, Text "Name", Name "Our units, same type and area" |
| 12 | Table | 24, 462, 1232, 242 | `Price Change[listing_id]`, `Site[name]`, `Area[name]`, `Compound[compound]`, `Compound[developer]`, `Property Type[unit_type]`, `Price Change[old_week_key]`, `Week[week_key]`, `Price Change[old_price_per_m2]`, `Price Change[new_price_per_m2]`, `Price Change[change_pct]`, `Price Change[Direction]` | Title "Every change". Set `old_price_per_m2`, `new_price_per_m2` and `change_pct` to **Don't summarize**. Rename on the visual: listing_id "Listing", name (Site) "Site", name (Area) "Area", compound "Compound", developer "Developer", unit_type "Type", old_week_key "Was in week", week_key "Caught in week", old_price_per_m2 "Was per m²", new_price_per_m2 "Now per m²", change_pct "Change %", Direction "Direction". Sort by Change %, ascending (the deepest cuts first). Conditional formatting > Font color on Change %: Format style Rules; If value < 0 then Theme colour 1; If value > 0 then Theme colour 4. Totals off |

The line chart stays empty until one listing on one site is picked: `Competitor Price Per m²`
returns blank for more than one. Read the listing's id and site in the table (#12), pick the site in
slicer #2 and type the id in slicer #4's search box. The site matters: the same id can be a
different listing on another site. The dashed line is missing when we have no unit of the listing's
type in its area. The line has one point per weekly run, so it needs two runs before it is a line.

## Sync the slicers

**View > Sync slicers**. For each slicer, tick **Sync** and **Visible** on the pages below:

| Slicer | Market position | Compounds and developers | Weekly changes | Why |
|---|---|---|---|---|
| Site (`Site[name]`) | yes | yes | yes | One choice of site for all three pages |
| Area (`Area[name]`) | yes | yes | yes | One choice of area for all three pages |
| Listing (`Listing Price[listing_id]`) | no | no | yes | Page 3 only: it drives the price history |

## Not used

No drill-through, bookmarks, buttons or tooltip pages, and no filters in the Filters pane (visual,
page or report level). "The latest run week" is applied in the measures, where a filter cannot be
cleared by accident. Three pages, three slicers and the interactions in `07-interactions.md` answer
the three questions.
