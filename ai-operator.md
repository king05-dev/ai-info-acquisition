# AI Integration — How Gemini Operates in This System

This document explains exactly where and how AI is integrated into the crawler — what it perceives, what it decides, and what action it takes.

---

## AI Operator vs AI Assistant

| | AI Assistant | AI Operator (this system) |
|---|---|---|
| **Triggered by** | Human asking a question | The crawler reaching a new page |
| **Input** | User's text prompt | Raw HTML of the current page |
| **Output** | Text answer | A list of URLs to navigate next |
| **Human required?** | Yes — to ask | No — runs autonomously |
| **Action taken** | None | Adds URLs to the crawl queue |
| **Example** | "What is on this page?" | "Where should I go next?" |

An assistant waits. An operator acts.

---

## Where Gemini Operates

**File:** `crawler/ai_discovery.py`  
**Model:** `gemini-1.5-flash`  
**Triggered:** Every page visited at depth 0, 1, or 2 (the first 3 levels of any crawl)

---

## The Operator Loop

```
Playwright loads page
        |
        v
Is depth <= 2?
  YES → Gemini reads the page HTML
        Decides which links are real navigation
        Returns URL list → inserted at front of crawl queue
        |
  NO  → Standard <a href> extraction only
        |
        v
Playwright visits next URL
```

---

## What Gemini Receives

```
Prompt sent to gemini-1.5-flash:

"You are analyzing a documentation page navigation.

Current URL: https://docs.python.org/3/

Page HTML (truncated):
<nav>...</nav><main>...</main>

Extract all navigation links (sidebar menus, top nav, expandable sections)
that lead to documentation subpages.
Return ONLY a JSON array of absolute URLs. No explanation."
```

---

## What Gemini Decides

- Which links are **real navigation** — sidebar sections, top-level topics, expandable menus
- Which links are **noise** — footer links, external sites, legal pages, anchor links
- Which links lead **deeper** into the documentation structure vs. back to the surface

This decision is what a human researcher makes when reading a page — and it is exactly what standard `<a href>` scraping cannot do, because modern sites render navigation menus with JavaScript after the page loads.

---

## What Gemini Returns

```json
[
  "https://docs.python.org/3/library/",
  "https://docs.python.org/3/reference/",
  "https://docs.python.org/3/tutorial/",
  "https://docs.python.org/3/howto/"
]
```

These are inserted at the **front** of the crawl queue (priority navigation) so the crawler goes deep before going wide.

---

## Why This Matters for Navigation Depth

Without Gemini, the crawler only finds links in raw HTML. On JS-rendered sites (Stripe, Notion, GitHub Docs), the sidebar navigation is built by JavaScript — it does not exist in the HTML source. Gemini reads what the browser actually rendered and extracts paths that would otherwise be invisible.

**With standard extraction only:**
- Finds generic `<a>` links on the page
- Misses sidebar menus rendered by React/Vue
- Navigation stays shallow

**With Gemini at depth 0-2:**
- Identifies the documentation structure intelligently
- Discovers sidebar paths and nested sections
- Crawl goes 5+ levels deep instead of staying at 1-2

---

## Perceive → Decide → Act

This is the core operator pattern:

| Step | What happens |
|---|---|
| **Perceive** | Playwright takes a screenshot and reads rendered HTML |
| **Decide** | Gemini identifies which navigation paths to follow |
| **Act** | URLs are added to the crawl queue — crawler follows them |

No human is involved in any of these steps. The AI perceives the environment (the web page), makes a decision (which links matter), and takes an action (queues the URLs). That is what makes it an operator rather than an assistant.

---

## Demo Target — Proving Navigation Depth

**Selected for demo:** `https://docs.python.org/3/`

**Why Python docs over Stripe docs:**

| | Stripe Docs | Python Docs |
|---|---|---|
| Rendering | JavaScript SPA | Static HTML |
| Page load speed | Slow (3-10s) | Fast (<1s) |
| Navigation structure | JS-rendered sidebar | HTML links |
| 15-page depth potential | 2-3 levels | 5-6 levels |
| Timeout risk | High | Low |

With 15 pages on Python docs, the crawler can reach:
- Level 0: `docs.python.org/3/`
- Level 1: `docs.python.org/3/library/`
- Level 2: `docs.python.org/3/library/functions.html`
- Level 3: `docs.python.org/3/library/functions.html#built-in-functions`
- Level 4+: Cross-references and sub-topics

This demonstrates navigation depth, information acquisition, and context retention across 5+ levels — which is the stated goal of the test, not page count.
