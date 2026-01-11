from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class JobSubmitRequest(BaseModel):
    job_id: str
    config: Dict[str, Any]


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    summary: Optional[Dict[str, Any]] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class QueueStatusResponse(BaseModel):
    running: Optional[str]
    queue: List[str]
