"""agent/self_versioner.py"""
import os
import subprocess
import time
import shutil


def _run_git(cmd, cwd):
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True, text=True, cwd=cwd, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(cmd)} falhou: {result.stderr[:200]}")
    return result.stdout.strip()


class SelfVersioner:
    def __init__(self, repo_path=None):
        self.repo_path = repo_path or os.path.expanduser("~/jarvis")

    def init_repo(self):
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            _run_git(["init"], self.repo_path)
            _run_git(["config", "user.email", "jarvis@jarvis.local"], self.repo_path)
            _run_git(["config", "user.name", "Jarvis"], self.repo_path)

    def create_branch(self, name_prefix="self-edit") -> str:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        branch = f"{name_prefix}/{timestamp}"
        try:
            _run_git(["checkout", "-b", branch], self.repo_path)
        except RuntimeError:
            _run_git(["checkout", "--orphan", branch], self.repo_path)
        return branch

    def commit_all(self, message: str):
        _run_git(["add", "-A"], self.repo_path)
        try:
            _run_git(["commit", "-m", message], self.repo_path)
        except RuntimeError:
            pass

    def get_current_branch(self) -> str:
        return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], self.repo_path)

    def rollback(self):
        _run_git(["checkout", "--", "."], self.repo_path)

    def has_changes(self) -> bool:
        status = _run_git(["status", "--porcelain"], self.repo_path)
        return bool(status.strip())

    def merge_back(self):
        current = self.get_current_branch()
        main_branch = "main"
        if main_branch not in _run_git(["branch", "--list", main_branch], self.repo_path):
            main_branch = "master"
        _run_git(["checkout", main_branch], self.repo_path)
        try:
            _run_git(["merge", "--no-ff", "-m", f"feat: merge {current}", current], self.repo_path)
        except RuntimeError:
            pass

    def remove_branch(self, branch: str):
        try:
            _run_git(["branch", "-D", branch], self.repo_path)
        except RuntimeError:
            pass
