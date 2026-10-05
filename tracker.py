"""The weekly steps Airflow runs, one function each, all for one run week (the Sunday its week starts):

- extract(source, run_week): bronze. Read one site's search pages for our six areas and keep every page
  under data/raw/<source>/<run_week>/ with an index.csv line per page read; realestate.eg also reads
  each residential unit's page. A folder with a _done file is a finished week and is skipped (the
  watermark is the run week). A page already on disk is not read again, so a retried task resumes.
- load_silver(run_week): silver. Parse every source's bronze for the week, check each row, save the
  good rows, quarantine the rest and log the counts per site and area, in one transaction.
- build_gold(run_week): gold. Rebuild the star for the week.
- report(run_week): print the week's price cuts and the widest gaps."""

import csv
import gzip
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import psycopg
import requests
from bs4 import BeautifulSoup
from psycopg.types.json import Jsonb

import browser_sites
import sites

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
SITE = "https://realestate.eg"
USER_AGENT = sites.USER_AGENT
DELAY = 2.5  # seconds between any two requests
ROWS_PER_SEARCH = 150  # a search's pages are read until this many residential rows in our areas...
# ...or the search's max_pages in data/site_areas.csv, or its last page, whichever comes first.
SOURCES = ["realestate", "propertyfinder", "dubizzle", "nawy", "bayut", "aqarmap"]
BROWSER = {"bayut", "aqarmap"}  # read by Omar's browser run (fetch_bayut_aqarmap.py), not by Airflow
PRICE_PER_M2_MIN, PRICE_PER_M2_MAX = 10_000, 400_000  # EGP: a row priced per m² outside this band is quarantined
OUTSIDE_BAND = f"price per m² outside {PRICE_PER_M2_MIN:,} to {PRICE_PER_M2_MAX:,}"
with open(ROOT / "data" / "areas.csv", newline="", encoding="utf-8") as f:
    AREAS = [r["area_id"] for r in csv.DictReader(f)]

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
    """The Sunday on or before the day."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def folder(source, run_week):
    return RAW / source / run_week.isoformat()


def gunzip(path):
    return gzip.decompress(path.read_bytes())


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- realestate.eg pages ---------------------------------------------------------------------------

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


def page_name(url):
    """A realestate.eg page's file name: '<area>-page-<n>' for an index page, the listing id for a unit."""
    index = re.search(r"/listings/([^/?]+)\?.*page=(\d+)", url)
    return f"{index.group(1)}-page-{index.group(2)}" if index else re.match(r"/en/(\d+)-", urlparse(url).path).group(1)


# --- Bronze: extract ---------------------------------------------------------------------------------

