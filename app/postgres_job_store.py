from contextlib import contextmanager
from typing import Optional, Dict, Any
import json

from sqlalchemy import text

from app.db.session import SessionLocal, engine


class PostgresJobStore:
    """
    Postgres-backed JobStore for sgen-worker.

    This version is intentionally model-free.
    """

    @contextmanager
    def _get_raw_connection(self):
        conn = engine.raw_connection()
        try:
            yield conn
        finally:
            conn.close()

    def claim_next_pending_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the next pending job.

        Returns a dict representing the job row, or None.
        """
        with SessionLocal() as session:
            with session.begin():
                row = session.execute(
                    text("""
                    UPDATE jobs
                    SET
                      status = 'running',
                      worker_id = :worker_id,
                      started_at = COALESCE(started_at, NOW()),
                      updated_at = NOW()
                    WHERE job_id = (
                      SELECT job_id
                      FROM jobs
                      WHERE status = 'pending'
                      ORDER BY created_at ASC
                      LIMIT 1
                      FOR UPDATE SKIP LOCKED
                    )
                    RETURNING *
                    """),
                    {"worker_id": worker_id},
                ).mappings().first()

                return dict(row) if row else None

    def set_job_completed(self, job_id: str, result: Dict[str, Any]) -> None:
        with SessionLocal() as session:
            with session.begin():
                session.execute(
                    text("""
                         UPDATE jobs
                         SET status      = 'completed',
                             result      = :result,
                             finished_at = NOW(),
                             updated_at  = NOW()
                         WHERE job_id = :job_id
                         """),
                    {
                        "job_id": job_id,
                        "result": json.dumps(result),
                    },
                )

    def set_job_failed(self, job_id: str, error: Dict[str, Any]) -> None:
        with SessionLocal() as session:
            with session.begin():
                session.execute(
                    text("""
                         UPDATE jobs
                         SET status      = 'failed',
                             error       = :error,
                             finished_at = NOW(),
                             updated_at  = NOW()
                         WHERE job_id = :job_id
                         """),
                    {
                        "job_id": job_id,
                        "error": json.dumps(error),
                    },
                )
    def get_job_for_owner(self, job_id: str, api_key_owner: str) -> Optional[Dict[str, Any]]:
            """
            Return job row if it belongs to api_key_owner, else None.
            """
            with SessionLocal() as session:
                row = session.execute(
                    text("""
                        SELECT job_id, status, mode, result, error, created_at, updated_at
                        FROM jobs
                        WHERE job_id = :job_id
                        AND api_key_owner = :api_key_owner
                        LIMIT 1
                    """),
                    {"job_id": job_id, "api_key_owner": api_key_owner},
                ).mappings().first()

                if not row:
                    return None

                job = dict(row)

                # result/error stored as JSON strings in your code; decode defensively
                if isinstance(job.get("result"), str) and job["result"]:
                    job["result"] = json.loads(job["result"])
                if isinstance(job.get("error"), str) and job["error"]:
                    job["error"] = json.loads(job["error"])

                return job
    
    def job_belongs_to_owner(self, job_id: str, api_key_owner: str) -> bool:
        """
        Returns True if job_id exists and is owned by api_key_owner, else False.
        """
        with SessionLocal() as session:
            row = session.execute(
                text("""
                    SELECT 1
                    FROM jobs
                    WHERE job_id = :job_id
                        AND api_key_owner = :api_key_owner
                    LIMIT 1
                """),
                {"job_id": job_id, "api_key_owner": api_key_owner},
            ).first()

            return row is not None
