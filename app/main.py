from fastapi import FastAPI
from threading import Thread
from .api import router, queue
from .executor import executor_loop

app = FastAPI(title="sgen-worker")
app.include_router(router)


@app.on_event("startup")
def start_executor():
    Thread(target=executor_loop, args=(queue,), daemon=True).start()
