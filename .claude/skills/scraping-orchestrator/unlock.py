"""Open a visible stealth browser on a saved profile so Omar can solve a CAPTCHA, log in
and accept cookie banners once. Scrapers then reuse the profile headless.

    python unlock.py <url> <site>

Profile: ~/.scraping-profiles/<site>. In the scraper:
    StealthyFetcher.fetch(url, headless=True, user_data_dir=<that path>)
"""
import sys
from pathlib import Path

from scrapling.fetchers import StealthyFetcher

url, site = sys.argv[1], sys.argv[2]
profile = Path.home() / ".scraping-profiles" / site
profile.mkdir(parents=True, exist_ok=True)


def wait_for_omar(page):
    input(f"Solve the CAPTCHA, log in and accept cookies in the browser window, then press Enter here.\nProfile: {profile}\n")


StealthyFetcher.fetch(url, headless=False, user_data_dir=str(profile), page_action=wait_for_omar, timeout=0)
print(f"Saved. Reuse with user_data_dir={str(profile)!r}")
