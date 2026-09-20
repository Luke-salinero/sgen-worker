# sgen-worker

Runs the SGen compute engine and serves job status/results. Not exposed to
the internet directly — `sgen-gateway` is the only intended caller.

## What this service does

- **Background loop** (`app/worker.py`, started on FastAPI startup): claims
  the oldest `pending` job from Postgres (`sgen-controller`'s `jobs` table,
  via `FOR UPDATE SKIP LOCKED`), writes its payload to
  `$SGEN_JOBS_ROOT/<job_id>/config.json`, and runs the compute engine
  (`$SGEN_ENGINE_PATH`) as a subprocess with that directory as its cwd.
  Marks the job `completed`/`failed` in Postgres based on the engine's exit
  code and whatever result files it wrote.
- **HTTP API** (`app/status.py`, `app/results.py`): serves progress and
  results back to `sgen-gateway`, reading the engine's
  `results/public_summary.json` / `results/results_gpu0.json` output files
  plus the job row in Postgres.

## Repository structure

- `app/worker.py` — the claim/execute/complete loop (`Worker.run()`)
- `app/status.py`, `app/results.py` — `GET /status/{job_id}`, `GET /results/{job_id}`
- `app/postgres_job_store.py` — job reads/writes, including the
  ownership-scoped `get_job_for_owner()` used by both HTTP routes
- `app/db/session.py` — SQLAlchemy engine/session from `DATABASE_URL`
- `app/main.py` — FastAPI app; starts the worker loop in a background thread on startup

`app/executor.py` was removed: it referenced `.queue`/`.storage`/`.settings`
modules from an earlier, pre-Postgres design that no longer exist in this
repo, and was never imported by anything.

## API endpoints

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| `GET`  | `/status/{job_id}` | `Api-Key-Owner` header | Progress summary (percent complete, ETA, GCPS) or, once completed, a summary plus up to `example_count` example candidates. 404 if the job doesn't exist *or* isn't owned by the given owner. |
| `GET`  | `/results/{job_id}` | `Api-Key-Owner` header | Full `results_gpu0.json` once the job is `completed`. |

Every query is scoped by `api_key_owner` at the SQL level
(`WHERE job_id = :job_id AND api_key_owner = :api_key_owner`) — `sgen-gateway`
sets this header from the caller's entitlement-resolved `subject_id`, never
from anything the client sends directly.

## Configuration

| Variable | Required | Purpose |
| -------- | -------- | ------- |
| `DATABASE_URL` | yes | Postgres connection string (same database as `sgen-controller`). |
| `SGEN_ENGINE_PATH` | yes | Path to the compute engine executable; the worker loop raises on startup if unset. |
| `SGEN_JOBS_ROOT` | no (default `/tmp/sgen_jobs`) | Per-job working directory root; each job gets `<root>/<job_id>/`. |
| `WORKER_ID` | no (default `worker-local`) | Identifier recorded on claimed jobs. |

## Running locally

```bash
python -m venv .venv
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/sgen
export SGEN_ENGINE_PATH=/path/to/engine
uvicorn app.main:app --reload
```
