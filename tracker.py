"""The weekly steps Airflow runs: load the reference data, read this week's asking prices from
realestate.eg, and print the competitor price cuts and our units' gap to the market. Each step is
one function. Every run reads the prices on the site today: there is no incremental read."""

import csv
import gzip
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import psycopg
import requests
from bs4 import BeautifulSoup
from psycopg.types.json import Jsonb

ROOT = Path(__file__).parent
SITE = "https://realestate.eg"
USER_AGENT = "egypt-real-estate-prices (+https://github.com/omarshalabyy1/egypt-real-estate-prices)"
CARDS_PER_AREA = 150  # read an area's index pages until this many residential unit cards...
MAX_PAGES_PER_AREA = 8  # ...or this many pages (50 cards a page), whichever comes first
DELAY = 2.5  # seconds between any two requests
# Index badges. Non-residential cards are skipped without reading their page; a badge in neither
# set is quarantined so a new type is seen, not dropped.
RESIDENTIAL = {"Apartment", "Apartment With Garden", "Chalet", "Chalet With Garden", "Duplex",
               "Penthouse", "Studio", "Town House", "Twin House", "Villa"}
NON_RESIDENTIAL = {"Store", "Clinic", "Office", "Mall", "Administrative", "Commercial", "Pharmacy",
                   "Shop", "Warehouse"}

http = requests.Session()
http.headers["User-Agent"] = USER_AGENT


def connect():
    return psycopg.connect(
        host=os.environ.get("WAREHOUSE_HOST", "localhost"),
        port=os.environ.get("WAREHOUSE_PORT", "5451"),
        dbname="prices",
        user="prices",
        password=os.environ["WAREHOUSE_PASSWORD"],
    )


