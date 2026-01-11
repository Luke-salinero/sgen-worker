from pathlib import Path
import json


def ensure_job_dir(jobs_root: Path, job_id: str) -> Path:
    job_dir = jobs_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())
