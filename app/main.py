import threading
from app.worker import Worker
from fastapi import FastAPI
from app.results import router as results_router
from app.status import router as job_status_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="S-Gen Worker",
        version="0.1.0",
        description="S-Gen worker app",
    )

    app.include_router(results_router)
    app.include_router(job_status_router)

    @app.on_event("startup")
    def start_worker():
        worker = Worker()
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

    return app

app = create_app()