def run_week_of(day):
    """The Sunday that starts the day's week."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def this_week():
    return run_week_of(datetime.now(timezone.utc).date())


# --- Step 1: reference data ------------------------------------------------------------------

def load_reference():
    """Create the tables and views, then load the areas and our own units from data/."""
    with connect() as conn:
        conn.execute((ROOT / "sql" / "schema.sql").read_text())
        for table, key, file in (("area", "area_id", "areas.csv"), ("our_unit", "unit_code", "our_units.csv")):
            with open(ROOT / "data" / file, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            cols = list(rows[0])
            updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != key)
            conn.cursor().executemany(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
                f"ON CONFLICT ({key}) DO UPDATE SET {updates}",
                [[r[c] or None for c in cols] for r in rows],
            )
            print(f"{table}: {len(rows)} rows loaded")


# --- Step 2: this week's asking prices ----------------------------------------------------------

def clean(text):
    """One space between words (the site puts non-breaking spaces in names); None stays None."""
    return " ".join(text.split()) if text else None


def number(value):
    try:
        return Decimal(re.sub(r"[^\d.-]", "", str(value))) if value not in (None, "") else None
    except InvalidOperation:
        return None


def parse_index(html, url):
    """One index page -> (cards, whether there is a next page). A card without beds/baths/m² is a
    compound or project, not a unit (is_project). A page with no cards at all means the site changed."""
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for card in soup.select(".property-card"):
        link = card.select_one(".property-card-title a")
        href = urljoin(url, link["href"]) if link else ""
        listing_id = re.match(r"/en/(\d+)-", urlparse(href).path)
        badge = card.select_one(".property-badge")
        subtitle = card.select_one(".property-card-subtitle a")
        location = card.select_one(".property-card-location a")
        specs = [s.get_text(" ", strip=True) for s in card.select(".property-spec")]
        cards.append({
            "listing_id": int(listing_id.group(1)) if listing_id else None,
            "url": href,
            "area_id": urlparse(location["href"]).path.rstrip("/").split("/")[-1] if location else None,
            "unit_type": clean(badge.get_text()) if badge else None,
            "compound": clean(subtitle.get_text(" ")) if subtitle else None,
            "bedrooms": next((number(s) for s in specs if "Bed" in s), None),
            "bathrooms": next((number(s) for s in specs if "Bath" in s), None),
            "size_m2": next((number(s) for s in specs if "m²" in s), None),
            "is_project": not specs,
        })
    if not cards:
        raise RuntimeError(f"No cards on {url}: has the site changed its pages?")
    return cards, soup.select_one("a[rel=next]") is not None


def parse_unit(html, url):
    """One unit page -> its asking price, size, rooms, compound and developer from the page's
    schema.org data, or None when the page has no Product block (the price lives there)."""
    blocks = []
    for script in BeautifulSoup(html, "html.parser").select('script[type="application/ld+json"]'):
        try:
            blocks.append(json.loads(script.get_text(), strict=False))
        except ValueError:
            continue
    blocks = [b for b in blocks if isinstance(b, dict)]
    product = next((b for b in blocks if b.get("@type") == "Product"), None)
    if product is None:
        return None
    home = next((b for b in blocks if "containedInPlace" in b), {})
    facts = {p.get("name"): p.get("value") for p in product.get("additionalProperty", [])}
    price = number((product.get("offers") or {}).get("price"))
    size = number(facts.get("Area") or (home.get("floorSize") or {}).get("value"))
    return {
        "asking_price": price,
        "size_m2": size,
        "price_per_m2": round(price / size, 2) if price and size and size > 0 else None,
        "bedrooms": number(facts.get("Bedrooms") or home.get("numberOfRooms")),
        "bathrooms": number(facts.get("Bathrooms") or home.get("numberOfBathroomsTotal")),
        # The site's compound name as shown, e.g. "The Square New Cairo Compound Al Ahly Sabbour
        # Developments": it holds the area and the developer in words that differ from brand.name.
        "compound": clean((home.get("containedInPlace") or {}).get("name")),
        "developer": clean((product.get("brand") or home.get("seller") or {}).get("name")),
    }


def read_robots():
    """robots.txt, read with our User-Agent: the site answers Python's default one with 403, which
    RobotFileParser.read() would take as "nothing allowed"."""
    robots = RobotFileParser()
    robots.parse(http.get(f"{SITE}/robots.txt", timeout=60).text.splitlines())
    time.sleep(DELAY)
    return robots


def fetch(robots, url, name):
    """GET one page as robots.txt allows, keep a gzipped copy in data/raw/<date>/ (listed in its
    index.csv), then wait DELAY seconds."""
    if not robots.can_fetch(USER_AGENT, url):
        raise RuntimeError(f"robots.txt does not allow {url}")
    response = http.get(url, timeout=60)
    fetched_at = datetime.now(timezone.utc)
    folder = ROOT / "data" / "raw" / fetched_at.date().isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.html.gz").write_bytes(gzip.compress(response.content))
    new_index = not (folder / "index.csv").exists()
    with open(folder / "index.csv", "a", newline="", encoding="utf-8") as f:
        if new_index:
            f.write("url,fetched_at,http_status,bytes\n")
        csv.writer(f).writerow([url, fetched_at.isoformat(), response.status_code, len(response.content)])
    time.sleep(DELAY)
    return response, fetched_at


def card_problem(card, area_ids):
    """Why a unit card cannot be used, or None."""
    if card["listing_id"] is None:
        return "unparseable id"
    if card["area_id"] not in area_ids:
        return "no area"
    if card["unit_type"] not in RESIDENTIAL:
        return "unknown type"
    return None


def unit_problem(page):
    """Why a unit page's values cannot be used, or None."""
    if not page["asking_price"] or page["asking_price"] <= 0:
        return "price missing or <= 0"
    if not page["size_m2"] or page["size_m2"] <= 0:
        return "size missing or <= 0"
    return None


def reject(url, fetched_at, reason, payload):
    return {"url": url, "fetched_at": fetched_at, "reason": reason,
            "payload": Jsonb(payload, dumps=lambda o: json.dumps(o, default=str))}


def read_cards(robots, area_id, location_id, area_ids, counts, rejects):
    """An area's index pages, in order, until CARDS_PER_AREA residential unit cards or
    MAX_PAGES_PER_AREA pages -> those cards (all of the last page's). Project and non-residential
    cards are counted and skipped; a card failing card_problem is quarantined."""
    cards = []
    for page in range(1, MAX_PAGES_PER_AREA + 1):
        url = f"{SITE}/en/listings/{area_id}?location={location_id}&page={page}"
        response, fetched_at = fetch(robots, url, f"{area_id}-page-{page}")
        response.raise_for_status()
        page_cards, has_next = parse_index(response.content, response.url)
        for card in page_cards:
            counts["cards seen"] += 1
            if card["is_project"]:
                counts["project cards skipped"] += 1
            elif card["unit_type"] in NON_RESIDENTIAL:
                counts["non-residential cards skipped"] += 1
            elif reason := card_problem(card, area_ids):
                rejects.append(reject(card["url"] or url, fetched_at, reason, card))
            else:
                cards.append(card)
        if not has_next or len(cards) >= CARDS_PER_AREA:
            break
    return cards


