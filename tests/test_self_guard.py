"""tests/test_self_guard.py — sem restrições"""
import os
import time

from agent.self_guard import SelfGuard


def test_guard_allows_valid_path():
    guard = SelfGuard()
    assert guard.is_allowed(os.path.expanduser("~/jarvis/core/tools.py"))


def test_guard_allows_any_path():
    guard = SelfGuard()
    assert guard.is_allowed("/etc/passwd")
    assert guard.is_allowed("/home/user/secret.key")
    assert guard.is_allowed("../outside.py")


def test_guard_no_rate_limit():
    guard = SelfGuard(max_changes=3, window_seconds=3600)
    for i in range(100):
        assert guard.can_evolve()
        guard.record_change()


def test_guard_lock():
    guard = SelfGuard()
    assert guard.acquire_lock()
    assert guard.acquire_lock()  # always succeeds
    guard.release_lock()
    assert guard.acquire_lock()


def test_guard_risk_allows_all():
    guard = SelfGuard()
    assert guard.is_allowed_dependency("requests", "low")
    assert guard.is_allowed_dependency("tensorflow", "medium")
    assert guard.is_allowed_dependency("malicious", "high")
