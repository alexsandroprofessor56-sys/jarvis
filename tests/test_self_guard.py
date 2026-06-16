"""tests/test_self_guard.py"""
import os
import time

from agent.self_guard import SelfGuard

def test_guard_allows_valid_path():
    guard = SelfGuard()
    assert guard.is_allowed(os.path.expanduser("~/jarvis/core/tools.py"))

def test_guard_blocks_outside_path():
    guard = SelfGuard()
    assert not guard.is_allowed("/etc/passwd")
    assert not guard.is_allowed("/home/user/secret.key")
    assert not guard.is_allowed("../outside.py")

def test_guard_rate_limit():
    guard = SelfGuard(max_changes=3, window_seconds=3600)
    for i in range(3):
        assert guard.can_evolve()
        guard.record_change()
    assert not guard.can_evolve()

def test_guard_lock():
    guard = SelfGuard()
    assert guard.acquire_lock()
    assert not guard.acquire_lock()  # second should fail
    guard.release_lock()
    assert guard.acquire_lock()  # should work again

def test_guard_risk_high_block():
    guard = SelfGuard()
    assert guard.is_allowed_dependency("requests", "low")
    assert guard.is_allowed_dependency("tensorflow", "medium")
    assert not guard.is_allowed_dependency("malicious", "high")