def log(out, url, final_url, fetched_at, status, size, path):
    """One line per page read in the folder's index.csv."""
    new = not (out / "index.csv").exists()
    with open(out / "index.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new:
            writer.writerow(["url", "final_url", "fetched_at", "http_status", "bytes", "path"])
        writer.writerow([url, final_url, fetched_at.isoformat(), status, size, path])


def keep(path, data):
    """Write a page gzipped, all or nothing."""
    part = path.with_suffix(".part")
    part.write_bytes(gzip.compress(data))
    part.replace(path)


def read_robots():
    """robots.txt, read with our User-Agent: the site answers Python's default one with 403, which
    RobotFileParser.read() would take as "nothing allowed"."""
    robots = RobotFileParser()
    robots.parse(http.get(f"{SITE}/robots.txt", timeout=60).text.splitlines())
    time.sleep(DELAY)
    return robots


def fetch(robots, out, url):
    """One realestate.eg page as robots.txt allows: from disk when this week already has it, else read,
    kept and logged, then a wait of DELAY seconds. A page answering an error is kept as it came."""
    path = out / f"{page_name(url)}.html.gz"
    if path.exists():
        return gunzip(path)
    if not robots.can_fetch(USER_AGENT, url):
        raise RuntimeError(f"robots.txt does not allow {url}")
    response = http.get(url, timeout=60)
    fetched_at = datetime.now(timezone.utc)
    keep(path, response.content)
    log(out, url, response.url, fetched_at, response.status_code, len(response.content), path.name)
    time.sleep(DELAY)
    return response.content


def read_realestate(robots, search, out):
    """An area's index pages until ROWS_PER_SEARCH residential unit cards in our areas, then each of
    those cards' unit pages. Canary: page 1's cards must give at least one priced unit page."""
    cards = []
    for page in range(1, search["max_pages"] + 1):
        url = search["url_template"].format(page=page)
        page_cards, has_next = parse_index(fetch(robots, out, url), url)
        cards += [(page, c) for c in page_cards if not c["is_project"] and c["listing_id"]
                  and c["area_id"] in AREAS and sites.unit_type(c["unit_type"]) in sites.RESIDENTIAL]
        if not has_next or len(cards) >= ROWS_PER_SEARCH:
            break
    priced = False
    for page, card in cards:
        html = fetch(robots, out, card["url"])
        priced = priced or (page == 1 and bool((parse_unit(html, card["url"]) or {}).get("asking_price")))
    if not priced:
        raise RuntimeError(f"Canary: page 1 of {search['url_template']} gave no priced unit")


def read_search(source, search, out):
    """A search's pages until ROWS_PER_SEARCH residential rows in our areas. Only the page's JSON block
    is kept, with its contact fields already removed. Canary: page 1 must give a priced row."""
    extract_block, parse = sites.SITES[source]
    kept = 0
    for page in range(1, search["max_pages"] + 1):
        url = search["url_template"].format(page=page)
        path = out / f"{search['area_id']}-{search['search']}-page-{page}.json.gz"
        if path.exists():
            block = json.loads(gunzip(path))
        else:
            response = sites.get(url)
            fetched_at = datetime.now(timezone.utc)
            block = extract_block(response.content.decode("utf-8"), url)
            keep(path, json.dumps(block, ensure_ascii=False).encode("utf-8"))
            log(out, url, response.url, fetched_at, response.status_code, len(response.content), path.name)
        rows, has_next = parse(block, url)
        if page == 1 and not any(r["asking_price"] for r in rows):
            raise RuntimeError(f"Canary: page 1 of {url} gave no priced row")
        kept += sum(r["area_id"] in AREAS and r["unit_type"] in sites.RESIDENTIAL for r in rows)
        if not has_next or kept >= ROWS_PER_SEARCH:
            break


def extract(source, run_week):
    """Bronze for one site and run week. Skipped when the folder already has _done."""
    out = folder(source, run_week)
    if (out / "_done").exists():
        print(f"{source} {run_week}: already extracted, skipped ({out / '_done'})")
        return
    out.mkdir(parents=True, exist_ok=True)
    robots = read_robots() if source == "realestate" else None
    for search in (s for s in sites.SEARCHES if s["source"] == source):
        if source == "realestate":
            read_realestate(robots, search, out)
        else:
            read_search(source, search, out)
    (out / "_done").write_text(f"{datetime.now(timezone.utc).isoformat()}\n")
    print(f"{source} {run_week}: {len(read_csv(out / 'index.csv'))} pages read")


# --- Silver: parse bronze, check, save ------------------------------------------------------------

def last_read(out, file):
    """url -> its last line in the folder's index or summary file (the page on disk is the last one read)."""
    return {r["url"]: r for r in read_csv(out / file)} if (out / file).exists() else {}


def realestate_parts(out):
    """area -> pages read, stated total, rows (with fetched_at) and page problems, from the saved pages.
    Each card is one row; project cards get the label "Project" so they are skipped."""
    reads, units, parts = last_read(out, "index.csv"), {}, {}
    for search in (s for s in sites.SEARCHES if s["source"] == "realestate"):
        part = parts[search["area_id"]] = {"pages": [], "stated_total": None, "rows": [], "problems": {}}
        for page in range(1, search["max_pages"] + 1):
            url = search["url_template"].format(page=page)
            path = out / f"{page_name(url)}.html.gz"
            if not path.exists():
                break
            html = gunzip(path)
            part["pages"].append(path.name)
            if page == 1:
                total = re.search(rb"of\s*<strong>([\d,]+)</strong>\s*results", html)
                part["stated_total"] = int(total.group(1).replace(b",", b"")) if total else None
            for card in parse_index(html, url)[0]:
                listing_id, unit, fetched_at = card["listing_id"], None, reads[url]["fetched_at"]
                key = ("realestate", str(listing_id))
                unit_path = out / f"{listing_id}.html.gz"
                if card["is_project"]:
                    pass
                elif listing_id is None:
                    part["problems"][key] = "unparseable id"
                elif not unit_path.exists():
                    part["problems"][key] = "unit page not read"
                else:
                    part["pages"].append(unit_path.name)
                    read = reads.get(card["url"], {})
                    fetched_at = read.get("fetched_at", fetched_at)
                    if listing_id not in units:
                        units[listing_id] = parse_unit(gunzip(unit_path), card["url"])
                    unit = units[listing_id]
                    if read.get("http_status") not in (None, "200"):
                        part["problems"][key] = f"http {read['http_status']}"
                    elif unit is None:
                        part["problems"][key] = "no JSON-LD"
                unit = unit or {}
                row = sites.row("realestate", listing_id, card["url"], card["area_id"],
                                unit.get("compound") or card["compound"], unit.get("developer"),
                                "Project" if card["is_project"] else card["unit_type"],
                                unit.get("bedrooms") or card["bedrooms"], unit.get("bathrooms") or card["bathrooms"],
                                unit.get("size_m2") or card["size_m2"], unit.get("asking_price"), None)
                part["rows"].append({**row, "fetched_at": fetched_at})
    return parts


def json_site_parts(source, out):
    """area -> pages read, stated total (summed over the area's searches) and rows, from the kept JSON."""
    reads, parts = last_read(out, "index.csv"), {}
    extract_block, parse = sites.SITES[source]
    for search in (s for s in sites.SEARCHES if s["source"] == source):
        part = parts.setdefault(search["area_id"], {"pages": [], "stated_total": None, "rows": [], "problems": {}})
        for page in range(1, search["max_pages"] + 1):
            url = search["url_template"].format(page=page)
            path = out / f"{search['area_id']}-{search['search']}-page-{page}.json.gz"
            if not path.exists():
                break
            block = json.loads(gunzip(path))
            part["pages"].append(path.name)
            if page == 1 and sites.stated_total(source, block) is not None:
                part["stated_total"] = (part["stated_total"] or 0) + sites.stated_total(source, block)
            part["rows"] += [{**r, "fetched_at": reads[url]["fetched_at"]} for r in parse(block, url)[0]]
    return parts


def browser_parts(source, out):
    """area -> pages read, stated total and rows, from the pages Omar's browser run saved. A page whose
    title says it holds 0 listings gives no rows; any other page without listings fails loudly."""
    parts = {}
    for page in read_csv(out / "summary.csv"):
        if not page["area_id"] or page["http_status"] != "200" or page["blocked"] == "True":
            continue
        part = parts.setdefault(page["area_id"], {"pages": [], "stated_total": None, "rows": [], "problems": {}})
        html = gunzip(out / page["path"]).decode("utf-8")
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        total = re.search(r"(\d[\d,]*) [A-Za-z ]*?for sale", title.group(1) if title else "", re.I)
        total = int(total.group(1).replace(",", "")) if total else None
        part["pages"].append(page["path"])
        if total is not None:
            part["stated_total"] = (part["stated_total"] or 0) + total
        if total == 0:
            continue
        rows, _ = browser_sites.BROWSER_SITES[source](html, page["url"])
        part["rows"] += [{**r, "fetched_at": page["fetched_at"]} for r in rows]
    return parts


def reconcile(counts, where):
    """Every row parsed is skipped, a duplicate, saved or quarantined, exactly once; else the run fails."""
    if counts["parsed"] != counts["skipped"] + counts["duplicate"] + counts["saved"] + counts["quarantined"]:
        raise RuntimeError(f"{where}: counts do not reconcile: {dict(counts)}")


def check(rows, seen, problems, typed=frozenset()):
    """One area's rows -> (counts, rows to save, (reason, row) to quarantine). A row outside our six
    areas or of a non-residential type is skipped; a listing already read this run (seen), or a row
    without a unit type whose listing the run also read with one (typed), is a duplicate; then a page
    problem, an unknown type, a missing price or size, or a price per m² outside the band quarantines it."""
    counts, saved, rejected = Counter(parsed=len(rows)), [], []
    for r in rows:
        key = (r["source"], r["source_listing_id"])
        if r["area_id"] not in AREAS or r["unit_type"] in sites.NON_RESIDENTIAL:
            counts["skipped"] += 1
            continue
        if key in seen or (r["unit_type"] is None and key in typed):
            counts["duplicate"] += 1
            continue
        seen.add(key)
        reason = (problems.get(key) or ("unknown type" if r["unit_type"] not in sites.RESIDENTIAL else None)
                  or ("price missing or <= 0" if not r["asking_price"] else None)
                  or ("size missing or <= 0" if not r["size_m2"] else None)
                  or (OUTSIDE_BAND if not PRICE_PER_M2_MIN * r["size_m2"] <= r["asking_price"]
                      <= PRICE_PER_M2_MAX * r["size_m2"] else None))
        if reason:
            counts["quarantined"] += 1
            rejected.append((reason, r))
        else:
            counts["saved"] += 1
            saved.append(r)
    return counts, saved, rejected


def load_reference(conn):
    """The areas (upserted) and our units (replaced) from data/."""
    areas = read_csv(ROOT / "data" / "areas.csv")
    conn.cursor().executemany(
        "INSERT INTO silver.area (area_id, name, lat, lon, coordinate_source) VALUES (%(area_id)s, %(name)s,"
        " %(lat)s, %(lon)s, %(coordinate_source)s) ON CONFLICT (area_id) DO UPDATE SET name = EXCLUDED.name,"
        " lat = EXCLUDED.lat, lon = EXCLUDED.lon, coordinate_source = EXCLUDED.coordinate_source",
        [{k: v or None for k, v in a.items()} for a in areas])
    units = read_csv(ROOT / "data" / "our_units.csv")
    conn.execute("DELETE FROM silver.our_unit")
    conn.cursor().executemany(
        "INSERT INTO silver.our_unit (unit_code, area_id, compound, developer, unit_type, bedrooms, size_m2,"
        " asking_price) VALUES (%(unit_code)s, %(area_id)s, %(compound)s, %(developer)s, %(unit_type)s,"
        " %(bedrooms)s, %(size_m2)s, %(asking_price)s)",
        [{**u, "developer": u.get("developer") or None} for u in units])
    print(f"silver.area: {len(areas)} rows, silver.our_unit: {len(units)} rows")


def load_fetch_log(conn, run_week):
    """Every page read this week, from each folder's index.csv or summary.csv. A browser page that
    never answered (an error line, no fetched_at) was not read and is not logged."""
    rows = []
    for source in SOURCES:
        out = folder(source, run_week)
        for file in ("index.csv", "summary.csv"):
            for r in read_csv(out / file) if (out / file).exists() else []:
                if not r.get("fetched_at"):
                    continue
                rows.append({"source": source, "run_week": run_week, "url": r["url"],
                             "final_url": r.get("final_url") or None, "fetched_at": r["fetched_at"],
                             "http_status": r.get("http_status") or None, "bytes": r.get("bytes") or None,
                             "path": r.get("path") or f"{page_name(r['url'])}.html.gz"})
    conn.cursor().executemany(
        "INSERT INTO bronze.fetch_log VALUES (%(source)s, %(run_week)s, %(url)s, %(final_url)s, %(fetched_at)s,"
        " %(http_status)s, %(bytes)s, %(path)s) ON CONFLICT DO NOTHING", rows)
    print(f"bronze.fetch_log: {len(rows)} pages read this week")


def save(conn, run_week, source, area_id, part, counts, saved, rejected):
    pages = list(dict.fromkeys(part["pages"]))  # a unit page shared by two cards is one page
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO silver.listing (source, listing_id, url, area_id, compound, developer, unit_type, bedrooms,"
        " bathrooms, size_m2, listed_on, first_seen_week, last_seen_week) VALUES (%(source)s,"
        " %(source_listing_id)s, %(url)s, %(area_id)s, %(compound)s, %(developer)s, %(unit_type)s, %(bedrooms)s,"
        " %(bathrooms)s, %(size_m2)s, %(listed_on)s, %(run_week)s, %(run_week)s) ON CONFLICT (source, listing_id)"
        " DO UPDATE SET url = EXCLUDED.url, area_id = EXCLUDED.area_id, compound = EXCLUDED.compound,"
        " developer = EXCLUDED.developer, unit_type = EXCLUDED.unit_type, bedrooms = EXCLUDED.bedrooms,"
        " bathrooms = EXCLUDED.bathrooms, size_m2 = EXCLUDED.size_m2, listed_on = EXCLUDED.listed_on,"
        " first_seen_week = least(listing.first_seen_week, EXCLUDED.first_seen_week),"
        " last_seen_week = greatest(listing.last_seen_week, EXCLUDED.last_seen_week)",
        [{**r, "run_week": run_week} for r in saved])
    cur.executemany(
        "INSERT INTO silver.price_observation (source, listing_id, run_week, asking_price, size_m2, fetched_at)"
        " VALUES (%(source)s, %(source_listing_id)s, %(run_week)s, %(asking_price)s, %(size_m2)s, %(fetched_at)s)"
        " ON CONFLICT DO NOTHING",
        [{**r, "run_week": run_week} for r in saved])
    cur.executemany(
        "INSERT INTO silver.quarantine (run_week, source, url, reason, payload) VALUES (%s, %s, %s, %s, %s)"
        " ON CONFLICT DO NOTHING",
        [(run_week, source, r["url"] or f"{source}:{r['source_listing_id']}", reason,
          Jsonb(r, dumps=lambda o: json.dumps(o, default=str))) for reason, r in rejected])
    cur.execute(
        "INSERT INTO silver.run_log VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (source, area_id,"
        " run_week) DO UPDATE SET pages_read = EXCLUDED.pages_read, pages_used = EXCLUDED.pages_used, stated_total = EXCLUDED.stated_total,"
        " rows_parsed = EXCLUDED.rows_parsed, rows_skipped = EXCLUDED.rows_skipped,"
        " rows_duplicate = EXCLUDED.rows_duplicate, rows_saved = EXCLUDED.rows_saved,"
        " rows_quarantined = EXCLUDED.rows_quarantined",
        (source, area_id, run_week, len(pages), pages, part["stated_total"], counts["parsed"], counts["skipped"],
         counts["duplicate"], counts["saved"], counts["quarantined"]))


def check_saved(conn, run_week, keys):
    """Every listing this load saved has its price for the week in silver. Prices are append-only, so the
    week may also hold prices an earlier load of it saved."""
    held = set(conn.execute("SELECT source, listing_id FROM silver.price_observation WHERE run_week = %s",
                            (run_week,)).fetchall())
    if missing := keys - held:
        raise RuntimeError(f"{len(missing)} prices saved for {run_week} are not in silver, e.g. {sorted(missing)[:3]}")


def load_silver(run_week):
    """Parse every source's bronze for the week and load silver in one transaction. A site Airflow reads
    without _done fails the run; a browser site's folder is used when Omar's run has finished it."""
    with connect() as conn:
        conn.execute((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    with connect() as conn:
        load_reference(conn)
        load_fetch_log(conn, run_week)
        # The week's quarantine is derived from its bronze: a reload replaces it. Prices are only ever added.
        conn.execute("DELETE FROM silver.quarantine WHERE run_week = %s", (run_week,))
        seen, total, saved_keys, parsed = set(), Counter(), set(), {}
        for source in SOURCES:
            out = folder(source, run_week)
            if not (out / "_done").exists():
                if source in BROWSER and not out.exists():
                    print(f"{source} {run_week}: no pages saved by the browser run, nothing to load")
                    continue
                raise RuntimeError(f"{out} has no _done: its extract did not finish")
            parsed[source] = (realestate_parts(out) if source == "realestate" else browser_parts(source, out)
                              if source in BROWSER else json_site_parts(source, out))
        # A listing read with a unit type and also without one keeps the typed row, whatever the parse order.
        typed = {(r["source"], r["source_listing_id"]) for parts in parsed.values() for part in parts.values()
                 for r in part["rows"] if r["unit_type"] is not None}
        for source, parts in parsed.items():
            for area_id, part in parts.items():
                counts, saved, rejected = check(part["rows"], seen, part["problems"], typed)
                reconcile(counts, f"{source} {area_id}")
                save(conn, run_week, source, area_id, part, counts, saved, rejected)
                saved_keys |= {(r["source"], r["source_listing_id"]) for r in saved}
                total += counts
                print(f"{source} {area_id}: {len(set(part['pages']))} pages, {dict(counts)}")
        reconcile(total, "all sources")
        check_saved(conn, run_week, saved_keys)
        quarantined = conn.execute("SELECT count(*) FROM silver.quarantine WHERE run_week = %s", (run_week,)).fetchone()[0]
        if quarantined != total["quarantined"]:
            raise RuntimeError(f"The warehouse holds {quarantined} quarantined rows for {run_week}, the run counted"
                               f" {total['quarantined']}")
        if not total["saved"]:
            raise RuntimeError(f"No asking price saved for {run_week}")
        print(f"{run_week}: {dict(total)}")


# --- Gold and report -----------------------------------------------------------------------------

def build_gold(run_week, conn=None):
    """Rebuild the star for the week in one transaction; its fact rows must match silver's prices."""
    own = conn is None
    conn = conn or connect()
    try:
        conn.execute("SELECT gold.build(%s)", (run_week,))
        facts, prices = conn.execute(
            "SELECT (SELECT count(*) FROM gold.fact_listing_price WHERE week_key = %(w)s),"
            " (SELECT count(*) FROM silver.price_observation WHERE run_week = %(w)s)", {"w": run_week}).fetchone()
        if facts != prices:
            raise RuntimeError(f"gold holds {facts} prices for {run_week}, silver {prices}")
        if own:
            conn.commit()
        print(f"gold {run_week}: {facts} listing prices")
    finally:
        if own:
            conn.close()


def report(run_week):
    """Print the week's competitor price cuts and the areas ranked by our units' gap to the market."""
    with connect() as conn:
        cuts = conn.execute(
            "SELECT s.source, c.listing_id, a.name, d.compound, t.unit_type, c.old_price_per_m2, c.new_price_per_m2,"
            " c.change_pct FROM gold.price_change c JOIN gold.dim_site s USING (site_key)"
            " JOIN gold.dim_area a USING (area_key) JOIN gold.dim_compound d USING (compound_key)"
            " JOIN gold.dim_property_type t USING (type_key) WHERE c.week_key = %s AND c.is_cut"
            " ORDER BY c.change_pct", (run_week,)).fetchall()
        print(f"Week of {run_week}: {len(cuts)} competitor price cuts per m2")
        for source, listing_id, area, compound, unit_type, old, new, pct in cuts:
            print(f"- {source} {listing_id} {unit_type} in {compound} ({area}): {old} -> {new} EGP/m2 ({pct}%)")
        print("Areas by the median gap of our units to the market, widest first:")
        for rank, area, median, cheaper, compared in conn.execute(
            "SELECT g.gap_rank, a.name, g.median_gap_pct, g.pct_listings_cheaper, g.units_compared"
            " FROM gold.area_gap g JOIN gold.dim_area a USING (area_key) ORDER BY g.gap_rank").fetchall():
            print(f"{rank}. {area}: {median}% median gap over {compared} units; {cheaper}% of listings ask less per m2")
