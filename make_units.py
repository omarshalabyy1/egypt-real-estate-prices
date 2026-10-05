# Medians used, EGP per m² (area_benchmark after the New Cairo sample of 2026-10-05: index page 1, 17 listings): Apartment 48437.5 (8), Duplex 123897.225 (2), Town House 82499.99 (1), Twin House 90000 (1), Villa 103714.27 (3). Penthouse and Chalet had no listing and use the Apartment median; the other five areas use New Cairo's until the full run.
"""Run once: writes data/our_units.csv, the client's own units. The client is unnamed, so its units
are generated: ten resale units per area inside real compounds seen on realestate.eg (named as the
site shows them), each priced per m² at a seeded random -15% to +15% around the market median for
its type, so some sit above the market and some below. Unit types use the site's spelling so they
join to the listings."""

import csv
import random
from collections import Counter
from pathlib import Path

MEDIAN = {"Apartment": 48437.5, "Duplex": 123897.225, "Town House": 82499.99, "Twin House": 90000,
          "Villa": 103714.27, "Penthouse": 48437.5, "Chalet": 48437.5}
SIZE = {"Apartment": (100, 200), "Duplex": (200, 300), "Penthouse": (150, 250), "Town House": (180, 260),
        "Twin House": (220, 300), "Villa": (280, 450), "Chalet": (80, 160)}  # m², lowest and highest
BEDROOMS = {"Apartment": 3, "Duplex": 4, "Penthouse": 3, "Town House": 4, "Twin House": 4, "Villa": 5, "Chalet": 2}
CODE = {"Apartment": "APT", "Duplex": "DUP", "Penthouse": "PH", "Town House": "TH", "Twin House": "TW",
        "Villa": "VIL", "Chalet": "CH"}

