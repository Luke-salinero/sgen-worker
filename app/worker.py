import time
import logging
import os
import json
import subprocess
from pathlib import Path

from app.postgres_job_store import PostgresJobStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sgen-worker")


class Worker:
    def __init__(self, poll_interval_seconds: float = 1.0):
        self.worker_id = os.getenv("WORKER_ID", "worker-local")
        self.poll_interval_seconds = poll_interval_seconds
        self.store = PostgresJobStore()

    def run(self) -> None:
        logger.info("sgen-worker started", extra={"worker_id": self.worker_id})

        jobs_root = Path(os.getenv("SGEN_JOBS_ROOT", "/tmp/sgen_jobs"))
        engine_path = os.getenv("SGEN_ENGINE_PATH")

        if not engine_path:
            raise RuntimeError("SGEN_ENGINE_PATH is not set")

        jobs_root.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                job = self.store.claim_next_pending_job(worker_id=self.worker_id)

                if not job:
                    time.sleep(self.poll_interval_seconds)
                    continue

                job_id = job["job_id"]
                mode = job.get("mode", "live")
                payload = job.get("payload")

                logger.info("Claimed job", extra={"job_id": job_id, "mode": mode})

                # payload might already be a dict (jsonb), but be defensive
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if not isinstance(payload, dict):
                    raise RuntimeError(f"job.payload is not an object/dict (type={type(payload)})")

                job_dir = jobs_root / str(job_id)
                results_dir = job_dir / "results"
                results_dir.mkdir(parents=True, exist_ok=True)

                config_path = job_dir / "config.json"
                config_path.write_text(json.dumps(payload, indent=2))

                logger.info(
                    "Starting engine",
                    extra={"job_id": job_id, "engine_path": engine_path, "cwd": str(job_dir)},
                )

                proc = subprocess.run(
                    [engine_path],
                    cwd=str(job_dir),
                    capture_output=True,
                    text=True,
                )

                if proc.returncode != 0:
                    error = {
                        "returncode": proc.returncode,
                        "stderr": (proc.stderr or "").strip(),
                        "stdout": (proc.stdout or "").strip(),
                    }
                    self.store.set_job_failed(job_id=str(job_id), error=error)
                    logger.error("Engine failed", extra={"job_id": job_id, "returncode": proc.returncode})
                    continue

                # Prefer engine-produced outputs if present
                public_results = results_dir / "public_results.json"
                public_summary = results_dir / "public_summary.json"

                if public_results.exists():
                    result = json.loads(public_results.read_text())
                elif public_summary.exists():
                    result = json.loads(public_summary.read_text())
                else:
                    # fallback: at least return captured stdout/stderr
                    result = {
                        "stdout": (proc.stdout or "").strip(),
                        "stderr": (proc.stderr or "").strip(),
                        "note": "engine did not write results files; returned captured output",
                    }

                self.store.set_job_completed(job_id=str(job_id), result=result)
                logger.info("Completed job", extra={"job_id": job_id})

            except Exception as exc:
                logger.exception("Worker loop error", extra={"error": str(exc)})
                time.sleep(1.0)
