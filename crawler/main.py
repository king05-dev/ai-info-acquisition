import asyncio
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from crawler import Crawler

app = FastAPI(title="AI Info Acquisition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kapaldo.com", "https://www.kapaldo.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_crawls: dict[str, Crawler] = {}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            crawler = active_crawls.get(session_id)
            if crawler:
                await websocket.send_text(json.dumps(crawler.snapshot()))
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


@app.post("/start")
async def start_crawl(payload: dict):
    url = payload.get("url")
    session_id = payload.get("session_id", "default")
    if not url:
        return JSONResponse({"error": "url required"}, status_code=400)

    crawler = Crawler(url, max_depth=6)
    active_crawls[session_id] = crawler
    asyncio.create_task(crawler.run())
    return {"session_id": session_id, "status": "started"}


@app.get("/results/{session_id}")
async def get_results(session_id: str):
    crawler = active_crawls.get(session_id)
    if not crawler:
        return JSONResponse({"error": "session not found"}, status_code=404)
    return crawler.export()


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
