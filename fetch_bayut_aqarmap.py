"""Bayut Egypt and Aqarmap: open page 1 of each area in a real Chromium window and save it.

Both sites refuse plain HTTP readers, so this script is run by hand, not by Airflow:

    python fetch_bayut_aqarmap.py

It reads each site's home page, then Bayut's page and Aqarmap's seven unit types for every area in
config/client.yaml (the demo's six areas: 50 pages, about seven minutes). It opens a visible browser, waits each
site's pace_seconds between pages, saves every page gzipped under
data/raw/<source>/<run_week>/ (gitignored; run_week is the Sunday on or before today in schedule.timezone), with a
summary.csv line per page and a _done file when the site is finished, and prints what each page holds.
Run it before the weekly Airflow run: load_silver reads these folders.

The browser keeps its profile (cookies, accepted banners, logins) in .browser-profile/ (gitignored,
never committed), so what you accept or log into stays for the next run. On the first run it waits
on each site's home page so you can accept cookies or log in. If a page shows a check, a CAPTCHA, a
login wall or a 401, 403 or 429, it waits for you to deal with it in the browser window and press
Enter, then loads the page once more; if it is still blocked, it stops reading that site. The script
never solves anything itself.

The area addresses are in config/client.yaml (each area's bayut page and aqarmap path); the demo's were
taken from the links on the home and region pages saved on 2026-10-05. Each site's home page is still saved
first, so a moved address can be corrected again.
"""

import csv
import gzip
import json
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from config import ROOT, load_config

CFG = load_config()
PACE = {s["id"]: s["pace_seconds"] for s in CFG["sites"]}  # seconds between pages, per site
PROFILE = ROOT / ".browser-profile"  # cookies and logins kept between runs; gitignored

# Aqarmap's listings carry no unit type, so its pages are read one type at a time and the parser takes
# the type from the address. The type names are the ones the site's saved search pages link to.
AQARMAP_TYPES = ["apartment", "villa", "townhouse", "twinhouse", "penthouse", "chalet", "studio"]
PAGES = {  # source: [(page name, area_id, address)]; a home page has no area and is not parsed
    "bayut": [("home", "", "https://www.bayut.eg/en/")]
             + [(a["id"], a["id"], a["sites"]["bayut"]["page"]) for a in CFG["areas"] if "bayut" in a["sites"]],
    "aqarmap": [("home", "", "https://aqarmap.com.eg/en/")]
               + [(f"{a['id']}-{kind}", a["id"], f"https://aqarmap.com.eg/en/for-sale/{kind}/{a['sites']['aqarmap']['path']}/")
                  for a in CFG["areas"] if "aqarmap" in a["sites"] for kind in AQARMAP_TYPES],
}
PAGES = {source: pages for source, pages in PAGES.items() if source in PACE}  # only the sites in the config

# Words a challenge or block page puts in its title or its (short) text. Normal listing pages can
# mention "captcha" in their scripts, so only the title and short pages are searched.
BLOCKED = re.compile(r"just a moment|captcha|verify you are human|are you a robot|access denied|request blocked", re.I)


def what_it_holds(html):
    """Which data blocks the page carries, so the parser can read the cheapest one."""
    info = {
        "next_data": '<script id="__NEXT_DATA__"' in html,
        "window_state": "window.state = " in html,
        "json_ld_blocks": html.count("application/ld+json"),
        "listings_in_state": None,
    }
    if info["window_state"]:
        try:
            state, _ = json.JSONDecoder().raw_decode(html, html.index("window.state = ") + len("window.state = "))
            info["listings_in_state"] = len(state["algolia"]["content"]["hits"])
        except (ValueError, KeyError, TypeError):
            pass
    return info


def load(page, url):
    """Open one address -> (status, html, title, blocked)."""
    response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(3_000)  # let the page finish drawing its listings
    html, title, text = page.content(), page.title(), page.inner_text("body")
    status = response.status if response else None
    # 401, 403 and 429 are the site refusing; a 404 only means the guessed address is wrong.
    blocked = (status in (None, 401, 403, 429) or bool(BLOCKED.search(title))
               or (len(text) < 3_000 and bool(BLOCKED.search(text))))
    return status, html, title, blocked


def main():
    today = datetime.now(ZoneInfo(CFG["schedule"]["timezone"])).date()  # the DAG's run week is in this zone too
    run_week = today - timedelta(days=(today.weekday() + 1) % 7)  # the Sunday on or before today
    first_run = not PROFILE.exists()
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(str(PROFILE), headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        for source, pages in PAGES.items():
            out = ROOT / "data" / "raw" / source / run_week.isoformat()
            out.mkdir(parents=True, exist_ok=True)
            rows = []
            for name, area_id, url in pages:
                try:
                    status, html, title, blocked = load(page, url)
                    if blocked or (first_run and name == "home"):
                        input(f"{source}: {title[:60]!r} (status {status}). In the browser window, deal with any "
                              "check, cookie banner or login, then press Enter here to go on... ")
                        status, html, title, blocked = load(page, url)
                except Exception as error:  # one page failing must not lose the others
                    row = {"page": name, "area_id": area_id, "url": url, "error": repr(error)[:300]}
                    rows.append(row)
                    print(source, row)
                    time.sleep(PACE[source])
                    continue
                (out / f"{name}.html.gz").write_bytes(gzip.compress(html.encode("utf-8")))
                row = {"page": name, "area_id": area_id, "url": url, "final_url": page.url,
                       "fetched_at": datetime.now(timezone.utc).isoformat(), "http_status": status,
                       "bytes": len(html), "path": f"{name}.html.gz", "title": title[:80], "blocked": blocked,
                       **what_it_holds(html)}
                rows.append(row)
                print(source, row)
                time.sleep(PACE[source])
                if blocked:  # still blocked after you had your turn in the window
                    print(f"{source}: stopped at {url} (status {status}, title {title[:60]!r})")
                    break
            with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
                writer.writeheader()
                writer.writerows(rows)
            (out / "_done").write_text(f"{datetime.now(timezone.utc).isoformat()}\n")
            print(f"{source}: {sum('error' not in row for row in rows)} of {len(rows)} pages saved in {out}")
        browser.close()


if __name__ == "__main__":
    main()