def read_units(robots, cards, counts, rejects):
    """Read each card's unit page -> one row per unit with today's asking price. The page's
    schema.org values win over the card's; a page that fails a check is quarantined."""
    units = []
    for card in cards:
        response, fetched_at = fetch(robots, card["url"], str(card["listing_id"]))
        counts["unit pages fetched"] += 1
        page = parse_unit(response.content, card["url"]) if response.status_code == 200 else None
        # "developer" is on the page only, and a page may name none: save() still needs the key.
        unit = {**card, "developer": None, **{k: v for k, v in (page or {}).items() if v is not None},
                "observed_on": fetched_at.date(), "fetched_at": fetched_at}
        if response.status_code != 200:
            reason = f"http {response.status_code}"
        elif page is None:
            reason = "no JSON-LD"
        else:
            reason = unit_problem(page)
        if reason:
            rejects.append(reject(card["url"], fetched_at, reason, {**card, "page": page}))
        else:
            units.append(unit)
    return units


def save(conn, units, rejects, run_week):
    """Keep each listing's latest description, add each price to the history (never overwritten,
    the day's first price wins) and keep the rejected rows with their reason."""
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO listing (listing_id, url, area_id, compound, developer, unit_type, bedrooms, bathrooms,"
        " size_m2, first_seen, last_seen) VALUES (%(listing_id)s, %(url)s, %(area_id)s, %(compound)s,"
        " %(developer)s, %(unit_type)s, %(bedrooms)s, %(bathrooms)s, %(size_m2)s, %(observed_on)s,"
        " %(observed_on)s) ON CONFLICT (listing_id) DO UPDATE SET url = EXCLUDED.url,"
        " area_id = EXCLUDED.area_id, compound = EXCLUDED.compound, developer = EXCLUDED.developer,"
        " unit_type = EXCLUDED.unit_type, bedrooms = EXCLUDED.bedrooms, bathrooms = EXCLUDED.bathrooms,"
        " size_m2 = EXCLUDED.size_m2, last_seen = EXCLUDED.last_seen",
        units,
    )
    cur.executemany(
        "INSERT INTO price_observation (listing_id, observed_on, asking_price, price_per_m2, fetched_at, run_week)"
        " VALUES (%(listing_id)s, %(observed_on)s, %(asking_price)s, %(price_per_m2)s, %(fetched_at)s,"
        " %(run_week)s) ON CONFLICT DO NOTHING",
        [{**u, "run_week": run_week} for u in units],
    )
    cur.executemany(
        "INSERT INTO quarantine (run_week, fetched_at, url, reason, payload) VALUES (%(run_week)s,"
        " %(fetched_at)s, %(url)s, %(reason)s, %(payload)s) ON CONFLICT DO NOTHING",
        [{**r, "run_week": run_week} for r in rejects],
    )


def collect(run_week):
    """Read every area's index pages, then each residential unit's page once, and save the prices
    and the rejected rows in one transaction. No price read at all fails the run."""
    robots = read_robots()
    with connect() as conn:
        areas = conn.execute("SELECT area_id, location_id FROM area ORDER BY area_id").fetchall()
    counts, rejects, cards = Counter(), [], {}
    for area_id, location_id in areas:
        for card in read_cards(robots, area_id, location_id, {a for a, _ in areas}, counts, rejects):
            if card["listing_id"] in cards:
                counts["duplicate cards skipped"] += 1  # the same unit on two pages
            cards[card["listing_id"]] = card
    units = read_units(robots, cards.values(), counts, rejects)
    if not units:
        raise RuntimeError("No asking price read this week")
    with connect() as conn:
        save(conn, units, rejects, run_week)
    counts["prices saved"] = len(units)
    for reason, n in Counter(r["reason"] for r in rejects).items():
        counts[f"quarantined: {reason}"] = n
    for name, n in counts.items():
        print(f"{name}: {n}")


# --- Step 3: report ------------------------------------------------------------------------------

def report(run_week):
    """Print this week's competitor price cuts and each of our units' gap to its area's median."""
    with connect() as conn:
        cuts = conn.execute(
            "SELECT listing_id, area_id, compound, unit_type, old_price, new_price, change_pct FROM price_change"
            " WHERE caught_week = %s AND is_cut ORDER BY change_pct", (run_week,),
        ).fetchall()
        print(f"Week of {run_week}: {len(cuts)} competitor price cuts")
        for listing_id, area, compound, unit_type, old, new, pct in cuts:
            print(f"- {listing_id} {unit_type} in {compound} ({area}): {old} -> {new} EGP ({pct}%)")
        print("Our units against the median price per m2 of the same type in the same area:")
        for code, ours, median, gap, compared in conn.execute(
            "SELECT unit_code, price_per_m2, median_price_per_m2, gap_pct, listings_compared FROM unit_gap"
            " ORDER BY unit_code"
        ).fetchall():
            print(f"- {code}: {ours} vs {median} ({gap}%, {compared} listings)" if compared else f"- {code}: no listing to compare")
