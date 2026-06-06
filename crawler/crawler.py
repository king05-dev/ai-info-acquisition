import asyncio
import json
import os
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from playwright.async_api import async_playwright

SCREENSHOT_DIR = "/tmp/crawler_screenshots"
MAX_PAGES = 15
MAX_DEPTH = 6
MAX_DEEP_LINKS_PER_PAGE = 5  # how many deeper links to queue per page
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def normalize_url(url: str) -> str:
    """Strip anchor and query params — two URLs differing only in ?version= are the same page."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def url_path_depth(url: str) -> int:
    """Count non-empty path segments — used to rank links by how deep they go."""
    return len([s for s in urlparse(url).path.split("/") if s])


def find_deeper_links(all_hrefs: list[str], current_url: str, allowed_netloc: str, visited: set) -> list[str]:
    """
    From the raw <a href> list, keep only links that:
      1. Are on exactly the same subdomain (e.g. docs.stripe.com — not dashboard.stripe.com)
      2. Have MORE path segments than the current URL (going deeper)
      3. Haven't been visited yet
      4. Have no query params (clean doc pages, not API explorer variants)
    Then sort deepest-first and return the top MAX_DEEP_LINKS_PER_PAGE.
    """
    current_depth = url_path_depth(current_url)
    candidates = []

    for href in all_hrefs:
        normalized = normalize_url(href)
        if not normalized or normalized in visited:
            continue
        parsed = urlparse(normalized)
        if parsed.netloc != allowed_netloc:   # exact match — no dashboard.stripe.com
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if url_path_depth(normalized) > current_depth:
            candidates.append(normalized)

    # Deduplicate, sort deepest-first, cap
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    unique.sort(key=url_path_depth, reverse=True)
    return unique[:MAX_DEEP_LINKS_PER_PAGE]


class Crawler:
    def __init__(self, start_url: str, max_depth: int = MAX_DEPTH):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited: dict[str, dict] = {}
        self.discovered: set[str] = set()
        self.queue: list[tuple[str, int]] = [(normalize_url(start_url), 0)]
        self.current_url = ""
        self.screenshot_ts = 0
        self.screenshot_count = 0
        self.status = "idle"
        self.session_id = ""
        self.should_stop = False
        self.started_at = datetime.utcnow().isoformat()
        parsed = urlparse(start_url)
        self.allowed_netloc = parsed.netloc  # exact subdomain — e.g. "docs.stripe.com"

    def screenshot_path(self, n: int) -> str:
        return os.path.join(SCREENSHOT_DIR, f"{self.session_id}_page_{n}.png")

    def latest_screenshot_path(self) -> str:
        return os.path.join(SCREENSHOT_DIR, f"{self.session_id}_latest.png")

    def snapshot(self) -> dict:
        return {
            "status": self.status,
            "current_url": self.current_url,
            "screenshot_ts": self.screenshot_ts,
            "screenshot_count": self.screenshot_count,
            "visited_count": len(self.visited),
            "max_depth_reached": max((v["depth"] for v in self.visited.values()), default=0),
            "queue_remaining": len(self.queue),
        }

    def export(self) -> dict:
        visited_urls = set(self.visited.keys())
        not_visited = [u for u in self.discovered if u not in visited_urls]
        return {
            "session_id": self.session_id,
            "start_url": self.start_url,
            "started_at": self.started_at,
            "finished_at": datetime.utcnow().isoformat(),
            "total_visited": len(self.visited),
            "total_discovered": len(self.discovered),
            "total_not_visited": len(not_visited),
            "max_depth": max((v["depth"] for v in self.visited.values()), default=0),
            "screenshot_count": self.screenshot_count,
            "visited": [
                {
                    "url": url,
                    "depth": data["depth"],
                    "title": data["title"],
                    "visited_at": data["visited_at"],
                    "screenshot_index": data.get("screenshot_index"),
                }
                for url, data in self.visited.items()
            ],
            "not_visited": not_visited[:100],
        }

    async def run(self):
        self.status = "running"
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--no-first-run",
                    "--mute-audio",
                ]
            )

            while self.queue and len(self.visited) < MAX_PAGES and not self.should_stop:
                url, depth = self.queue.pop(0)

                if url in self.visited or depth > self.max_depth:
                    continue

                netloc = urlparse(url).netloc
                if netloc != self.allowed_netloc:
                    continue

                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    java_script_enabled=True,
                )
                page = await context.new_page()

                await page.route(
                    "**/*.{png,jpg,jpeg,gif,svg,webp,ico,woff,woff2,ttf,mp4,mp3}",
                    lambda route: route.abort()
                )

                try:
                    self.current_url = url
                    print(f"[crawler] d={depth} page={len(self.visited)+1} {url}", flush=True)

                    try:
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    except Exception:
                        await page.goto(url, timeout=30000, wait_until="commit")

                    await asyncio.sleep(1.5)

                    # Screenshot
                    self.screenshot_count += 1
                    idx = self.screenshot_count
                    try:
                        await page.screenshot(path=self.screenshot_path(idx), full_page=False, timeout=10000)
                        await page.screenshot(path=self.latest_screenshot_path(), full_page=False, timeout=10000)
                        self.screenshot_ts = int(datetime.utcnow().timestamp())
                    except Exception:
                        idx = None

                    title = await page.title()
                    self.visited[url] = {
                        "depth": depth,
                        "title": title,
                        "visited_at": datetime.utcnow().isoformat(),
                        "screenshot_index": idx,
                    }

                    # Extract all hrefs from DOM — no AI needed
                    all_hrefs: list[str] = await page.eval_on_selector_all(
                        "a[href]", "els => els.map(el => el.href)"
                    )

                    # Track everything discovered (for the "not visited" report)
                    for href in all_hrefs:
                        n = normalize_url(href)
                        if n:
                            self.discovered.add(n)

                    if depth < self.max_depth:
                        # Find links that go DEEPER than the current page
                        deep_links = find_deeper_links(
                            all_hrefs, url, self.allowed_netloc, set(self.visited.keys())
                        )
                        print(f"[crawler] found {len(deep_links)} deeper links", flush=True)

                        # Insert in reverse so index-0 = deepest link (first visited next)
                        for link in reversed(deep_links):
                            clean = normalize_url(link)
                            if clean and clean not in self.visited:
                                self.queue.insert(0, (clean, depth + 1))
                    # At max_depth: screenshot taken, links logged — no deeper queuing

                except Exception as e:
                    self.visited[url] = {
                        "depth": depth,
                        "title": f"ERROR: {str(e)[:120]}",
                        "visited_at": datetime.utcnow().isoformat(),
                        "screenshot_index": None,
                    }
                finally:
                    await page.close()
                    await context.close()

            await browser.close()

        report = self.export()
        report_path = os.path.join(SCREENSHOT_DIR, f"{self.session_id}_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[crawler] done. visited={len(self.visited)} max_depth={report['max_depth']}", flush=True)
        self.status = "done"
