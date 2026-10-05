"""Bayut Egypt and Aqarmap: open page 1 of each area in a real Chromium window and save it.

Both sites refuse plain HTTP readers, so this script is run by hand, not by Airflow:

    python fetch_bayut_aqarmap.py

It reads 50 pages (Bayut: home and six areas; Aqarmap: home and seven unit types in each of six
areas), about seven minutes. It opens a visible browser, waits 5 seconds between pages, saves every page gzipped under
data/raw/browser/<date>/ (gitignored), and prints what each page holds. If a site answers with an
error, a challenge or a CAPTCHA, the script stops reading that site: nothing here solves one.
The saved pages are what the parsers for these two sites are written from.

The area addresses below were taken from the links on the home and region pages saved on
2026-10-05; each site's home page is still saved first, so a moved address can be corrected again.
"""

import csv
import gzip
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
DELAY = 5  # seconds between pages

PAGES = {
    "bayut": [
        ("home", "https://www.bayut.eg/en/"),
        ("new-cairo", "https://www.bayut.eg/en/cairo/properties-for-sale-in-new-cairo/"),
        ("new-administrative-capital", "https://www.bayut.eg/en/cairo/properties-for-sale-in-new-capital-city/"),
        ("sheikh-zayed", "https://www.bayut.eg/en/giza/properties-for-sale-in-sheikh-zayed/"),
        ("sixth-october-city", "https://www.bayut.eg/en/giza/properties-for-sale-in-6th-of-october/"),
        ("north-coast", "https://www.bayut.eg/en/matruh/properties-for-sale-in-north-coast/"),
        ("mostakbal-city", "https://www.bayut.eg/en/cairo/properties-for-sale-in-mostakbal-city/"),
    ],
    "aqarmap": [("home", "https://aqarmap.com.eg/en/")],
}

# Aqarmap's listings carry no unit type, so its pages are read one type at a time and the parser takes
# the type from the address. The type names are the ones the saved North Coast page links to.
AQARMAP_AREAS = {
    "new-cairo": "cairo/new-cairo",
    "new-administrative-capital": "cairo/new-administrative-capital",
    "sheikh-zayed": "cairo/el-sheikh-zayed-city",
    "sixth-october-city": "cairo/6th-of-october",
    "north-coast": "north-coast",
    "mostakbal-city": "cairo/new-cairo/lmstqbl-syty",
}
AQARMAP_TYPES = ["apartment", "villa", "townhouse", "twinhouse", "penthouse", "chalet", "studio"]
PAGES["aqarmap"] += [(f"{area}-{kind}", f"https://aqarmap.com.eg/en/for-sale/{kind}/{path}/")
                     for area, path in AQARMAP_AREAS.items() for kind in AQARMAP_TYPES]

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


def main():
    out = ROOT / "data" / "raw" / "browser" / datetime.now(timezone.utc).date().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        for source, pages in PAGES.items():
            for name, url in pages:
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    page.wait_for_timeout(3_000)  # let the page finish drawing its listings
                    html, title, text = page.content(), page.title(), page.inner_text("body")
                except Exception as error:  # one page failing must not lose the others
                    row = {"source": source, "page": name, "url": url, "error": repr(error)[:300]}
                    rows.append(row)
                    print(row)
                    time.sleep(DELAY)
                    continue
                status = response.status if response else None
                (out / f"{source}-{name}.html.gz").write_bytes(gzip.compress(html.encode("utf-8")))
                # 401, 403 and 429 are the site refusing; a 404 only means the guessed address is wrong.
                blocked = (status in (None, 401, 403, 429) or bool(BLOCKED.search(title))
                           or (len(text) < 3_000 and bool(BLOCKED.search(text))))
                row = {"source": source, "page": name, "url": url, "final_url": page.url, "status": status,
                       "title": title[:80], "bytes": len(html), "blocked": blocked, **what_it_holds(html)}
                rows.append(row)
                print(row)
                time.sleep(DELAY)
                if blocked:
                    print(f"{source}: stopped at {url} (status {status}, title {title[:60]!r})")
                    break
        browser.close()
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{sum('error' not in row for row in rows)} of {len(rows)} pages saved in {out}. Tell Claude it ran; the parsers are written from these pages.")


if __name__ == "__main__":
    main()
