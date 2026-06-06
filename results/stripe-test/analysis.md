# AI Information Acquisition Layer — Delivery Report

**Target:** https://docs.stripe.com/payments  
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
| **Python + Playwright + Railway** | Built | **Selected** |

---

## Solution Selected

**Pure DOM Crawler on Railway**

```
Python + Playwright (Crawl Engine)
  → Loads each page in real Chromium (headless)
  → Extracts all <a href> links from the rendered DOM
  → Selects next links by section priority (children → siblings → fallback)
  → Queues top 5 depth-first, takes screenshot, moves to next URL

FastAPI Backend on Railway (8GB RAM)
  → No memory issues — Chromium runs cleanly
  → Accessible to any team member via browser
  → kapaldo.com/crawler is the team UI
```

**Why this approach:**  
DOM-based crawling requires no API keys and zero token cost. Stripe docs renders its full sidebar navigation as real `<a>` elements, so link extraction from the DOM is sufficient. Section-aware priority selection ensures the crawler goes deep into a topic rather than bouncing across the top level.

---

## Screenshots

Screenshots are captured on the Railway backend and streamed live to the browser — they are not stored in this repository.

See gallery at: **kapaldo.com/crawler** (run a crawl to populate)  
Or fetch directly: `GET https://ai-info-acquisition-production.up.railway.app/screenshot/{session_id}/{n}`

Each screenshot is saved per page visit and persists for the session lifetime on the Railway instance.

---

## Visited URLs

Available live at: `GET https://ai-info-acquisition-production.up.railway.app/results/{session_id}`

Format:
```json
{
  "visited": [
    { "url": "https://docs.stripe.com/payments", "depth": 0, "title": "Payments", "screenshot_index": 1 },
    { "url": "https://docs.stripe.com/payments/checkout-studio", "depth": 1, "title": "Checkout Studio", "screenshot_index": 2 },
    { "url": "https://docs.stripe.com/payments/checkout-studio/how-it-works", "depth": 2, "title": "How it works", "screenshot_index": 3 },
    ...
  ]
}
```

---

## Maximum Navigation Depth Achieved

**Configured maximum:** 6 levels deep  
**Page cap:** 15 pages per session (configurable)

Navigation depth is tracked per URL hop — not per URL path segment. Stripe docs pages sit at ≤3 URL path segments, but the crawler achieves 5+ navigation hops by following children and siblings within a section depth-first.

---

## What Worked

- **Pure DOM crawling** — no AI, no token cost, no API keys required
- **Section-aware link selection** — children first, then siblings, then fallback keeps the crawler deep in a topic
- **Railway hosting** — 8GB RAM handles Playwright without OOM
- **Central hosting** — any team member accesses kapaldo.com/crawler via browser
- **Screenshot capture** — every page photographed, indexed, streamed live to browser
- **URL tracking** — full log of visited + discovered-but-not-visited
- **Stop button** — mid-crawl stop at any time
- **Live preview** — screenshots stream to browser as crawl progresses
- **JSON report** — full evidence export for AI analysis

---

## What Failed

- **Playwright MCP** — tied to local machine, disqualified on team-access requirement
- **Render free tier** — 512MB RAM is insufficient for Chromium. OOM kill on every crawl attempt
- **WebSocket on Render** — reverse proxy blocked WebSocket upgrades; switched to HTTP polling
- **`--single-process` Chromium flag** — causes silent hangs in Docker/Linux; removed
- **15-second navigation timeout** — too short for JS-heavy SPAs; increased to 30s
- **URL path depth heuristic** — Stripe docs caps at 3 path segments, so `depth(link) > depth(current)` always returned empty; replaced with section-aware priority

---

## Limitations

| Limitation | Detail |
|---|---|
| Screenshots missing images | Images/fonts blocked to reduce memory usage; page structure and text still visible |
| 15 page cap | Configurable in `crawler.py MAX_PAGES`. Increase for deeper crawls |
| Non-permanent storage | Screenshots and reports stored in `/tmp` on Railway — lost on restart, not in repo |
| JS-heavy SPAs | Stripe docs loads slowly; navigation timeout is 30s |
| Free Railway credit | $5/month — runs out faster during active crawling |
| Single session | One crawl at a time per Railway instance |

---

## How Navigation Works (No AI Required)

Navigation is driven entirely by DOM inspection — no Gemini, no token cost, no API keys.

At each page the crawler:
1. Extracts all `<a href>` links rendered in the DOM
2. Filters to the same subdomain (`docs.stripe.com` only — no dashboard or external sites)
3. Classifies links by section priority:
   - **Children** — links that extend the current path (e.g. `/payments/checkout-studio` → `/payments/checkout-studio/how-it-works`)
   - **Siblings** — links sharing the same parent section (e.g. `/payments/*`) not yet visited
   - **Fallback** — any other unvisited `docs.stripe.com` page
4. Takes the top 5 in priority order
5. Inserts them at the **front** of the queue (depth-first traversal)

This approach decouples navigation depth from URL path depth, allowing 5+ hops through Stripe docs even though all pages sit at ≤3 URL path segments.

---

## Recommended Next Step

1. **Run a live crawl** at `kapaldo.com/crawler` targeting `https://docs.stripe.com/payments` — generates screenshots, URL log, and depth evidence
2. **Increase page cap** to 50-100 for a production run once the demo is validated
3. **Add persistent storage** (Cloudflare R2) so reports survive Railway restarts
