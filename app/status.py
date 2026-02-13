import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException

from app.postgres_job_store import PostgresJobStore

router = APIRouter(tags=["status"])
store = PostgresJobStore()

@router.get("/status/{job_id}")
async def status(
    job_id: str,
    api_key_owner: str = Header(..., alias="Api-Key-Owner"),
) -> Dict[str, Any]:
    job = store.get_job_for_owner(job_id=job_id, api_key_owner=api_key_owner)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status_val = job.get("status")

    if status_val == "failed":
        return {
            "job_id": job_id,
            "status": "failed",
            "error": job.get("error") or {"message": "job failed"},
        }

    jobs_root = Path(os.getenv("SGEN_JOBS_ROOT", "/tmp/sgen_jobs"))
    results_dir = jobs_root / str(job_id) / "results"
    public_summary_path = results_dir / "public_summary.json"

    if not public_summary_path.exists():
        return {
            "job_id": job_id,
            "status": status_val,
            "note": "public_summary.json not available yet",
        }

    try:
        summary = json.loads(public_summary_path.read_text())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="public_summary.json is not valid JSON")

    if isinstance(summary, dict) and "status" not in summary:
        summary["status"] = status_val
    if isinstance(summary, dict) and "job_id" not in summary:
        summary["job_id"] = job_id

    total_unrounded = int(summary["processed"]) / int(summary["total_work"]) * 100
    percentage = str(round(total_unrounded,2)) + "%"
    if summary["status"] != "completed":
        public_summary_returned = {
            "job_id": job_id,
            "status": summary["status"],
            "found": summary["found"],
            "percent complete": percentage,
            "runtime": summary["runtime_seconds"] + "s",
            "ETA": summary["eta_seconds"] + "s",
            "GCPS": summary["gcps_total"],
        }
    else:
        public_summary_returned = {
            "job_id": job_id,
            "status": summary["status"],
            "found": summary["found"],
            "runtime": summary["runtime_seconds"] + "s",
            "total work": summary["total_work"],
            "total valid candidates": summary["total_valid_candidates"],
            "example valid candidate": summary["example_valid_candidate"],
        }
    return public_summary_returned
