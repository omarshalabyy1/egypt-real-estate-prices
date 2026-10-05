"""Asking prices from three more listing sites: Property Finder Egypt, Dubizzle (OLX) Egypt and Nawy.
For each site, fetch_<site>(area_id, page) returns one search page's text and parse_<site>(text, url)
turns it into (rows, whether there is a next page). Every row has the same shape (see row()). The
parsers only read the JSON the site embeds in the page and never read agent, broker, seller or contact
fields. A row's area_id comes from the listing's own location, not from the URL asked for: a listing
outside our six areas gets None, so the loader can quarantine it as "no area"."""

import csv
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

ROOT = Path(__file__).parent
USER_AGENT = "egypt-real-estate-prices (+https://github.com/omarshalabyy1/egypt-real-estate-prices)"
DELAY = 2.5  # seconds between any two requests
TRIES = 3  # tries for one page when the site answers 429 or 5xx
# Each site's search page per area and page number (data/site_areas.csv).
with open(ROOT / "data" / "site_areas.csv", newline="", encoding="utf-8") as f:
    URLS = {(r["source"], r["area_id"]): r["url_template"] for r in csv.DictReader(f)}
# The unit types we compare, keyed by the site's label in lower case without spaces or punctuation.
# Any other label (Office, Hotel Apartment, iVilla...) is kept as the site wrote it.
UNIT_TYPES = {"apartment": "Apartment", "villa": "Villa", "townhouse": "Town House",
              "twinhouse": "Twin House", "duplex": "Duplex", "penthouse": "Penthouse",
              "chalet": "Chalet", "studio": "Studio"}
# Each site's own location for our six areas.
PROPERTYFINDER_AREAS = {"new-cairo-city": "new-cairo", "new-capital-city": "new-administrative-capital",
                        "sheikh-zayed-city": "sheikh-zayed", "6-october-city": "sixth-october-city",
                        "north-coast": "north-coast", "mostakbal-city-future-city": "mostakbal-city",
                        "mostakbal-city---future-city": "mostakbal-city"}  # location_tree slugs
DUBIZZLE_AREAS = {"new-cairo": "new-cairo", "new-capital-city": "new-administrative-capital",
                  "sheikh-zayed": "sheikh-zayed", "6th-of-october": "sixth-october-city",
                  "north-coast": "north-coast", "mostakbal-city": "mostakbal-city"}  # location slugs
NAWY_AREAS = {2: "new-cairo", 9: "new-administrative-capital", 26: "sheikh-zayed",
              1: "sixth-october-city", 3: "north-coast", 10: "mostakbal-city"}  # area ids

http = requests.Session()
http.headers["User-Agent"] = USER_AGENT


def get(source, area_id, page):
    """GET one search page and wait DELAY seconds. A 429 or 5xx answer is tried again, up to TRIES
    times in all, waiting longer each time; an error answer left after that fails loudly."""
    url = URLS[source, area_id].format(page=page)
    for attempt in range(TRIES):
        response = http.get(url, timeout=60)
        time.sleep(DELAY)
        if response.status_code not in (429, 500, 502, 503, 504) or attempt == TRIES - 1:
            break
        time.sleep(DELAY * 2 ** (attempt + 1))
    response.raise_for_status()
    return response.content.decode("utf-8")


def unit_type(label):
    """Our name for the site's unit type, or the site's label when it is not a type we compare."""
    if not label:
        return None
    label = " ".join(label.split())
    return UNIT_TYPES.get(re.sub(r"[^a-z]", "", label.lower()), label)


def decimal(value):
    """A positive number, or None (missing, 0, or not a number)."""
    try:
        value = Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None
    return value if value and value > 0 else None


def integer(value):
    """A count of rooms, or None when the site gives none or a word ("studio")."""
    return int(value) if isinstance(value, int) or str(value or "").isdigit() else None


def row(source, listing_id, url, area_id, compound, developer, label, bedrooms, bathrooms, size,
        price, listed_on):
    return {
        "source": source,
        "source_listing_id": str(listing_id),
        "url": url,
        "area_id": area_id,
        "compound": " ".join(compound.split()) if compound else None,
        "developer": " ".join(developer.split()) if developer else None,
        "unit_type": unit_type(label),
        "bedrooms": integer(bedrooms),
        "bathrooms": integer(bathrooms),
        "size_m2": decimal(size),
        "asking_price": decimal(price),
        "listed_on": listed_on,
    }


def next_data(text, url):
    """The JSON a Next.js page embeds in <script id="__NEXT_DATA__">."""
    found = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not found:
        raise RuntimeError(f"No __NEXT_DATA__ on {url}: has the site changed its pages?")
    return json.loads(found.group(1))


# --- Property Finder Egypt -------------------------------------------------------------------

def fetch_propertyfinder(area_id, page):
    return get("propertyfinder", area_id, page)


