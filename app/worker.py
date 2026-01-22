import time
import logging
import os

from app.postgres_job_store import PostgresJobStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sgen-worker")


class Worker:
    def __init__(self, poll_interval_seconds: float = 1.0):
        self.worker_id = os.getenv("WORKER_ID", "worker-local")
        self.poll_interval_seconds = poll_interval_seconds
        self.store = PostgresJobStore()

    def run(self) -> None:
        logger.info(
            "sgen-worker started",
            extra={"worker_id": self.worker_id},
        )

        while True:
            try:
                job = self.store.claim_next_pending_job(
                    worker_id=self.worker_id
                )

                if not job:
                    time.sleep(self.poll_interval_seconds)
                    continue

                # job is a DICT returned from Postgres
                job_id = job["job_id"]
                mode = job["mode"]
                payload = job["payload"]

                logger.info(
                    "Claimed job",
                    extra={
                        "job_id": job_id,
                        "mode": mode,
                    },
                )

                # TEMPORARY fake execution
                result = {
                    "message": "executed by sgen-worker",
                    "worker_id": self.worker_id,
                    "payload": payload,
                }

                self.store.set_job_completed(
                    job_id=job_id,
                    result=result,
                )

                logger.info(
                    "Completed job",
                    extra={"job_id": job_id},
                )

            except Exception as exc:
                logger.exception(
                    "Worker loop error",
                    extra={"error": str(exc)},
                )
                time.sleep(1.0)
