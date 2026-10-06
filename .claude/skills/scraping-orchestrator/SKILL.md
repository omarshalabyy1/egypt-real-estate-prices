---
name: scraping-orchestrator
description: Entry point for ANY scraping job (scrape, crawl, extract listings, prices, hidden API, 403/429, blocked, Cloudflare, CAPTCHA, login wall, cookies, "سكرب", "اسحب البيانات"), and for any project that scrapes. Builds with requests, curl_cffi and Playwright by default, and routes each step to the installed skill or file it needs - scraping, web-scraping, playwright-skill, with scrapling, scrapling-fetcher and crawl4ai as measured fallbacks only. Use it first, before any of those six.
---

# Scraping orchestrator

Route each step to the one skill or file it needs (skills in `~/.claude/skills/<name>/`; where a row names a file, `Read` only that file). Stop at the first step that gets the data.

**Tools, in order:** `requests` → `curl_cffi` (`impersonate="chrome"`) → Playwright. Scrapling and crawl4ai only when Playwright is measured blocked, recorded in the site notes.

## 1. Start from what is known

Read `~/.scraping-profiles/<site>/notes.md` if it exists (rung that worked, rate limit, selectors, the site's own item count, each dated). Start at that rung and re-check with one request; old notes are a hypothesis. After every job, update it in a few lines (create it if missing).

## 2. Route

| Step | Load / read | Use it for |
|---|---|---|
| Plan | Skill `scraping` | Size the job (one page = ten-line script, recurring = Airflow task) and what "complete" means. Always first. |
| Probe | `scraping/scripts/probe.py <url> --out probe_out` | A dozen requests: data in HTML or embedded JSON, JS shell, who is in front, sitemaps, WordPress totals. |
| Hidden API | Built-in browser `read_network_requests`; `web-scraping/strategies/api-discovery.md`, `traffic-interception.md` | JS shell: find the JSON call and call it with `requests` / `curl_cffi`. Best path when it exists. |
| Sitemap or list | `web-scraping/strategies/sitemap-discovery.md`, `scraping/reference/recipes.md` | URL list from the sitemap, CMS API or `__NEXT_DATA__`. |
| HTML pages | `requests`, then `curl_cffi` on 401 / 403 / timeout; BeautifulSoup | Default for pages. `requests` first: some sites block `curl_cffi` but not `requests`. |
| JS pages, clicks, forms | Playwright, headless Chromium (skill `playwright-skill`) | `domcontentloaded`, then `networkidle` capped at ~10 s; clicks, filters, infinite scroll with no API behind. |
| Blocked | Force ladder below; `scraping/reference/transport.md`, `web-scraping/strategies/anti-blocking.md` | Never stop at the first refusal. |
| Check | `scraping/reference/validation.md` | Counts at every stage against the site's own total, empty fields, duplicates. Before anything is reported. |

Prefer API, then sitemap or list, then pages; move to a heavier tool only when the lighter one fails on a measurement.

| Signal (probe, response or browser) | Go to |
|---|---|
| `__NEXT_DATA__`, `window.__INITIAL_STATE__`, `application/ld+json` | Parse the embedded JSON, skip the HTML |
| Near-empty shell, data only after JavaScript | Hidden API |
| WordPress (`/wp-json/`, `x-wp-total`) | REST API with `per_page=100` |
| Data in the HTML, 200 | HTML pages |
| `cf-mitigated: challenge`, "Just a moment", 403 from Cloudflare / Akamai / DataDome | Ladder rung 3 (a JS check, not a CAPTCHA) |
| 429 or `Retry-After` | Wait it out, drop concurrency one level, resume |
| CAPTCHA, login or cookie wall | Ladder rung 5 |
| 200 but zero items, or a small round count | Wrong page or soft block: compare with the visible page |

## 3. Plan, then build

Write about ten lines, show Omar (no approval needed, he can redirect), save in the site notes or the project's `docs/`: goal and the site's count to match; pages, fields, selectors or JSON keys; URL source and count; tool and rung with the test numbers; speed (pages/min, total time); one-off or Airflow task; storage (raw kept, then clean table); checks; what will break and the fallback.

Run it: one `requests.Session` or async `curl_cffi` for APIs and pages; one Playwright browser kept open for the whole run with ~8 pages via `asyncio.gather` (reopening per batch halved throughput; more tabs slowed this laptop). Backoff on 429, no fixed delays. Resumable JSONL state (`scraping/scripts/runner_template.py`) only for a few hundred pages or more.

## 4. Force ladder

Read the saved refusal body first (`probe_out/`), then climb one rung at a time:

1. `requests`.
2. `curl_cffi`, `impersonate="chrome"`.
3. Playwright headless; then visible Chromium or `channel="chrome"`.
4. Fallback, only after rung 3 is measured blocked. Test two on the same page (status, items vs the visible page, fields, seconds), pick on the numbers, write the verdict in the notes:
   - Scrapling `StealthyFetcher.fetch(url, headless=True, network_idle=True, solve_cloudflare=False)`, then `real_chrome=True` (skills `scrapling-fetcher` templates, `scrapling`). Jumia 2026-10-05: `curl_cffi` 403, Scrapling 200 with 40/40 prices; Playwright was not tested there.
   - crawl4ai with `crawl4ai/references/anti-detection.md` (its stealth lost to Cloudflare on Jumia, 0 items).
   - Keep `solve_cloudflare=False`, also in a copied `stealth_cloudflare.py` (ships `True`). If a Scrapling browser will not launch, run `scrapling install` once.
5. CAPTCHA, login or cookie wall: Omar runs `python ~/.claude/skills/scraping-orchestrator/unlock.py <url> <site>` in his terminal (Claude can start it with `mcp__terminal__run_in_terminal`; the Bash tool has no stdin). He passes the check in the visible window and presses Enter. The profile stays in `~/.scraping-profiles/<site>/` with `session.json` (cookies + user agent): Playwright reuses the profile headless (`launch_persistent_context`), `requests` / `curl_cffi` send those cookies and that user agent. For Airflow, copy `session.json` to `data/cookies/<site>.json` (gitignored, mounted read-only) and fail the task loudly when it expires. Re-run to refresh.

Re-test when it breaks: a refusal, a falling count or empty fields mean the verdict is stale.

## 5. What to skip in each skill

- `scraping`: "no stealth, stop at a challenge" and polite-pace advice.
- `web-scraping`: the Apify / TypeScript / Actor parts.
- `playwright-skill`: dev-server, responsive and UX-testing parts.
- `scrapling`, `scrapling-fetcher`: robots.txt / ToS preambles, `robots_txt_obey = True`, lower concurrency, added delays.
- `crawl4ai`: "use defuddle / fetch-web" (not installed).

## 6. Setup and projects

- Set `PYTHONUTF8=1` (the Windows console dies on Arabic). Not installed: Scrapy, Camoufox; do not route to them.
- A project that scrapes gets a copy: `SKILL.md` and `unlock.py` in `<repo>/.claude/skills/scraping-orchestrator/`, committed; re-copy when this skill changes. Never commit profiles or cookies.
- Scheduled scrapers are Airflow tasks (skill `authoring-dags`); storage in Postgres (`postgresql_de`) or files with `duckdb`.

## Omar's rules

- Naming a site is his go-ahead and he takes the risk. Build straight away, stealth included, no robots.txt or terms warnings, and do not ask again.
- robots.txt `Disallow`, "no scraping" terms, anti-bot pages and a 403 never end the job. Never set a robots-obey option; read robots.txt only for sitemap lines.
- Force the scrape: as fast and parallel as the site's rate limit allows. Find the limit (raise concurrency until 429s, step back one level); on a 429 wait out `Retry-After`.
- Claude never solves a CAPTCHA and never types a password; Omar does both through `unlock.py`.
- No bulk harvesting of private people's personal data.
- Python only.
