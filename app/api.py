from fastapi import APIRouter, Depends, Header, HTTPException
from pathlib import Path
from .models import *
from .queue import JobQueue
from .storage import ensure_job_dir, write_json, read_json
from .settings import get_settings

router = APIRouter()
queue = JobQueue()


def auth(token: str = Header(..., alias="X-SGen-Worker-Token")):
    if token != get_settings().worker_token:
        raise HTTPException(status_code=401)


@router.post("/v1/jobs", dependencies=[Depends(auth)])
def submit_job(req: JobSubmitRequest):
    settings = get_settings()
    job_dir = ensure_job_dir(Path(settings.jobs_root), req.job_id)
    write_json(job_dir / "config.json", req.config)
    queue.enqueue(req.job_id)
    return {"job_id": req.job_id, "state": "queued"}


@router.get("/v1/jobs/{job_id}", response_model=JobStatusResponse, dependencies=[Depends(auth)])
def job_status(job_id: str):
    settings = get_settings()
    job_dir = Path(settings.jobs_root) / job_id
    results_dir = job_dir / "results"

    if not job_dir.exists():
        raise HTTPException(404)

    summary = results_dir / "public_summary.json"
    results = results_dir / "public_results.json"

    if summary.exists():
        data = read_json(summary)
        return JobStatusResponse(
            job_id=job_id,
            state=data.get("status", "unknown"),
            summary=data,
            results=read_json(results) if results.exists() else None,
        )

    running, queue_list = queue.status()
    if running == job_id:
        return JobStatusResponse(job_id=job_id, state="running")

    return JobStatusResponse(job_id=job_id, state="queued")
