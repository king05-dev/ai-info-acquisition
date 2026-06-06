import asyncio
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from crawler import Crawler, SCREENSHOT_DIR

app = FastAPI(title="AI Info Acquisition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kapaldo.com", "https://www.kapaldo.com", "http://localhost:3000", "https://ai-info-acquisition-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_crawls: dict[str, Crawler] = {}


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


@app.get("/status/{session_id}")
async def get_status(session_id: str):
    crawler = active_crawls.get(session_id)
    if not crawler:
        return JSONResponse({"error": "session not found"}, status_code=404)
    return crawler.snapshot()


@app.get("/screenshot/{session_id}")
async def get_screenshot(session_id: str):
    path = os.path.join(SCREENSHOT_DIR, f"{session_id}.png")
    if not os.path.exists(path):
        return JSONResponse({"error": "no screenshot yet"}, status_code=404)
    return FileResponse(path, media_type="image/png")


@app.get("/results/{session_id}")
async def get_results(session_id: str):
    crawler = active_crawls.get(session_id)
    if not crawler:
        return JSONResponse({"error": "session not found"}, status_code=404)
    return crawler.export()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"service": "AI Info Acquisition", "status": "ok", "endpoints": ["/start", "/status/{session_id}", "/screenshot/{session_id}", "/results/{session_id}"]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
