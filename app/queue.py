from collections import deque
from threading import Lock


class JobQueue:
    def __init__(self):
        self._queue = deque()
        self._running: str | None = None
        self._lock = Lock()

    def enqueue(self, job_id: str):
        with self._lock:
            if job_id not in self._queue:
                self._queue.append(job_id)

    def start_next(self) -> str | None:
        with self._lock:
            if self._running is None and self._queue:
                self._running = self._queue.popleft()
                return self._running
            return None

    def finish(self):
        with self._lock:
            self._running = None

    def status(self):
        with self._lock:
            return self._running, list(self._queue)
