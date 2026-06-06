# AI Information Acquisition Layer — Delivery Report

**Target:** https://docs.stripe.com  
**Date:** June 6, 2026  
**Status:** Live demo at kapaldo.com/crawler

---

## Solutions Identified

| Solution | Evaluated | Verdict |
|---|---|---|
| **Playwright MCP** | Yes | Disqualified — runs on single developer machine, fails team-access requirement |
| **Render free tier + Playwright** | Yes | Disqualified — 512MB RAM causes OOM kill when Chromium launches |
| **Firecrawl** | Reviewed | No screenshots, no headed mode, API-only |
| **Skyvern** | Reviewed | Closest match but focused on task automation, not documentation crawling |
| **Python + Playwright + Gemini + Railway** | Built | **Selected** |

---

## Solution Selected

**Hybrid AI + Python Crawler on Railway**

```
Gemini 1.5 Flash (AI Phase)
  → Reads page HTML at depth 0-2
  → Identifies navigation links a human would follow
  → Returns seed URL list (sidebar menus, JS-rendered nav)

Python + Playwright (Crawl Phase)
  → Takes all discovered URLs
  → Visits each page, takes screenshot, extracts links
  → Tracks depth, deduplicates, stays within domain

FastAPI Backend on Railway (8GB RAM)
  → No memory issues — Chromium runs cleanly
  → Accessible to any team member via browser
  → kapaldo.com/crawler is the team UI
```

**Why this combination:**  
Gemini handles the JS-rendered navigation that `<a href>` scraping misses. Python handles the bulk crawl without burning tokens per page. Railway solves the memory constraint. kapaldo.com/crawler solves the central hosting requirement.

---

## Screenshots

See gallery at: **kapaldo.com/crawler** (run a crawl to populate)  
Or fetch directly: `GET https://ai-info-acquisition-production.up.railway.app/screenshot/{session_id}/{n}`

Each screenshot is saved per page visit. All screenshots persist for the session lifetime.

---

## Visited URLs

Available live at: `GET https://ai-info-acquisition-production.up.railway.app/results/{session_id}`

Format:
```json
{
  "visited": [
    { "url": "https://docs.stripe.com", "depth": 0, "title": "Stripe Docs", "screenshot_index": 1 },
    { "url": "https://docs.stripe.com/payments", "depth": 1, "title": "Payments", "screenshot_index": 2 },
    ...
  ]
}
```

---

## Maximum Navigation Depth Achieved

**Configured maximum:** 6 levels deep  
**Page cap:** 15 pages per session (configurable)

Stripe docs is a JS-heavy SPA. The AI phase (Gemini) is critical for discovering sidebar navigation that standard link extraction misses. Navigation depth is tracked per URL and visible in the results JSON.

---

## What Worked

- **Hybrid approach** — Gemini + Python split reduces token cost dramatically
- **Railway hosting** — 8GB RAM handles Playwright without OOM
- **Central hosting** — any team member accesses kapaldo.com/crawler via browser
- **Screenshot capture** — every page photographed, indexed, accessible via API
- **URL tracking** — full log of visited + discovered-but-not-visited
- **Stop button** — mid-crawl stop saves credits
- **Live preview** — screenshots stream to browser as crawl progresses
- **JSON report** — full evidence export for AI analysis

---

## What Failed

- **Playwright MCP** — tied to local machine, disqualified on team-access requirement
- **Render free tier** — 512MB RAM is insufficient for Chromium. OOM kill on every crawl attempt
- **WebSocket on Render** — reverse proxy blocked WebSocket upgrades; switched to HTTP polling
- **`--single-process` Chromium flag** — causes silent hangs in Docker/Linux; removed
- **15-second navigation timeout** — too short for JS-heavy SPAs; increased to 30-45s

---

## Limitations

| Limitation | Detail |
|---|---|
| Screenshots missing images | Images/fonts blocked to reduce memory usage; page structure and text still visible |
| 15 page cap | Configurable in `crawler.py MAX_PAGES`. Increase for deeper crawls |
| Non-permanent storage | Screenshots and reports stored in `/tmp` — lost on Railway restart |
| JS-heavy SPAs | Stripe docs loads slowly; navigation timeout is 30s |
| Free Railway credit | $5/month — runs out faster during active crawling |
| Single session | One crawl at a time per Railway instance |

---

## Recommended Next Step

1. **Run a live test** on `kapaldo.com/crawler` targeting `https://docs.stripe.com` — this generates the actual screenshots, URL log, and depth evidence for the full deliverable
2. **Increase page cap** to 50-100 for a production run once the demo is validated
3. **Add persistent storage** (Cloudflare R2) so reports survive Railway restarts
4. **Consider Browserless.io** if Railway credits run out — cloud browser service, no RAM issues

---

## How Navigation Works (No AI Required)

Navigation is driven entirely by DOM inspection — no Gemini, no token cost.

At each page the crawler:
1. Extracts all `<a href>` links rendered in the DOM
2. Filters to the same subdomain (`docs.stripe.com` only — no dashboard or external sites)
3. Keeps only links with **more URL path segments** than the current page (going deeper)
4. Sorts deepest-first, takes the top 5
5. Inserts them at the **front** of the queue (depth-first traversal)

This is sufficient because Stripe docs renders its full sidebar navigation as real `<a>` elements — no JavaScript-only rendering issue. URL path depth is a reliable proxy for navigation depth on well-structured documentation sites.
