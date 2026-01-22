from contextlib import contextmanager
from typing import Optional, Dict, Any

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
                    SET
                      status = 'completed',
                      result = :result,
                      finished_at = NOW(),
                      updated_at = NOW()
                    WHERE job_id = :job_id
                    """),
                    {
                        "job_id": job_id,
                        "result": result,
                    },
                )

    def set_job_failed(self, job_id: str, error: Dict[str, Any]) -> None:
        with SessionLocal() as session:
            with session.begin():
                session.execute(
                    text("""
                    UPDATE jobs
                    SET
                      status = 'failed',
                      error = :error,
                      finished_at = NOW(),
                      updated_at = NOW()
                    WHERE job_id = :job_id
                    """),
                    {
                        "job_id": job_id,
                        "error": error,
                    },
                )
