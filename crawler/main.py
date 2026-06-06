import asyncio
import json
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from crawler import Crawler, SCREENSHOT_DIR

app = FastAPI(title="AI Info Acquisition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kapaldo.com",
        "https://www.kapaldo.com",
        "https://ai-info-acquisition-production.up.railway.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_crawls: dict[str, Crawler] = {}


@app.get("/")
async def root():
    return {"service": "AI Info Acquisition", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/start")
async def start_crawl(payload: dict):
    url = payload.get("url")
    session_id = payload.get("session_id", "default")
    if not url:
        return JSONResponse({"error": "url required"}, status_code=400)

    crawler = Crawler(url, max_depth=6)
    crawler.session_id = session_id
    active_crawls[session_id] = crawler
    asyncio.create_task(crawler.run())
    return {"session_id": session_id, "status": "started"}


@app.post("/stop/{session_id}")
async def stop_crawl(session_id: str):
    crawler = active_crawls.get(session_id)
    if not crawler:
        return JSONResponse({"error": "session not found"}, status_code=404)
    crawler.should_stop = True
    return {"session_id": session_id, "status": "stopping"}


@app.get("/status/{session_id}")
async def get_status(session_id: str):
    crawler = active_crawls.get(session_id)
    if not crawler:
        return JSONResponse({"error": "session not found"}, status_code=404)
    return crawler.snapshot()


@app.get("/screenshot/{session_id}/latest")
async def get_latest_screenshot(session_id: str):
    path = os.path.join(SCREENSHOT_DIR, f"{session_id}_latest.png")
    if not os.path.exists(path):
        return JSONResponse({"error": "no screenshot yet"}, status_code=404)
    return FileResponse(path, media_type="image/png")


@app.get("/screenshot/{session_id}/{n}")
async def get_screenshot(session_id: str, n: int):
    path = os.path.join(SCREENSHOT_DIR, f"{session_id}_page_{n}.png")
    if not os.path.exists(path):
        return JSONResponse({"error": "screenshot not found"}, status_code=404)
    return FileResponse(path, media_type="image/png")


@app.get("/results/{session_id}")
async def get_results(session_id: str):
    # Try saved report first
    report_path = os.path.join(SCREENSHOT_DIR, f"{session_id}_report.json")
    if os.path.exists(report_path):
        with open(report_path) as f:
            return json.load(f)
    # Fall back to live export
    crawler = active_crawls.get(session_id)
    if not crawler:
        return JSONResponse({"error": "session not found"}, status_code=404)
    return crawler.export()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
