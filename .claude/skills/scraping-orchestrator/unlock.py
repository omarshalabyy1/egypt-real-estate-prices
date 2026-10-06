"""Open a visible Chromium on a saved profile so Omar can solve a CAPTCHA, log in and accept
cookie banners once. Scrapers then reuse the session headless.

    python unlock.py <url> <site>

Saves the browser profile in ~/.scraping-profiles/<site>/ and session.json there (cookies + user agent).
    Playwright:         p.chromium.launch_persistent_context(<profile>, headless=True)
    requests/curl_cffi: send session.json's cookies and user_agent
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

url, site = sys.argv[1], sys.argv[2]
profile = Path.home() / ".scraping-profiles" / site
profile.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(profile, headless=False)
    page = browser.pages[0]
    page.goto(url, timeout=60000)
    input("Solve the CAPTCHA, log in and accept cookies in the browser window, then press Enter here.\n")
    session = {"user_agent": page.evaluate("navigator.userAgent"), "cookies": browser.cookies()}
    (profile / "session.json").write_text(json.dumps(session), encoding="utf-8")
    browser.close()
print(f"Saved {profile / 'session.json'} ({len(session['cookies'])} cookies)")
