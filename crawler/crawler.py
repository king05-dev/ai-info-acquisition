import asyncio
import os
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from ai_discovery import discover_links

SCREENSHOT_DIR = "/tmp/crawler_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class Crawler:
    def __init__(self, start_url: str, max_depth: int = 6):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited: dict[str, dict] = {}
        self.queue: list[tuple[str, int]] = [(start_url, 0)]
        self.current_url = ""
        self.screenshot_ts = 0
        self.status = "idle"
        self.session_id = ""
        parsed = urlparse(start_url)
        parts = parsed.netloc.split(".")
        self.base_domain = ".".join(parts[-2:]) if len(parts) >= 2 else parsed.netloc

    def screenshot_path(self) -> str:
        return os.path.join(SCREENSHOT_DIR, f"{self.session_id}.png")

    def snapshot(self) -> dict:
        return {
            "status": self.status,
            "current_url": self.current_url,
            "screenshot_ts": self.screenshot_ts,
            "visited_count": len(self.visited),
            "max_depth_reached": max((v["depth"] for v in self.visited.values()), default=0),
            "queue_remaining": len(self.queue),
        }

    def export(self) -> dict:
        return {
            "start_url": self.start_url,
            "total_visited": len(self.visited),
            "max_depth": max((v["depth"] for v in self.visited.values()), default=0),
            "visited": [
                {"url": url, "depth": data["depth"], "title": data["title"]}
                for url, data in self.visited.items()
            ],
        }

    async def run(self):
        self.status = "running"
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            while self.queue:
                url, depth = self.queue.pop(0)

                if url in self.visited or depth > self.max_depth:
                    continue

                netloc = urlparse(url).netloc
                if not netloc.endswith(self.base_domain):
                    continue

                try:
                    self.current_url = url

                    try:
                        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                    except Exception:
                        await page.goto(url, timeout=45000, wait_until="commit")

                    await asyncio.sleep(1.5)

                    # Save screenshot to disk
                    try:
                        await page.screenshot(
                            path=self.screenshot_path(),
                            full_page=False,
                            timeout=10000
                        )
                        self.screenshot_ts = int(datetime.utcnow().timestamp())
                    except Exception:
                        pass

                    title = await page.title()
                    self.visited[url] = {
                        "depth": depth,
                        "title": title,
                        "visited_at": datetime.utcnow().isoformat(),
                    }

                    if depth <= 2:
                        ai_links = await discover_links(page, url)
                        for link in ai_links:
                            normalized = link.split("#")[0].rstrip("/")
                            if normalized and normalized not in self.visited:
                                self.queue.insert(0, (normalized, depth + 1))

                    links = await page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(el => el.href)"
                    )
                    for link in links:
                        normalized = link.split("#")[0].rstrip("/")
                        if normalized and normalized not in self.visited:
                            self.queue.append((normalized, depth + 1))

                except Exception as e:
                    self.visited[url] = {
                        "depth": depth,
                        "title": f"ERROR: {str(e)[:120]}",
                        "visited_at": datetime.utcnow().isoformat(),
                    }

            await browser.close()
        self.status = "done"
