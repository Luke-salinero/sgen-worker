import subprocess
import time
from pathlib import Path
from .queue import JobQueue
from .storage import write_json
from .settings import get_settings


def executor_loop(queue: JobQueue):
    settings = get_settings()
    jobs_root = Path(settings.jobs_root)

    while True:
        job_id = queue.start_next()
        if not job_id:
            time.sleep(settings.poll_interval_ms / 1000)
            continue

        job_dir = jobs_root / job_id
        results_dir = job_dir / "results"
        results_dir.mkdir(exist_ok=True)

        try:
            proc = subprocess.run(
                [settings.engine_path],
                cwd=job_dir,
                capture_output=True,
                text=True,
            )

            if proc.returncode != 0:
                write_json(
                    results_dir / "public_summary.json",
                    {
                        "status": "failed",
                        "error": proc.stderr.strip(),
                    },
                )
            # engine itself writes public_results.json

        except Exception as exc:
            write_json(
                results_dir / "public_summary.json",
                {
                    "status": "failed",
                    "error": str(exc),
                },
            )
        finally:
            queue.finish()