def parse_propertyfinder(text, url):
    """One search page -> its single-unit listings. Project cards (a development) and project_unit
    cards (a developer's price range for a unit type) are skipped. The compound is the location's
    COMPOUND level, else the level just below a "... Compounds" district (La Vista City under "New
    Capital Compounds"), else the listing's own location when the site files it as a STREET, TOWER or
    SUBCOMMUNITY (Solana East, Mayan New Cairo); otherwise None. The site gives no developer name."""
    result = next_data(text, url)["props"]["pageProps"]["searchResult"]
    if not result["listings"]:
        raise RuntimeError(f"No listings on {url}: has the site changed its pages?")
    rows = []
    for item in result["listings"]:
        p = item.get("property")
        if item.get("listing_type") != "property" or not p:
            continue
        tree, location = p.get("location_tree") or [], p.get("location") or {}
        compound = (next((t["name"] for t in tree if t.get("type") == "COMPOUND"), None)
                    or next((b["name"] for a, b in zip(tree, tree[1:]) if a["name"].endswith(" Compounds")), None)
                    or (location.get("name") if location.get("type") in ("STREET", "TOWER", "SUBCOMMUNITY") else None))
        price, size = p.get("price") or {}, p.get("size") or {}
        rows.append(row(
            "propertyfinder", p["id"], p.get("share_url"),
            next((PROPERTYFINDER_AREAS[t["slug"]] for t in tree if t.get("slug") in PROPERTYFINDER_AREAS), None),
            compound, None, p.get("property_type"), p.get("bedrooms"), p.get("bathrooms"),
            size.get("value") if size.get("unit") == "sqm" else None,
            price.get("value") if price.get("currency") == "EGP" and not price.get("is_hidden") else None,
            datetime.fromisoformat(p["listed_date"].replace("Z", "+00:00")).date() if p.get("listed_date") else None,
        ))
    meta = result["meta"]
    return rows, meta["page"] < meta["page_count"]


# --- Dubizzle (OLX) Egypt --------------------------------------------------------------------

def fetch_dubizzle(area_id, page):
    return get("dubizzle", area_id, page)


def parse_dubizzle(text, url):
    """One search page -> its for-sale ads. The compound is the ad's deepest location below the city
    (level 3 or 4: a compound or a district, the site does not tell them apart). The price is the
    ad's own, also when it is marked negotiable; the site gives no developer name. listed_on is the
    ad's creation day (UTC). The site's nbPages does not follow nbHits, so the next page is counted
    from nbHits."""
    start = text.find("window.state = ")
    if start < 0:
        raise RuntimeError(f"No window.state on {url}: has the site changed its pages?")
    content = json.JSONDecoder().raw_decode(text, start + len("window.state = "))[0]["algolia"]["content"]
    if not content["hits"]:
        raise RuntimeError(f"No ads on {url}: has the site changed its pages?")
    rows = []
    for hit in content["hits"]:
        if hit.get("purpose") != "for-sale":
            continue
        fields = hit.get("extraFields") or {}
        levels = hit.get("location") or []
        rows.append(row(
            "dubizzle", hit["externalID"],
            f"https://www.dubizzle.com.eg/en/ad/{hit['slug']}-ID{hit['externalID']}.html",
            next((DUBIZZLE_AREAS[l["slug"]] for l in levels if l.get("slug") in DUBIZZLE_AREAS), None),
            levels[-1]["name"] if levels and levels[-1].get("level", 0) >= 3 else None, None,
            next((f.get("formattedValue_l1") for f in hit.get("formattedExtraFields") or [] if f.get("attribute") == "type"), None),
            fields.get("rooms"), fields.get("bathrooms"), fields.get("ft"), fields.get("price"),
            datetime.fromtimestamp(hit["createdAt"], timezone.utc).date() if hit.get("createdAt") else None,
        ))
    page = int(parse_qs(urlparse(url).query).get("page", ["1"])[0])
    return rows, page * content["hitsPerPage"] < content["nbHits"]


# --- Nawy ------------------------------------------------------------------------------------

def fetch_nawy(area_id, page):
    return get("nawy", area_id, page)


def parse_nawy(text, url):
    """One property search page -> its units. The price is the payment plan's minPrice, the price
    the unit page shows. Nawy gives no listing date (readyBy is the delivery date), so listed_on is
    None. The area is the unit's area, else its parent area (Golden Square -> New Cairo)."""
    result = next_data(text, url)["props"]["pageProps"]["loadedSearchResultsSSR"]
    if not result["results"]:
        raise RuntimeError(f"No units on {url}: has the site changed its pages?")
    rows = []
    for unit in result["results"]:
        area, plan = unit.get("area") or {}, unit.get("paymentPlan") or {}
        rows.append(row(
            "nawy", unit["id"], unit.get("shareLink"),
            NAWY_AREAS.get(area.get("id")) or NAWY_AREAS.get(area.get("parentAreaId")),
            (unit.get("compound") or {}).get("name"), (unit.get("developer") or {}).get("name"),
            unit.get("propertyType"), unit.get("numberOfBedrooms"), unit.get("numberOfBathrooms"),
            unit.get("unitArea"), plan.get("minPrice") if plan.get("currency") == "EGP" else None, None,
        ))
    return rows, result["page"] * result["pageSize"] < result["total"]


SITES = {
    "propertyfinder": (fetch_propertyfinder, parse_propertyfinder),
    "dubizzle": (fetch_dubizzle, parse_dubizzle),
    "nawy": (fetch_nawy, parse_nawy),
}
