import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any, List

from app.config.settings import SettingsManager
from app.database.db_manager import DatabaseManager
from app.extractors.extractor_manager import ExtractorManager
from app.download.queue_manager import QueueManager
from app.core.path_utils import render_filename_template, get_safe_destination_path

app = FastAPI(title="Video Downloader Pro API")

# CORS configuration to allow local development with npm run dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings_mgr = SettingsManager()
db_mgr = DatabaseManager()
extractor_mgr = ExtractorManager()
extractor_mgr.load_all()

queue_mgr = None

@app.on_event("startup")
async def startup_event():
    global queue_mgr
    await db_mgr.initialize()
    queue_mgr = QueueManager(
        db_manager=db_mgr,
        max_concurrent=settings_mgr.settings.concurrent_downloads,
        speed_limit=0,
        chunk_size=settings_mgr.settings.chunk_size,
        retry_count=settings_mgr.settings.retry_count
    )
    queue_mgr.start()

@app.on_event("shutdown")
async def shutdown_event():
    if queue_mgr:
        await queue_mgr.stop()

class AnalyzeRequest(BaseModel):
    url: str

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        extractor = extractor_mgr.get_extractor_for_url(req.url)
        await extractor.analyze(req.url)
        return {
            "title": extractor.get_title(),
            "uploader": extractor.get_uploader(),
            "duration": extractor.get_duration(),
            "thumbnail": extractor.get_thumbnail(),
            "description": extractor.get_description(),
            "formats": extractor.get_available_formats(),
            "url": req.url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class DownloadRequest(BaseModel):
    url: str
    format_id: str

@app.post("/api/download")
async def download(req: DownloadRequest):
    try:
        extractor = extractor_mgr.get_extractor_for_url(req.url)
        await extractor.analyze(req.url)
        formats = extractor.get_available_formats()
        selected_fmt = next((f for f in formats if f["format_id"] == req.format_id), None)
        if not selected_fmt:
            raise HTTPException(status_code=400, detail=f"Format ID {req.format_id} not found.")

        filename = render_filename_template(
            settings_mgr.settings.filename_template,
            {
                "title": extractor.get_title(),
                "uploader": extractor.get_uploader(),
                "upload_date": None,
                "resolution": selected_fmt.get("resolution") or "unknown",
                "ext": selected_fmt.get("ext") or "mp4",
                "id": selected_fmt["format_id"]
            }
        )
        save_path = get_safe_destination_path(settings_mgr.settings.download_dir, filename)

        download_id = await queue_mgr.add_download(
            url=req.url,
            title=extractor.get_title(),
            save_path=str(save_path),
            format_id=selected_fmt["format_id"],
            thumbnail_url=extractor.get_thumbnail(),
            duration=extractor.get_duration(),
            resolution=selected_fmt.get("resolution"),
            codec=selected_fmt.get("vcodec"),
            container=selected_fmt.get("ext"),
            headers=selected_fmt.get("headers") or {}
        )
        return {"download_id": download_id, "save_path": str(save_path)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/downloads")
async def list_downloads():
    if not queue_mgr:
        return []
    
    # Get history from DB
    db_history = await db_mgr.get_download_history(limit=50)
    
    # Merge active status/metrics from QueueManager in-memory tasks
    active_tasks = {}
    for task_id, task in queue_mgr.tasks.items():
        active_tasks[task_id] = {
            "status": task.status,
            "progress": task.progress,
            "downloaded_bytes": task.downloaded_bytes,
            "total_bytes": task.total_bytes,
            "speed": task.speed,
            "eta": task.eta,
            "error_message": task.error_message
        }

    results = []
    for row in db_history:
        item = dict(row)
        task_id = item["id"]
        # If active in memory, overwrite/merge metrics
        if task_id in active_tasks:
            item.update(active_tasks[task_id])
        results.append(item)
    return results

@app.post("/api/downloads/{download_id}/pause")
async def pause_download(download_id: int):
    if queue_mgr:
        await queue_mgr.pause_download(download_id)
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="QueueManager not active")

@app.post("/api/downloads/{download_id}/resume")
async def resume_download(download_id: int):
    if queue_mgr:
        await queue_mgr.resume_download(download_id)
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="QueueManager not active")

@app.post("/api/downloads/{download_id}/cancel")
async def cancel_download(download_id: int):
    if queue_mgr:
        await queue_mgr.cancel_download(download_id)
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="QueueManager not active")

@app.get("/api/settings")
async def get_settings():
    return settings_mgr.settings.model_dump()

@app.post("/api/settings")
async def update_settings(settings: Dict[str, Any]):
    try:
        settings_mgr.update(**settings)
        if queue_mgr:
            queue_mgr.max_concurrent = settings_mgr.settings.concurrent_downloads
            queue_mgr.chunk_size = settings_mgr.settings.chunk_size
            queue_mgr.retry_count = settings_mgr.settings.retry_count
        return {"status": "success", "settings": settings_mgr.settings.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Mount static files from React build folder
dist_path = Path(__file__).parent.parent.parent / "web" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
