"""Run after a weekly run: writes data/our_units.csv, the client's own units. The client is unnamed, so
its units are generated: ten resale units per area, 60 in all, each inside a real compound that has at
least 3 listings in silver for the latest run week (named and with the developer as a site writes them),
each priced per m² at a seeded random -15% to +15% around the market median for its area and type in
gold.area_benchmark (pooled over sites), so some sit above the market and some below.

A pair of area and type with no listing that week uses the same type's median pooled over all areas;
a type with no listing anywhere uses the area's Apartment median. Then reload and rebuild gold:

    python make_units.py
    python -c "import tracker, datetime; c = tracker.connect(); tracker.load_reference(c); c.commit(); tracker.build_gold(datetime.date(2026, 10, 4))"
"""

import csv
import random
from collections import Counter
from pathlib import Path

import tracker

SIZE = {"Apartment": (100, 200), "Duplex": (200, 300), "Penthouse": (150, 250), "Town House": (180, 260),
        "Twin House": (220, 300), "Villa": (280, 450), "Chalet": (80, 160)}  # m², lowest and highest
BEDROOMS = {"Apartment": 3, "Duplex": 4, "Penthouse": 3, "Town House": 4, "Twin House": 4, "Villa": 5, "Chalet": 2}
CODE = {"Apartment": "APT", "Duplex": "DUP", "Penthouse": "PH", "Town House": "TH", "Twin House": "TW",
        "Villa": "VIL", "Chalet": "CH"}
UNITS = {  # area: (code prefix, the ten unit types)
    "new-cairo": ("NC", ["Apartment"] * 4 + ["Duplex", "Penthouse", "Town House", "Twin House"] + ["Villa"] * 2),
    "new-administrative-capital": ("CAP", ["Apartment"] * 4 + ["Duplex", "Penthouse", "Town House", "Twin House"]
                                   + ["Villa"] * 2),
    "sheikh-zayed": ("SZ", ["Apartment"] * 3 + ["Duplex"] + ["Town House"] * 2 + ["Twin House"] * 2 + ["Villa"] * 2),
    "sixth-october-city": ("OCT", ["Apartment"] * 5 + ["Penthouse"] * 2 + ["Duplex", "Town House", "Villa"]),
    "north-coast": ("NCO", ["Chalet"] * 7 + ["Villa"] * 3),
    "mostakbal-city": ("MC", ["Apartment"] * 3 + ["Duplex", "Penthouse"] + ["Town House"] * 2 + ["Twin House"]
                       + ["Villa"] * 2),
}

with tracker.connect() as conn:
    median = {(a, t): m for a, t, m in conn.execute(
        "SELECT a.area_id, t.unit_type, b.median_price_per_m2 FROM gold.area_benchmark b"
        " JOIN gold.dim_area a USING (area_key) JOIN gold.dim_property_type t USING (type_key)")}
    type_median = dict(conn.execute(
        "SELECT t.unit_type, percentile_cont(0.5) WITHIN GROUP (ORDER BY f.price_per_m2)::numeric"
        " FROM gold.pooled_listing_price f JOIN gold.dim_property_type t USING (type_key)"
        " WHERE f.week_key = (SELECT max(week_key) FROM gold.fact_listing_price) GROUP BY t.unit_type"))
    compounds = conn.execute(
        "SELECT l.area_id, l.unit_type, l.compound, l.developer, count(*) FROM silver.listing l"
        " JOIN silver.price_observation o USING (source, listing_id)"
        " WHERE o.run_week = (SELECT max(run_week) FROM silver.price_observation) AND l.compound IS NOT NULL"
        " GROUP BY 1, 2, 3, 4 HAVING count(*) >= 3 ORDER BY 1, 2, 3, 4").fetchall()

random.seed(2026)
rows, fallbacks = [], Counter()
for area_id, (prefix, types) in UNITS.items():
    numbers = Counter()
    for unit_type in types:
        numbers[unit_type] += 1
        # A compound with 3 listings of this type in the area, else with 3 listings of any type there.
        choices = ([c[2:4] for c in compounds if c[:2] == (area_id, unit_type)]
                   or sorted({c[2:4] for c in compounds if c[0] == area_id}, key=lambda c: (c[0], c[1] or "")))
        compound, developer = random.choice(choices)
        if (area_id, unit_type) in median:
            market = median[area_id, unit_type]
        else:
            market = type_median.get(unit_type) or median[area_id, "Apartment"]
            fallbacks[f"{area_id} {unit_type}"] += 1
        size = random.randrange(SIZE[unit_type][0], SIZE[unit_type][1] + 1, 5)
        price_per_m2 = float(market) * random.uniform(0.85, 1.15)
        rows.append({
            "unit_code": f"{prefix}-{CODE[unit_type]}-{numbers[unit_type]:02d}",
            "area_id": area_id,
            "compound": compound,
            "developer": developer or "",
            "unit_type": unit_type,
            "bedrooms": BEDROOMS[unit_type],
            "size_m2": size,
            "asking_price": int(round(price_per_m2 * size, -4)),  # asking prices are round numbers
        })

with open(Path(__file__).parent / "data" / "our_units.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print(f"{len(rows)} units written to data/our_units.csv; fallback medians used: {dict(fallbacks) or 'none'}")
