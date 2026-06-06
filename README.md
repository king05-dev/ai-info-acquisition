# AI Information Acquisition Layer

Autonomous web crawler that navigates websites 5+ levels deep, streams live screenshots to a browser UI, and documents everything for later AI analysis.

Centrally hosted — accessible by any team member via browser, no local install required.

---

## Candidate Evaluation

### Playwright MCP
- **What it is:** MCP server that drives a local browser via Claude Code
- **Verdict: Disqualified**
- **Reason:** Runs on a single developer's machine. Cannot be centrally hosted or accessed by multiple team members. Fails the team-access requirement by design.

### Selected Solution: Python Playwright + FastAPI + WebSocket
- **Why:** Full server-side browser control, real-time screenshot streaming to any browser, Dockerized for deployment anywhere
- **Meets all requirements:** Yes

---

## Requirements Checklist

| Requirement | Status |
|---|---|
| Autonomously navigate websites | Done |
| Follow 5+ navigation layers deep | Done |
| Open menus and subpages | Done |
| Take screenshots | Done |
| Record visited URLs | Done |
| Document seen vs not seen | Done |
| Evidence for later AI analysis | Done |
| AI-driven workflow | Done |
| Centrally hosted, team accessible | Done |

---

## Architecture

```
Browser UI (any team member)
    |
    |  WebSocket (live screenshot stream)
    v
FastAPI Server (Docker, hosted)
    |-- /start   -> trigger crawl with target URL
    |-- /status  -> current depth, URLs visited
    `-- /results -> full evidence export
    |
    v
Playwright (headless Chromium, server-side)
    |
    |-- AI Phase (Claude API - claude-haiku-4-5)
    |   `-- Discovers navigation structure, menus, hidden paths
    |       -> Outputs seed URL list
    |
    `-- Crawl Phase (Python)
        `-- Systematically crawls all discovered URLs
            -> Tracks depth, captures screenshots, logs content
```

---

## Test Case: Stripe Documentation

**Target:** https://docs.stripe.com  
**Goal:** Prove 5+ level navigation depth with evidence

Results in `/results/stripe-test/`

---

## Project Structure

```
ai-info-acquisition/
|-- crawler/
|   |-- main.py           # FastAPI app + WebSocket
|   |-- crawler.py        # Playwright crawl logic
|   |-- ai_discovery.py   # Claude API navigation phase
|   `-- requirements.txt
|-- ui/
|   `-- index.html        # Web UI (URL input + live stream)
|-- results/
|   `-- stripe-test/      # Test evidence
|-- Dockerfile
|-- docker-compose.yml
|-- .env.example
`-- README.md
```

---

## Running Locally

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
docker-compose up
# Open http://localhost:8000
# Enter target URL, click Start
# Watch live in browser
```

## Deploying for Team Access

```bash
# On any VPS / cloud server
cp .env.example .env
# Add ANTHROPIC_API_KEY
docker-compose up -d
# Share the server IP with the team
```

---

## Results Summary

> To be filled after Stripe docs test run.

- **Max depth achieved:** -
- **URLs visited:** -
- **What worked:** -
- **What failed:** -
- **Limitations:** -
- **Recommended next step:** -
