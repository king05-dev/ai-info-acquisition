import asyncio
import base64
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from ai_discovery import discover_links


class Crawler:
    def __init__(self, start_url: str, max_depth: int = 6):
        self.start_url = start_url
        self.max_depth = max_depth
        self.visited: dict[str, dict] = {}
        self.queue: list[tuple[str, int]] = [(start_url, 0)]
        self.current_url = ""
        self.current_screenshot = ""
        self.status = "idle"
        self.base_domain = urlparse(start_url).netloc

    def snapshot(self) -> dict:
        return {
            "status": self.status,
            "current_url": self.current_url,
            "current_screenshot": self.current_screenshot,
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
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            while self.queue:
                url, depth = self.queue.pop(0)

                if url in self.visited or depth > self.max_depth:
                    continue

                if urlparse(url).netloc != self.base_domain:
                    continue

                try:
                    self.current_url = url
                    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    await asyncio.sleep(0.8)

                    screenshot_bytes = await page.screenshot(full_page=False)
                    self.current_screenshot = base64.b64encode(screenshot_bytes).decode()

                    title = await page.title()
                    self.visited[url] = {
                        "depth": depth,
                        "title": title,
                        "screenshot_b64": self.current_screenshot,
                        "visited_at": datetime.utcnow().isoformat(),
                    }

                    # AI-driven discovery for shallow levels to catch JS-rendered nav
                    if depth <= 2:
                        ai_links = await discover_links(page, url)
                        for link in ai_links:
                            normalized = link.split("#")[0].rstrip("/")
                            if normalized and normalized not in self.visited:
                                self.queue.insert(0, (normalized, depth + 1))

                    # Standard link extraction for all levels
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
                        "title": f"ERROR: {str(e)}",
                        "screenshot_b64": "",
                        "visited_at": datetime.utcnow().isoformat(),
                    }

            await browser.close()
        self.status = "done"
