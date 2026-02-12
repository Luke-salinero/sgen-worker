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

    if not (store.job_completed_and_owned(job_id=job_id, api_key_owner=api_key_owner)):
        raise HTTPException(status_code=404, detail="Job not found or not completed")

    jobs_root = Path(os.getenv("SGEN_JOBS_ROOT", "/tmp/sgen_jobs"))
    public_results_path = jobs_root / str(job_id) / "results" / "public_results.json"

    if not public_results_path.exists():
        raise HTTPException(status_code=500, detail="public_results.json missing for completed job")

    try:
        return json.loads(public_results_path.read_text())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="public_results.json is not valid JSON")
