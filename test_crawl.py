import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("https://kapaldo.com/crawler", wait_until="networkidle")
        await asyncio.sleep(2)
        await page.get_by_role("button", name="Start Crawl").click()
        print("Clicked Start Crawl")
        await asyncio.sleep(6)
        await page.screenshot(path="screenshot-after-click.png", full_page=False)
        print("Screenshot saved")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(main())
