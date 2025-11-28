# api/tasks/windows_worker.py

from rq.worker import SimpleWorker
from rq.timeouts import BaseDeathPenalty

# A no-op death penalty class to safely replace SIGALRM-based timeouts on Windows
class NoOpDeathPenalty(BaseDeathPenalty):
    def __enter__(self): pass
    def __exit__(self, exc_type, exc_val, exc_tb): pass

# Custom worker class for Windows compatibility
class WindowsWorker(SimpleWorker):
    death_penalty_class = NoOpDeathPenalty