from pydantic import BaseModel
from functools import lru_cache
import os


class Settings(BaseModel):
    worker_token: str
    jobs_root: str = "/home/brian/sgen_worker/jobs"
    engine_path: str = "/home/brian/s_gen/build/s_gen"
    poll_interval_ms: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings(
        worker_token=os.environ["SGEN_WORKER_TOKEN"],
    )
