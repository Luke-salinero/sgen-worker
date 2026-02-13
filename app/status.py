import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Query

from app.postgres_job_store import PostgresJobStore

router = APIRouter(tags=["status"])
store = PostgresJobStore()

@router.get("/status/{job_id}")
async def status(
    job_id: str,
    api_key_owner: str = Header(..., alias="Api-Key-Owner"),
    example_count: int = Query(1, ge=1, le=50),
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


    if summary["status"] != "completed":
        total_unrounded = int(summary["processed"]) / int(summary["total_work"]) * 100
        percentage = str(round(total_unrounded, 2)) + "%"
        public_summary_returned = {
            "job_id": job_id,
            "status": summary["status"],
            "found": summary["found"],
            "percent complete": percentage,
            "runtime": str(round(summary["runtime_seconds"],2)) + "s",
            "ETA": str(round(summary["eta_seconds"],2)) + "s",
            "GCPS": str(round(summary["gcps_total"],2)),
        }
    else:
        public_summary_returned = {
            "job_id": job_id,
            "status": summary["status"],
            "found": summary["found"],
            "runtime": str(round(summary["runtime_seconds"], 2)) + "s",
            "total work": summary["total_work"],
            "total valid candidates": summary["total_valid_candidates"],
        }

        public_results_path = results_dir / "results_gpu0.json"
        if not public_results_path.exists():
            public_summary_returned["example valid candidates"] = [summary["example_valid_candidate"]]
            return public_summary_returned

        try:
            result_summary = json.loads(public_results_path.read_text())
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="public_results.json is not valid JSON")

        all_examples = result_summary.get("valid_candidates", [])
        examples = all_examples[:example_count]
        if example_count == 1:
            public_summary_returned["example valid candidates"] = (
                examples[0] if examples else None
            )
        else:
            public_summary_returned["example valid candidates"] = examples

    return public_summary_returned
