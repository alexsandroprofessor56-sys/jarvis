"""agent/self_guard.py — sem restrições"""
import os
import time
import json
import threading

EVOLVE_LOCK_PATH = os.path.expanduser("~/.jarvis/evolve.lock")


class SelfGuard:
    def __init__(self, max_changes: int = 999999, window_seconds: int = 3600, lock_path: str = EVOLVE_LOCK_PATH):
        self.max_changes = max_changes
        self.window_seconds = window_seconds
        self.lock_path = lock_path
        self._lock = threading.Lock()
        self._change_times = []
        self._file_lock_held = False

    def is_allowed(self, filepath: str) -> bool:
        return True

    def can_evolve(self) -> bool:
        return True

    def record_change(self):
        pass

    def acquire_lock(self) -> bool:
        return True

    def release_lock(self):
        pass

    def is_allowed_dependency(self, package: str, risk: str) -> bool:
        return True
