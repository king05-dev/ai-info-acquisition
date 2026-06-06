import asyncio
import json
import os
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from ai_discovery import discover_links

SCREENSHOT_DIR = "/tmp/crawler_screenshots"
MAX_PAGES = 15
MAX_AI_CALLS = 8   # Gemini calls per session — guides depth chain, saves tokens
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class Crawler:
    def __init__(self, start_url: str, max_depth: int = 6):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited: dict[str, dict] = {}
        self.discovered: set[str] = set()  # all URLs found, including not visited
        self.queue: list[tuple[str, int]] = [(start_url, 0)]
        self.current_url = ""
        self.screenshot_ts = 0
        self.screenshot_count = 0
        self.status = "idle"
        self.session_id = ""
        self.should_stop = False
        self.ai_calls_used = 0
        self.started_at = datetime.utcnow().isoformat()
        parsed = urlparse(start_url)
        parts = parsed.netloc.split(".")
        self.base_domain = ".".join(parts[-2:]) if len(parts) >= 2 else parsed.netloc

    def screenshot_path(self, n: int | None = None) -> str:
        if n is None:
            n = self.screenshot_count
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
                if not netloc.endswith(self.base_domain):
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
                    print(f"[crawler] visiting depth={depth} page={len(self.visited)+1} url={url}", flush=True)

                    try:
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    except Exception:
                        print(f"[crawler] fallback to commit: {url}", flush=True)
                        await page.goto(url, timeout=30000, wait_until="commit")

                    await asyncio.sleep(1.5)

                    self.screenshot_count += 1
                    idx = self.screenshot_count
                    try:
                        # Save indexed screenshot
                        await page.screenshot(path=self.screenshot_path(idx), full_page=False, timeout=10000)
                        # Also save as latest for live preview
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

                    if depth < self.max_depth:
                        use_ai = self.ai_calls_used < MAX_AI_CALLS
                        if use_ai:
                            self.ai_calls_used += 1
                            print(f"[crawler] gemini call #{self.ai_calls_used}", flush=True)
                            ai_links = await discover_links(page, url)
                            # Insert in reverse so Gemini's first (deepest) link is at queue front
                            for link in reversed(ai_links):
                                normalized = link.split("#")[0].rstrip("/")
                                if normalized:
                                    self.discovered.add(normalized)
                                    if normalized not in self.visited:
                                        self.queue.insert(0, (normalized, depth + 1))
                        else:
                            # Budget exhausted — href-only but filtered to same URL-path prefix
                            # so we don't flood the queue with unrelated breadth links
                            current_path = urlparse(url).path.rstrip("/")
                            links = await page.eval_on_selector_all("a[href]", "els => els.map(el => el.href)")
                            for link in links:
                                normalized = link.split("#")[0].rstrip("/")
                                if not normalized:
                                    continue
                                parsed_link = urlparse(normalized)
                                if not parsed_link.netloc.endswith(self.base_domain):
                                    continue
                                link_path = parsed_link.path.rstrip("/")
                                # Only queue links that go deeper in the same section
                                if link_path.startswith(current_path + "/"):
                                    self.discovered.add(normalized)
                                    if normalized not in self.visited:
                                        self.queue.insert(0, (normalized, depth + 1))
                    else:
                        # At max depth — log hrefs as discovered but don't queue
                        links = await page.eval_on_selector_all("a[href]", "els => els.map(el => el.href)")
                        for link in links:
                            normalized = link.split("#")[0].rstrip("/")
                            if normalized:
                                self.discovered.add(normalized)

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

        # Save final report to disk
        report = self.export()
        report_path = os.path.join(SCREENSHOT_DIR, f"{self.session_id}_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[crawler] done. visited={len(self.visited)} screenshots={self.screenshot_count}", flush=True)
        self.status = "done"
