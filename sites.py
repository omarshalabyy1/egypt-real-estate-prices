"""Asking prices from three more listing sites: Property Finder Egypt, Dubizzle (OLX) Egypt and Nawy.
Each site's search page embeds its results as JSON. extract_<site>(text, url) takes that JSON block out
of the page and removes every agent, broker, agency, client, user and contact field (strip_contacts)
before anything is written; parse_<site>(block, url) turns the stripped block into (rows, whether there
is a next page). Every row has the same shape (see row()). A row's area_id comes from the listing's own
location, not from the URL asked for: a listing outside our areas (config/client.yaml) gets None."""

import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests

from config import load_config

CFG = load_config()
USER_AGENT = "egypt-real-estate-prices (+https://github.com/omarshalabyy1/egypt-real-estate-prices)"
PACE = {s["id"]: s["pace_seconds"] for s in CFG["sites"]}  # seconds between any two requests to a site
TRIES = 3  # tries for one page when the site answers 429 or 5xx
CAIRO = ZoneInfo("Africa/Cairo")  # the sites' own time zone, for a listing's day
CURRENCY = CFG["client"]["currency"]  # a price in another currency is no price
# Every search the weekly run reads, site by site and area by area (config/client.yaml): its URL per page
# number and the most pages read. Dubizzle has two searches per area.
SEARCHES = [{"source": site, "area_id": a["id"], "search": s["search"], "url_template": s["url"],
             "max_pages": s["max_pages"]}
            for site in PACE for a in CFG["areas"] for s in a["sites"].get(site, {}).get("searches", [])]


def locations(site):
    """The site's name for each of our areas (its `locations` in config/client.yaml) -> our area id."""
    return {loc: a["id"] for a in CFG["areas"] for loc in a["sites"].get(site, {}).get("locations", [])}

# The home types the sites list, keyed by the site's label in lower case without spaces or punctuation.
# Any other label (Office, Hotel Apartment...) is kept as the site wrote it.
UNIT_TYPES = {"apartment": "Apartment", "apartmentwithgarden": "Apartment", "villa": "Villa", "standalonevilla": "Villa",
              "townhouse": "Town House", "twinhouse": "Twin House", "duplex": "Duplex",
              "penthouse": "Penthouse", "chalet": "Chalet", "chaletwithgarden": "Chalet", "studio": "Studio",
              "ivilla": "iVilla", "cabin": "Cabin", "loft": "Loft"}
# The types the client compares (rules.unit_types). A known type the client does not compare is skipped.
RESIDENTIAL = set(CFG["rules"]["unit_types"])
if unknown := RESIDENTIAL - set(UNIT_TYPES.values()):
    raise SystemExit(f"config/client.yaml rules.unit_types: {', '.join(sorted(unknown))} is not a type sites.py knows")
NOT_COMPARED = set(UNIT_TYPES.values()) - RESIDENTIAL
# Labels known not to be homes: skipped and counted, never quarantined. "Project" is a realestate.eg
# card for a whole compound, not a unit. A label in neither set is quarantined as "unknown type".
NON_RESIDENTIAL = {"Office", "Administrative", "Retail", "Medical", "Clinic", "Store", "Shop", "Commercial",
                   "Pharmacy", "Hotel Apartment", "Mall", "Warehouse", "Project", "Building", "Laboratory"}
# A JSON key holding any of these words is removed, with everything under it, before a block is kept.
CONTACT = re.compile(r"agent|broker|agency|client|user|contact|phone|mobile|whatsapp|email|seller|owner"
                     r"|description|title", re.I)
# Each site's own location for our areas.
PROPERTYFINDER_AREAS = locations("propertyfinder")  # location_tree slugs
DUBIZZLE_AREAS = locations("dubizzle")  # location slugs
NAWY_AREAS = locations("nawy")  # area ids

http = requests.Session()
http.headers["User-Agent"] = USER_AGENT


def get(url, pace):
    """GET one page and wait pace seconds. A 429 or 5xx answer is tried again, up to TRIES times in
    all, waiting longer each time; a 404 is tried once more. An error answer left after that fails loudly."""
    for attempt in range(TRIES):
        response = http.get(url, timeout=60)
        time.sleep(pace)
        again = response.status_code in (429, 500, 502, 503, 504) or (response.status_code == 404 and attempt == 0)
        if not again or attempt == TRIES - 1:
            break
        time.sleep(pace * 2 ** (attempt + 1))
    response.raise_for_status()
    return response


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


