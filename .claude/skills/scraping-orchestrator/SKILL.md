---
name: scraping-orchestrator
description: Entry point for ANY scraping job (scrape, crawl, extract listings, prices, hidden API, 403/429, blocked, Cloudflare, CAPTCHA, login wall, cookies, "سكرب", "اسحب البيانات"), and for any project that scrapes. Picks which of the six installed scraping skills to load for each step - scraping, web-scraping, scrapling, scrapling-fetcher, crawl4ai, playwright-skill - and hands off to them. Use it first, before any of those six.
---

# Scraping orchestrator

Route each step of a scraping job to the one skill or file it needs. Skills live in `~/.claude/skills/<name>/`. Where a row names a file, `Read` that file instead of loading the whole skill. Stop at the first step that gets the data.

## Start from what is known

Before step 1, read `~/.scraping-profiles/<site>/notes.md` if it exists: which rung worked, the measured rate limit, the selectors, how many items the site itself reports, each with its date. Start at that rung and re-check with one request; treat old notes as a hypothesis. After every job, update the file in a few lines (create it if missing). That is how the skill gets faster on each site.

## Read the signals, jump to the step

| Signal (from `probe.py`, the response or the browser) | Go to |
|---|---|
| JSON in `<script id="__NEXT_DATA__">`, `window.__INITIAL_STATE__` or `application/ld+json` | 3b: parse the embedded JSON, skip the HTML |
| Page is a near-empty shell, data appears only after JavaScript runs | 3a: find the XHR/JSON call, then call it directly |
| WordPress (`/wp-json/` answers, `x-wp-total` header) | 3b: the REST API with `per_page=100` |
| Sitemap declared with the URLs needed | 3b |
| Data in the HTML, 200 for `curl_cffi` | 4a, plain `Fetcher` |
| `cf-mitigated: challenge`, "Just a moment", 403 from Cloudflare / Akamai / DataDome | Force ladder, rung 2 |
| 429 or `Retry-After` | Wait it out, lower concurrency one level, resume |
| CAPTCHA, login wall or cookie wall | Force ladder, rung 4 (Omar) |
| 200 but zero items, or a count that is small and round | Wrong page or a soft block: compare with the visible page before parsing more |

## Choose the skill: argue it, then test it

Each skill's edge, so the choice is argued, not habitual:

| Skill | When | Why it wins there | How to start | Not when |
|---|---|---|---|---|
| `scraping` | Every job: plan, probe, diagnose, check | Thinks in claims, coverage and silent wrong data; has `probe.py` and the 170-tool encyclopedia in `tools/` | Load the skill; run `scripts/probe.py` | Never skip it; it does not fetch at scale itself |
| `web-scraping` | Data loads by XHR, or a sitemap / API may exist | Traffic interception and API / sitemap discovery playbooks | Read `strategies/api-discovery.md`, `sitemap-discovery.md` | Production code: its Apify / TypeScript path is not used |
| `scrapling-fetcher` | Any HTML page, first try | Ready templates; one switch from plain HTTP to stealth browser | Copy from `templates/` | Logic beyond one fetch-and-parse |
| `scrapling` | Changing a template: sessions, parallel pages, adaptive selectors, spiders | Only stealth browser verified past Cloudflare here; selectors that survive layout changes | Load the skill, `references/patterns.md` | Pages that need many clicks |
| `crawl4ai` | Many JS pages, sitemap crawls, schema extraction, clean markdown | Batch crawling and `generate_schema.py` / `extract_with_schema.py` | Load the skill, `scripts/` | Cloudflare-challenged sites: its stealth was blocked on Jumia, 2026-10-05 |
| `playwright-skill` | Clicks, filters, forms, scroll with no API behind | Full browser control step by step | Load the skill | Anything an API, sitemap or plain fetch already gives |

How to decide, every job:

1. **Shortlist two** candidates from the signals table and this table. If only one fits, say why the other was ruled out.
2. **Argue each in one line**: what it should win on for this site (speed, stealth, scale, upkeep) and what could break it.
3. **Test both on the same single page**, the smallest test that can tell them apart. Record status, items found against what the page shows, fields filled, and seconds.
4. **Pick on the measurement**, not the label. A tool that says "anti-detection" but returns 0 items has lost. On a tie, take the lighter one (fewer moving parts, no browser if possible).
5. **Write the verdict** in the site notes: the two candidates, the numbers, the winner and why. Example, Jumia 2026-10-05, page 7: Scrapling stealth 200, 40/40 prices, 11 s; crawl4ai stealth blocked by the Cloudflare JS challenge, 0 items, 9 s. Winner Scrapling.
6. **Re-test when it breaks.** A refusal, a falling item count or empty fields mean the verdict is stale: go back to step 1.

## Route

