"""Asking prices from Bayut Egypt and Aqarmap. Both sites refuse plain HTTP readers, so their search
pages are opened by hand in a real browser (fetch_bayut_aqarmap.py) and parsed here from the saved
copy. parse_<site>(html, url) turns one saved search page into (rows, whether there is a next page),
each row in the shape of sites.row(). The parsers read only the data the page embeds for its listings
and never read agent, broker, owner, agency or contact fields. A row's area_id comes from the
listing's own location, not from the page asked for: a listing outside our areas gets None."""

import json
import re

from bs4 import BeautifulSoup

from sites import CFG, CURRENCY, locations, row

# Bayut's own city for our areas (addressLocality in the page's JSON-LD).
BAYUT_AREAS = locations("bayut")
# Aqarmap's location slug for our areas (each area's aqarmap path), longest first, so a path inside another
# area's path wins (Aqarmap files some cities under others: see config/client.yaml).
AQARMAP_AREAS = dict(sorted(((a["sites"]["aqarmap"]["path"], a["id"]) for a in CFG["areas"] if "aqarmap" in a["sites"]),
                            key=lambda item: -len(item[0])))


def json_ld(html):
    """Every <script type="application/ld+json"> block on the page."""
    return [json.loads(block) for block in
            re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)]


def has_next(html):
    """Both sites put <link rel="next"> in the page head while a next page exists."""
    return re.search(r'<link[^>]*rel="next"', html) is not None


# --- Bayut Egypt -----------------------------------------------------------------------------

def parse_bayut(html, url):
    """One search page -> its listings, from the JSON-LD ItemList. The compound is only on the
    listing card ("<compound>, <district>, <city>, <governorate>"): it is the card's deepest place below the city
    (a compound or a district, the site does not tell them apart), else None. The page gives no
    developer name and no listing date."""
    items = [element["item"] for block in json_ld(html) for node in block.get("@graph", [])
             for element in (node.get("mainEntity") or {}).get("itemListElement", [])]
    if not items:
        raise RuntimeError(f"No listings in the JSON-LD of {url}: has the site changed its pages?")
    places = {}  # listing id -> its card's location, deepest place first
    for card in BeautifulSoup(html, "html.parser").select('li[aria-label="Listing"]'):
        link, place = card.select_one('a[aria-label="Listing link"]'), card.select_one('[aria-label="Location"]')
        if link and place:
            places[re.search(r"details-(\d+)", link["href"]).group(1)] = [p.strip() for p in place.get_text().split(",")]
    if not places:
        raise RuntimeError(f"No listing cards on {url}: has the site changed its pages?")
    rows = []
    for item in items:
        home = item["mainEntity"]
        listing_id = re.search(r"details-(\d+)", item["url"]).group(1)
        path, size = places.get(listing_id, []), home.get("floorSize") or {}
        rows.append(row(
            "bayut", listing_id, item["url"], BAYUT_AREAS.get((home.get("address") or {}).get("addressLocality")),
            path[0] if len(path) >= 3 else None, None, home.get("accommodationCategory"),
            home.get("numberOfBedrooms"), home.get("numberOfBathroomsTotal"),
            size.get("value") if size.get("unitText") == "SQM" else None,
            home.get("price") if home.get("priceCurrency") == CURRENCY else None, None,
        ))
    return rows, has_next(html)


# --- Aqarmap ---------------------------------------------------------------------------------

def flight(html):
    """The data a Next.js app-router page streams in self.__next_f.push([1, "..."]) chunks, joined."""
    return "".join(json.loads(chunk) for chunk in
                   re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html))


def parse_aqarmap(html, url):
    """One search page -> its for-sale listings, from the listing objects in the flight data. The
    price's currency is the listing's offer in the page's JSON-LD. The compound is the location level
    just below "Compounds in ..." or "Resorts", else None; Aqarmap names it "<Compound> - <Developer>",
    so the part after the last " - " is the developer. The listings carry no unit type, so it comes
    from the page asked for (/for-sale/apartment/...); a /for-sale/property-type/ page gives None.
    There is no listing date."""
    asked = re.search(r"/for-sale/([a-z-]+)/", url)
    label = asked.group(1) if asked and asked.group(1) != "property-type" else None
    payload, decoder, listings = flight(html), json.JSONDecoder(), {}
    for found in re.finditer(r'"listing":\s*\{', payload):
        listing = decoder.raw_decode(payload, found.end() - 1)[0]
        if "attributes" in listing:  # the card's full copy; its footer repeats a shorter one
            listings.setdefault(listing["id"], listing)
    if not listings:
        raise RuntimeError(f"No listings on {url}: has the site changed its pages?")
    currencies = {int(re.search(r"/listing/(\d+)-", element["item"]["url"]).group(1)):
                  (element["item"].get("offers") or {}).get("priceCurrency")
                  for block in json_ld(html) for node in block.get("@graph", []) if node.get("@type") == "ItemList"
                  for element in node.get("itemListElement", [])}
    rows = []
    for listing in listings.values():
        if (listing.get("section") or {}).get("slug") != "for-sale":
            continue
        location, attributes = listing.get("location") or {}, listing.get("attributes") or {}
        slug = location.get("slug") or ""
        slugs, names = slug.split("/"), (location.get("title_full_path") or "").split(" / ")
        compound = (next((names[i + 1] for i, s in enumerate(slugs[:-1]) if s in ("compounds", "resorts")), None)
                    if len(slugs) == len(names) else None)
        compound, _, developer = compound.rpartition(" - ") if compound and " - " in compound else (compound, "", None)
        rows.append(row(
            "aqarmap", listing["id"], f"https://aqarmap.com.eg/en/listing/{listing['id']}-{listing['slug']}",
            next((area for prefix, area in AQARMAP_AREAS.items() if slug == prefix or slug.startswith(prefix + "/")), None),
            compound, developer, label, attributes.get("rooms"), attributes.get("baths"), listing.get("area"),
            listing.get("price") if currencies.get(listing["id"]) == CURRENCY else None, None,
        ))
    return rows, has_next(html)


BROWSER_SITES = {"bayut": parse_bayut, "aqarmap": parse_aqarmap}
