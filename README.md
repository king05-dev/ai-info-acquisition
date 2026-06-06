# AI Information Acquisition Layer

Autonomous web crawler that navigates websites 5+ levels deep, captures screenshots of every page, logs all visited URLs, and documents what was seen vs. missed — centrally hosted and accessible by any team member via browser.

Live demo: **[kapaldo.com/crawler](https://kapaldo.com/crawler)**  
Backend: **[ai-info-acquisition-production.up.railway.app](https://ai-info-acquisition-production.up.railway.app)**

---

## What Was Built

### The Problem
Teams manually copy-paste information from websites and documentation. The goal was to determine whether a system can autonomously gather this information instead.

### The Solution — Pure DOM Crawler on Railway

```
Browser UI (kapaldo.com/crawler)
    |
    | HTTP polling every 1 second
    v
FastAPI Backend (Railway — 8GB RAM)
    |
    `-- Crawl Engine: Python + Playwright
        1. Load page in real Chromium
        2. Extract all <a href> links from rendered DOM
        3. Filter: same subdomain only, no query params
        4. Keep only links DEEPER than current URL (more path segments)
        5. Sort deepest-first, queue top 5 at queue front
        6. Screenshot → move to next URL
```

No AI, no token cost. URL path depth is the navigation signal.

### Why Playwright MCP Was Disqualified
Playwright MCP runs on a single developer's machine. The requirement was central hosting accessible by multiple team members. Playwright MCP fails this by design.

### Why Render Free Tier Was Disqualified
Render's free tier has 512MB RAM. Chromium alone requires 300-400MB to launch. Every crawl attempt caused an OOM kill. Railway (8GB RAM) is used instead.

---

## Requirements Checklist

| Requirement | Status | How |
|---|---|---|
| Autonomously navigate websites | Done | Playwright drives real Chromium |
| Follow 5+ navigation layers deep | Done | Depth-first queue, URL-path depth heuristic |
| Open menus and subpages | Done | Full DOM rendered — all sidebar links captured |
| Take screenshots | Done | Playwright screenshot per page, all saved |
| Record visited URLs | Done | Full URL log with depth + title |
| Document seen vs not seen | Done | Discovered URLs vs visited URLs tracked separately |
| Evidence for later AI analysis | Done | JSON report + screenshots accessible via API |
| Centrally hosted, team accessible | Done | Railway + kapaldo.com/crawler |

---

## Architecture

### Frontend — `kapaldo.com/crawler`
- Next.js page on Cloudflare Pages
- URL input + Start/Stop buttons
- Live screenshot stream (polls `/screenshot/{id}/latest` every second)
- URL log with depth badges
- After crawl: screenshot gallery + "not visited" evidence panel

### Backend — `ai-info-acquisition-production.up.railway.app`
- FastAPI on Railway (Docker, Playwright pre-installed)
- `GET /health` — service health check
- `POST /start` — begin a crawl session
- `POST /stop/{session_id}` — stop mid-crawl
- `GET /status/{session_id}` — live stats (visited count, depth, queue)
- `GET /screenshot/{session_id}/latest` — current page screenshot
- `GET /screenshot/{session_id}/{n}` — screenshot of page n
- `GET /results/{session_id}` — full JSON report

---

## Test Case — Stripe Documentation

**Target:** `https://docs.stripe.com`  
**Selected because:** Deep sidebar navigation, demanding multi-level structure, well-structured URLs that map to content hierarchy.

Results in `/results/stripe-test/` after a live test run.

---

## Project Structure

```
ai-info-acquisition/
├── crawler/
│   ├── main.py           # FastAPI app — all API endpoints
│   ├── crawler.py        # Playwright crawl engine + DOM depth heuristic
│   └── requirements.txt
├── results/
│   └── stripe-test/      # Test evidence
├── Dockerfile            # Microsoft Playwright base image
├── docker-compose.yml    # Local development
└── README.md
```

---

## Running Locally

```bash
docker-compose up
# Open http://localhost:8000/health to verify
# Open kapaldo.com/crawler and point NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:8000
```

## Deploying for Team Access (Railway)

```bash
# 1. Push to GitHub (auto-deploys via Railway)
# 2. Generate domain on port 8000 in Settings → Networking
# 3. Update NEXT_PUBLIC_CRAWLER_API_URL in ayts-fe/.env.production
```

No API keys required — no external AI services used.

---

## Evidence Collected Per Crawl

After each session the backend saves to `/tmp/`:

| File | Contents |
|---|---|
| `{session_id}_page_{n}.png` | Screenshot of page n |
| `{session_id}_latest.png` | Most recent page (live view) |
| `{session_id}_report.json` | Full JSON: visited URLs, titles, depths, not-visited list |

The JSON report can be fed directly into any LLM for summarization, gap analysis, or decision support.

---

## Limitations

- Screenshots lose images and fonts (blocked to save memory)
- Max 15 pages per session (configurable in `crawler.py MAX_PAGES`)
- `/tmp` storage is lost on Railway restart — not permanent storage
- JS-heavy SPAs may timeout on first visit (30s limit)
- Free Railway credit: $5/month (~500 idle hours, less when crawling)