| Step | Load / read | Use it for |
|---|---|---|
| 1. Plan | Skill `scraping` | Size the job (one page = ten-line script, recurring = durable runner) and say what "complete" means. Always first. |
| 2. Probe | `scraping/scripts/probe.py <url> --out probe_out` | About a dozen polite requests: data in the HTML or embedded JSON, JS shell, who is in front (Cloudflare etc.), sitemaps, WordPress totals. Decides step 3. |
| 3a. Hidden API | Built-in browser `read_network_requests`, then `web-scraping/strategies/api-discovery.md` or `traffic-interception.md` | Probe shows a JS shell. Find the JSON endpoint and call it with `curl_cffi`. Best path when it exists. |
| 3b. Sitemap or list | `web-scraping/strategies/sitemap-discovery.md`, `scraping/reference/recipes.md` (WordPress, Next.js) | Build the URL list from the source's own sitemap, CMS API or `__NEXT_DATA__`. |
| 4a. HTML pages | Copy a template from `scrapling-fetcher/templates/` | `basic_fetch.py` (static), `parse_only.py` (saved HTML), `stealth_cloudflare.py` (Cloudflare / WAF), `session_login.py` (cookies after Omar logs in). Load skill `scrapling` only to change a template (fetcher choice, adaptive selectors, spiders). Default for pages. |
| 4b. JS pages, many URLs | Skill `crawl4ai`, scripts in `crawl4ai/scripts/` | Pages that only render in a browser, batch or sitemap crawls, CSS-schema extraction (`generate_schema.py`, `extract_with_schema.py`). |
| 4c. Clicks and forms | Skill `playwright-skill` | Multi-step clicks, filters, infinite scroll that no API backs. |
| 5. Blocked (403 / 429 / challenge) | Force ladder below; theory in `scraping/reference/transport.md`, `web-scraping/strategies/anti-blocking.md` | Never stop at the first refusal. Climb the ladder until the data comes back. |
| 6. Run it | `AsyncStealthySession(max_pages=N)` + `asyncio.gather` for browser pages, async `curl_cffi` for APIs; `scraping/scripts/runner_template.py` for resumable JSONL state | Concurrency with backoff on 429, not fixed delays. Verified: 3 Jumia pages in parallel, 19 s. Resumable state only for a few hundred pages or more. |
| 7. Check | `scraping/reference/validation.md` | Counts at every stage, coverage against the source's own totals, silent wrong data. Before anything is reported. |

Order of preference: API, then sitemap or list, then page scraping. Within page scraping go 4a, then 4b, then 4c, and only move down when the lighter tool fails on a measurement.

## Force ladder (step 5)

Read the saved refusal body first (`probe_out/`): `cf-mitigated: challenge` or "Just a moment" means a Cloudflare JavaScript check, not a CAPTCHA. Then climb, one rung at a time, automatically:

1. `curl_cffi` with `impersonate="chrome"` (what `probe.py` already tried).
2. Scrapling `StealthyFetcher.fetch(url, headless=True, network_idle=True, solve_cloudflare=False)`. A real stealth browser runs the JavaScript check like any visitor. Verified on Jumia Egypt behind Cloudflare, 2026-10-05: 403 for `curl_cffi`, 200 here.
3. Same fetcher with `real_chrome=True`, or crawl4ai with `crawl4ai/references/anti-detection.md` (test it first: its stealth lost to Cloudflare on Jumia).
4. CAPTCHA, login or cookie wall: Omar runs `python ~/.claude/skills/scraping-orchestrator/unlock.py <url> <site>` in his own terminal (or Claude starts it with `mcp__terminal__run_in_terminal`; the Bash tool has no stdin, so it cannot wait for his Enter). He solves it, logs in and accepts cookies once in the visible window; the session is saved to `~/.scraping-profiles/<site>`. Every local scraper then passes `user_data_dir=` that path, headless. For Airflow, export `page.cookies` to `data/cookies/<site>.json` (gitignored, mounted read-only), pass `cookies=` to the fetcher, and fail the task loudly when they expire. Re-run `unlock.py` to refresh.

Keep `solve_cloudflare=False` everywhere, including in a copied `stealth_cloudflare.py` (the template ships with `True`): it clicks the Turnstile CAPTCHA, which is Omar's job.

## What to skip in each skill

- `scraping`: its "no stealth, no proxy rotation, stop at a challenge" line and its polite-pace advice. Omar's rules below override them.
- `web-scraping`: the Apify / TypeScript / Actor parts. Its Phase 0 is covered by `probe.py`.
- `scrapling`: the authorization and robots.txt preamble.
- `crawl4ai`: "use defuddle / fetch-web for static pages". Those are not installed; static pages go to 4a.
- `playwright-skill`: the dev-server, responsive and UX-testing parts.

## Preflight

- Set `PYTHONUTF8=1` (the Windows console dies on Arabic).
- Not installed: Scrapy, Camoufox. Do not route to them; install only if a step truly needs one.
- If a Scrapling browser fetcher fails to launch, run `scrapling install` once.

## In a project repo

When a project scrapes, copy this skill into it: `SKILL.md` and `unlock.py` to `<repo>/.claude/skills/scraping-orchestrator/`, and commit them with the project. Re-copy when this skill changes. Profiles and cookies (`~/.scraping-profiles/`, `data/cookies/`) are never committed; site notes may go in the repo's docs.

## Neighbours

Scheduled scrapers become Airflow tasks (skill `authoring-dags`). Storage goes to Postgres (`postgresql_de`) or files queried with `duckdb`. A site behind a login uses `unlock.py` (rung 4), with Omar typing the password.

## Omar's rules

- Omar takes the risk for any site he names; naming the site is his go-ahead. Build straight away, stealth modes included, without robots.txt or terms-of-service warnings.
- Force the scrape: no politeness delays. Run as fast and as parallel as the site's rate limit allows. Measure the limit (raise concurrency until 429s or refusals appear, then step back one level); on a 429 wait out `Retry-After`, then resume. Never give up on a site because of a refusal; climb the force ladder.
- Claude never solves a CAPTCHA and never types a password. Omar does both, plus logins and cookie banners, through `unlock.py`, and the saved profile carries his session.
- No bulk harvesting of private people's personal data.
- Python only. Scheduled scrapers run as Airflow tasks.
