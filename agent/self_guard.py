"""agent/self_guard.py"""
import os
import time
import json
import threading

EVOLVE_LOCK_PATH = os.path.expanduser("~/.jarvis/evolve.lock")

ALLOWED_PATHS = [
    os.path.expanduser("~/jarvis"),
]

ALLOWED_EXTENSIONS = (".py", ".json", ".txt", ".md", ".cfg", ".conf")

BLOCKED_DIRS = [".git", "__pycache__", ".state", "node_modules", ".venv"]

ALLOWED_FILES = [
    os.path.expanduser("~/.config/systemd/user/jarvis.service"),
    os.path.expanduser("~/.bashrc"),
    os.path.expanduser("~/.zshrc"),
]

RISK_LOW = ("low",)
RISK_MEDIUM = ("medium",)
RISK_HIGH = ("high",)


class SelfGuard:
    def __init__(self, max_changes: int = 5, window_seconds: int = 3600, lock_path: str = EVOLVE_LOCK_PATH):
        self.max_changes = max(max_changes, 1)
        self.window_seconds = max(window_seconds, 1)
        self.lock_path = lock_path
        self._lock = threading.Lock()
        self._change_times = []
        self._file_lock_held = False

    def is_allowed(self, filepath: str) -> bool:
        abspath = os.path.abspath(filepath)
        if os.path.basename(abspath) == "self_guard.py":
            return False
        for block in BLOCKED_DIRS:
            if f"/{block}/" in abspath + "/":
                return False
        ext = os.path.splitext(abspath)[1]
        if ext and ext not in ALLOWED_EXTENSIONS:
            return False
        if abspath in ALLOWED_FILES:
            return True
        for allowed in ALLOWED_PATHS:
            allowed_abs = os.path.abspath(allowed)
            if not allowed_abs.endswith("/"):
                allowed_abs += "/"
            if abspath.startswith(allowed_abs):
                return True
        return False

    def can_evolve(self) -> bool:
        if self.max_changes <= 0:
            return False
        with self._lock:
            now = time.time()
            self._change_times = [t for t in self._change_times if now - t < self.window_seconds]
            return len(self._change_times) < self.max_changes

    def record_change(self):
        with self._lock:
            self._change_times.append(time.time())

    def acquire_lock(self) -> bool:
        if self._file_lock_held:
            return False
        while True:
            try:
                with open(self.lock_path, "x") as f:
                    f.write(str(os.getpid()))
                self._file_lock_held = True
                return True
            except FileExistsError:
                try:
                    with open(self.lock_path) as f:
                        pid = int(f.read().strip())
                    try:
                        os.kill(pid, 0)
                        return False
                    except (OSError, ProcessLookupError):
                        os.remove(self.lock_path)
                        continue
                except (ValueError, OSError):
                    try:
                        os.remove(self.lock_path)
                    except OSError:
                        pass
                    continue

    def release_lock(self):
        self._file_lock_held = False
        try:
            if os.path.exists(self.lock_path):
                with open(self.lock_path) as f:
                    content = f.read().strip()
                if content == str(os.getpid()):
                    os.remove(self.lock_path)
        except OSError:
            pass

    def is_allowed_dependency(self, package: str, risk: str) -> bool:
        if risk in RISK_HIGH:
            return False
        if risk in RISK_MEDIUM:
            return True
        return True