UNITS = {  # area: (code prefix, [(unit type, compound)])
    "new-cairo": ("NC", [
        ("Apartment", "Jazura Compound New Cairo Samco Holding Developments"),
        ("Apartment", "Mist New Cairo Compound M Squared Development"),
        ("Apartment", "Yardin New Cairo Compound Mass Developments"),
        ("Apartment", "RED G New Cairo Compound Jadeer Group Developments"),
        ("Duplex", "Jade and Blue New Cairo Compound Aspect Developments"),
        ("Penthouse", "The Red Residence Compound New Cairo Al Borouj Misr Development"),
        ("Town House", "Zomra New Cairo Compound Nations Of Sky Development"),
        ("Twin House", "The Vill New Cairo Compound IL CAZAR Developments"),
        ("Villa", "Zomra New Cairo Compound Nations Of Sky Development"),
        ("Villa", "Mist New Cairo Compound M Squared Development"),
    ]),
    "new-administrative-capital": ("CAP", [
        ("Apartment", "Mamsha Vista"),
        ("Apartment", "Mamsha Vista"),
        ("Apartment", "Euphoria Queen Land New Capital Compound Euphoria Group Developments"),
        ("Apartment", "Euphoria Queen Land New Capital Compound Euphoria Group Developments"),
        ("Duplex", "Euphoria Queen Land New Capital Compound Euphoria Group Developments"),
        ("Penthouse", "Mamsha Vista"),
        ("Town House", "Grand Valleys New Capital Compound Mountain View Developments"),
        ("Twin House", "Grand Valleys New Capital Compound Mountain View Developments"),
        ("Villa", "Grand Valleys New Capital Compound Mountain View Developments"),
        ("Villa", "Grand Valleys New Capital Compound Mountain View Developments"),
    ]),
    "sheikh-zayed": ("SZ", [
        ("Apartment", "Summit Sheikh Zayed Compound Ritzy Developments"),
        ("Apartment", "Valea Sheikh Zayed Compound Saudi Group Developments"),
        ("Apartment", "Coy Sheikh Zayed Compound Voya Developments"),
        ("Duplex", "Calma Sheikh Zayed Compound Leaders Developments"),
        ("Town House", "Ons New Zayed Compound Mabany Edris Developments"),
        ("Town House", "SVN Shades New Zayed Compound ZG Developments"),
        ("Twin House", "Clavel New Zayed Compound EDIC Developments"),
        ("Twin House", "West Line New Zayed Compound Living Lines Developments"),
        ("Villa", "Belami New Zayed Compound Pyramids Rocks Developments"),
        ("Villa", "Kinz New Zayed Compound Madaar Developments"),
    ]),
    "sixth-october-city": ("OCT", [
        ("Apartment", "Samaya October Gardens Compound Nilestone Developments"),
        ("Apartment", "Samaya October Gardens Compound Nilestone Developments"),
        ("Apartment", "Hyde Park West October Compound"),
        ("Apartment", "Elm Tree 6 October Compound"),
        ("Apartment", "Hyde Park West October Compound"),
        ("Penthouse", "Westdays 6 October Compound IL CAZAR Development"),
        ("Penthouse", "Westdays 6 October Compound IL CAZAR Development"),
        ("Duplex", "Elm Tree 6 October Compound"),
        ("Town House", "Hyde Park West October Compound"),
        ("Villa", "Hyde Park West October Compound"),
    ]),
    "north-coast": ("NCO", [
        ("Chalet", "Siela North Coast Village Concept Developments"),
        ("Chalet", "Vero North Coast Village Wadi Degla Developments"),
        ("Chalet", "Ondixa North Coast Village AWJ Developments"),
        ("Chalet", "Vista Marina North Coast Village El Tawfiqi Development"),
        ("Chalet", "Al Alamein Lagoons North Coast Village Modon Developments"),
        ("Chalet", "Retan North Coast Village Cairo Global Developments"),
        ("Chalet", "The Island Marina 5 North Coast Village HDP Egypt"),
        ("Villa", "Shores North Coast Village El Amar Group"),
        ("Villa", "Mouj North Coast Village Pledge Developments"),
        ("Villa", "Sky North Village North Coast Sky Ad Developments"),
    ]),
    "mostakbal-city": ("MC", [
        ("Apartment", "Mivida Gardens Mostakbal City Compound Emaar Misr Developments"),
        ("Apartment", "Park Central Mostakbal City Compound Hassan Allam Properties"),
        ("Apartment", "Kukun Mostakbal City Compound The Land Development"),
        ("Duplex", "Park Central Mostakbal City Compound Hassan Allam Properties"),
        ("Penthouse", "Park Central Mostakbal City Compound Hassan Allam Properties"),
        ("Town House", "Mivida Gardens Mostakbal City Compound Emaar Misr Developments"),
        ("Town House", "The Butter Fly Mostakbal City Compound Madinet Masr"),
        ("Twin House", "Scenes Mostakbal City Compound Tatweer Misr Development"),
        ("Villa", "Mivida Gardens Mostakbal City Compound Emaar Misr Developments"),
        ("Villa", "Scenes Mostakbal City Compound Tatweer Misr Development"),
    ]),
}

random.seed(2026)
rows = []
for area_id, (prefix, units) in UNITS.items():
    numbers = Counter()
    for unit_type, compound in units:
        numbers[unit_type] += 1
        size = random.randrange(SIZE[unit_type][0], SIZE[unit_type][1] + 1, 5)
        price_per_m2 = MEDIAN[unit_type] * random.uniform(0.85, 1.15)
        rows.append({
            "unit_code": f"{prefix}-{CODE[unit_type]}-{numbers[unit_type]:02d}",
            "area_id": area_id,
            "compound": compound,
            "unit_type": unit_type,
            "bedrooms": BEDROOMS[unit_type],
            "size_m2": size,
            "asking_price": int(round(price_per_m2 * size, -4)),  # asking prices are round numbers
        })

with open(Path(__file__).parent / "data" / "our_units.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"{len(rows)} units written to data/our_units.csv")
