import json
import os
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException

from app.postgres_job_store import PostgresJobStore

router = APIRouter(tags=["results"])
store = PostgresJobStore()

@router.get("/results/{job_id}")
async def results(
    job_id: str,
    api_key_owner: str = Header(..., alias="Api-Key-Owner"),
):

    job = store.get_job_for_owner(
        job_id=job_id,
        api_key_owner=api_key_owner
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_status = job.get("status")

    jobs_root = Path(os.getenv("SGEN_JOBS_ROOT", "/tmp/sgen_jobs"))
    results_dir = jobs_root / str(job_id) / "results"

    if job_status == "pending" or job_status == "failed":
        return {"job_id": job_id, "job_status": "pending"}

    if job_status == "completed":
        public_results_path = results_dir / "public_results.json"
        if not public_results_path.exists():
            raise HTTPException(
                status_code=500,
                detail="public_results.json missing for completed job",
            )
        return json.loads(public_results_path.read_text())

    raise HTTPException(
        status_code=500,
        detail=f"Unknown job status: {job_status}"
    )
