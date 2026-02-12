from app.worker import Worker
from fastapi import FastAPI
from results import results

def create_app() -> FastAPI:
    """Application factory for the S-Gen gateway.

    Exposes the function used to construct and configure the FastAPI app
    """

    app = FastAPI(
        title="S-Gen Worker",
        version="0.1.0",
        description="Worker service for S-Gen.",
    )

    # Routers
    app.include_router(results.router)
    return app

def main():
    app = create_app()
    worker = Worker()
    worker.run()


if __name__ == "__main__":
    main()
