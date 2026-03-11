import uuid
import shutil
from typing import Dict, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger

from src.engine import run_ophthalmo_agent
from src.config import settings

app = FastAPI(title="EyeArticle PRO API")

# CORS - allow Vercel domain and local dev
# Set ALLOWED_ORIGINS env var in production, e.g.:
# "https://your-app.vercel.app,https://your-custom-domain.com"
import os
_origins_env = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jobs storage (in-memory)
# In production, use Redis or a Database for persistence across restarts
jobs: Dict[str, Dict] = {}


class ResearchRequest(BaseModel):
    url: str
    disease_label: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    result: Optional[Dict] = None


def background_research_task(job_id: str, url: str, disease_label: Optional[str] = None):
    def update_job_progress(text: str, value: float):
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = value
        jobs[job_id]["message"] = text

    try:
        result = run_ophthalmo_agent(
            pdf_url=url,
            disease_label=disease_label,
            progress_callback=update_job_progress
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Pesquisa concluída com sucesso."
        jobs[job_id]["result"] = result
    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Erro: {str(e)}"


@app.post("/api/research", response_model=Dict[str, str])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Na fila de processamento...",
        "result": None
    }
    background_tasks.add_task(background_research_task, job_id, request.url, request.disease_label)
    return {"job_id": job_id}


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


class MoveRequest(BaseModel):
    job_id: str
    area_name: str


@app.post("/api/save-to-area")
async def save_to_area(request: MoveRequest):
    if request.job_id not in jobs or jobs[request.job_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job não encontrado ou não concluído")

    job = jobs[request.job_id]
    old_safe_name = job["result"]["safe_name"]
    new_area_safe = request.area_name.lower().replace(" ", "_")
    paper_hash = old_safe_name.split("/")[-1]
    new_safe_name = f"{new_area_safe}/{paper_hash}"

    if old_safe_name == new_safe_name:
        return {"status": "already_saved", "safe_name": new_safe_name}

    try:
        if settings.use_cloud_storage:
            import src.storage as storage
            storage.move_prefix(old_safe_name, new_safe_name)
        else:
            old_path = settings.output_dir / old_safe_name
            new_path = settings.output_dir / new_area_safe / paper_hash
            new_path.parent.mkdir(parents=True, exist_ok=True)
            if old_path.exists():
                shutil.move(str(old_path), str(new_path))

        job["result"]["safe_name"] = new_safe_name
        return {"status": "success", "safe_name": new_safe_name}
    except Exception as e:
        logger.error(f"Failed to move folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "storage": "vercel_blob" if settings.use_vercel_blob else ("r2" if settings.use_r2 else "local"),
    }


# Serve output directory for images (local dev / fallback when no cloud storage configured)
if not settings.use_cloud_storage:
    if not settings.output_dir.exists():
        settings.output_dir.mkdir(parents=True)
    app.mount("/api/outputs", StaticFiles(directory=str(settings.output_dir)), name="outputs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
