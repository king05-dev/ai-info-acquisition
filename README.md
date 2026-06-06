# AI Information Acquisition Layer

Autonomous web crawler that navigates websites 5+ levels deep, captures screenshots of every page, logs all visited URLs, and documents what was seen vs. missed — centrally hosted and accessible by any team member via browser.

Live demo: **[kapaldo.com/crawler](https://kapaldo.com/crawler)**  
Backend: **[ai-info-acquisition-production.up.railway.app](https://ai-info-acquisition-production.up.railway.app)**

---

## What Was Built

### The Problem
Teams manually copy-paste information from websites and documentation. The goal was to determine whether AI can autonomously gather this information instead.

### The Solution — Hybrid AI + Python Crawler

```
Browser UI (kapaldo.com/crawler)
    |
    | HTTP polling every 1 second
    v
FastAPI Backend (Railway — 8GB RAM)
    |
    |-- AI Phase: Gemini 1.5 Flash
    |   Reads page HTML, identifies navigation links
    |   a human would follow (menus, sidebars, JS nav)
    |   → Outputs smart seed URL list
    |
    `-- Crawl Phase: Python + Playwright
        Systematically visits all discovered URLs
        → Tracks depth, captures screenshots, logs content
```

**Why hybrid?** Running AI for every page visit is expensive and slow. Gemini is only used for the first 2-3 levels to discover navigation structure. Python handles the bulk crawl from there — fast and token-efficient.

### Why Playwright MCP Was Disqualified
Playwright MCP runs on a single developer's machine. The requirement was central hosting accessible by multiple team members. Playwright MCP fails this by design.

### Why Render Free Tier Was Disqualified
Render's free tier has 512MB RAM. Chromium alone requires 300-400MB to launch. Every crawl attempt caused an OOM kill. Railway (8GB RAM) is used instead.

---

## Requirements Checklist

| Requirement | Status | How |
|---|---|---|
| Autonomously navigate websites | Done | Playwright drives real Chromium |
| Follow 5+ navigation layers deep | Done | Recursive depth tracking, max depth 6 |
| Open menus and subpages | Done | Gemini identifies JS-rendered nav at depth 0-2 |
| Take screenshots | Done | Playwright screenshot per page, all saved |
| Record visited URLs | Done | Full URL log with depth + title |
| Document seen vs not seen | Done | Discovered URLs vs visited URLs tracked separately |
| Evidence for later AI analysis | Done | JSON report + screenshots accessible via API |
| AI-driven workflow | Done | Gemini 1.5 Flash for navigation discovery |
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
- `POST /stop/{session_id}` — stop mid-crawl (saves credits)
- `GET /status/{session_id}` — live stats (visited count, depth, queue)
- `GET /screenshot/{session_id}/latest` — current page screenshot
- `GET /screenshot/{session_id}/{n}` — screenshot of page n
- `GET /results/{session_id}` — full JSON report

### Gemini API Key Role
Used in `crawler/ai_discovery.py`. When the crawler visits a page at depth ≤ 2, it sends the first 8,000 characters of the page HTML to `gemini-1.5-flash` and asks it to identify navigation links a human would follow. Returns a JSON array of URLs. Falls back silently if the API call fails — the crawl continues with standard link extraction.

Model: `gemini-1.5-flash` (free tier: 15 req/min, 1M tokens/day)  
Env var: `GOOGLE_API_KEY`

---

## Test Case — Stripe Documentation

**Target:** `https://docs.stripe.com`  
**Selected because:** JS-heavy SPA, deep sidebar navigation, demanding multi-level structure.

Results in `/results/stripe-test/` after a live test run.

---

## Project Structure

```
ai-info-acquisition/
├── crawler/
│   ├── main.py           # FastAPI app — all API endpoints
│   ├── crawler.py        # Playwright crawl engine
│   ├── ai_discovery.py   # Gemini navigation discovery
│   └── requirements.txt
├── results/
│   └── stripe-test/      # Test evidence
├── Dockerfile            # Microsoft Playwright base image
├── docker-compose.yml    # Local development
├── .env.example
└── README.md
```

---

## Running Locally

```bash
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
docker-compose up
# Open http://localhost:8000/health to verify
# Open kapaldo.com/crawler and point NEXT_PUBLIC_CRAWLER_API_URL=http://localhost:8000
```

## Deploying for Team Access (Railway)

```bash
# 1. Push to GitHub (auto-deploys via Railway)
# 2. Set GOOGLE_API_KEY in Railway Variables tab
# 3. Generate domain on port 8000 in Settings → Networking
# 4. Update NEXT_PUBLIC_CRAWLER_API_URL in ayts-fe/.env.production
```

---

## Evidence Collected Per Crawl

After each session the backend saves to `/tmp/`:

| File | Contents |
|---|---|
| `{session_id}_page_{n}.png` | Screenshot of page n |
| `{session_id}_latest.png` | Most recent page (live view) |
| `{session_id}_report.json` | Full JSON: visited URLs, titles, depths, not-visited list |

The JSON report is the "evidence for later AI analysis" — it can be fed directly into any LLM for summarization, gap analysis, or decision support.

---

## Limitations

- Screenshots lose images and fonts (blocked to save memory)
- Max 15 pages per session (configurable in `crawler.py`)
- `/tmp` storage is lost on Railway restart — not permanent storage
- JS-heavy SPAs may timeout on first visit (45s limit)
- Free Railway credit: $5/month (~500 idle hours, less when crawling)