def cairo_date(moment):
    """The day in Cairo of an aware datetime."""
    return moment.astimezone(CAIRO).date()


def strip_contacts(value):
    """The JSON value without any key naming a person or a way to reach one (CONTACT), at any depth."""
    if isinstance(value, dict):
        return {k: strip_contacts(v) for k, v in value.items() if not CONTACT.search(k)}
    if isinstance(value, list):
        return [strip_contacts(v) for v in value]
    return value


def next_data(text, url):
    """The JSON a Next.js page embeds in <script id="__NEXT_DATA__">, contact fields removed."""
    found = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not found:
        raise RuntimeError(f"No __NEXT_DATA__ on {url}: has the site changed its pages?")
    return strip_contacts(json.loads(found.group(1)))


# --- Property Finder Egypt -------------------------------------------------------------------

def extract_propertyfinder(text, url):
    return next_data(text, url)


def parse_propertyfinder(block, url):
    """One search page -> its single-unit listings. Project cards (a development) and project_unit
    cards (a developer's price range for a unit type) are skipped. The compound is the location's
    COMPOUND level, else the level just below a "... Compounds" district (La Vista City under "New
    Capital Compounds"), else the listing's own location when the site files it as a STREET, TOWER or
    SUBCOMMUNITY (Solana East, for one); otherwise None. The site gives no developer name.
    listed_on is the listing day in Cairo."""
    result = block["props"]["pageProps"]["searchResult"]
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
            price.get("value") if price.get("currency") == CURRENCY and not price.get("is_hidden") else None,
            cairo_date(datetime.fromisoformat(p["listed_date"].replace("Z", "+00:00"))) if p.get("listed_date") else None,
        ))
    meta = result["meta"]
    return rows, meta["page"] < meta["page_count"]


# --- Dubizzle (OLX) Egypt --------------------------------------------------------------------

def extract_dubizzle(text, url):
    """The window.state JSON the page embeds, contact fields removed."""
    start = text.find("window.state = ")
    if start < 0:
        raise RuntimeError(f"No window.state on {url}: has the site changed its pages?")
    return strip_contacts(json.JSONDecoder().raw_decode(text, start + len("window.state = "))[0])


def parse_dubizzle(block, url):
    """One search page -> its for-sale ads. The compound is the ad's deepest location below the city
    (level 3 or 4: a compound or a district, the site does not tell them apart). The price is the
    ad's own, also when it is marked negotiable; the site gives no developer name. listed_on is the
    ad's creation day in Cairo. The site's nbPages does not follow nbHits, so the next page is counted
    from nbHits."""
    content = block["algolia"]["content"]
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
            cairo_date(datetime.fromtimestamp(hit["createdAt"], timezone.utc)) if hit.get("createdAt") else None,
        ))
    page = int(parse_qs(urlparse(url).query).get("page", ["1"])[0])
    return rows, page * content["hitsPerPage"] < content["nbHits"]


# --- Nawy ------------------------------------------------------------------------------------

def extract_nawy(text, url):
    return next_data(text, url)


def parse_nawy(block, url):
    """One property search page -> its units. The price is the payment plan's minPrice, the price
    the unit page shows. Nawy gives no listing date (readyBy is the delivery date), so listed_on is
    None. The area is the unit's area, else its parent area (a district's city)."""
    result = block["props"]["pageProps"]["loadedSearchResultsSSR"]
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
            unit.get("unitArea"), plan.get("minPrice") if plan.get("currency") == CURRENCY else None, None,
        ))
    return rows, result["page"] * result["pageSize"] < result["total"]


def stated_total(source, block):
    """How many listings the site says the search has, or None."""
    if source == "propertyfinder":
        return block["props"]["pageProps"]["searchResult"]["meta"].get("total_count")
    if source == "dubizzle":
        return block["algolia"]["content"].get("nbHits")
    return block["props"]["pageProps"]["loadedSearchResultsSSR"].get("total")


SITES = {
    "propertyfinder": (extract_propertyfinder, parse_propertyfinder),
    "dubizzle": (extract_dubizzle, parse_dubizzle),
    "nawy": (extract_nawy, parse_nawy),
}
