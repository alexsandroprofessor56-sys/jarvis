"""tests/test_self_restarter.py"""
import os
import tempfile
import json
from agent.self_restarter import SelfRestarter

def test_save_and_load_state():
    with tempfile.TemporaryDirectory() as tmp:
        restarter = SelfRestarter(state_dir=tmp)
        state = {"reminders": [], "episodes_since_start": 5, "last_command": "test"}
        restarter.save_state(state)
        loaded = restarter.load_state()
        assert loaded["last_command"] == "test"
        assert loaded["episodes_since_start"] == 5

def test_is_structural_change():
    restarter = SelfRestarter()
    assert restarter.is_structural_change(["core/orchestrator.py"])
    assert restarter.is_structural_change(["agent/agent.py"])
    assert not restarter.is_structural_change(["agent/planner.py"])
    assert restarter.is_structural_change(["main.py"])
    assert not restarter.is_structural_change(["config/settings.py"])

def test_clear_state():
    with tempfile.TemporaryDirectory() as tmp:
        restarter = SelfRestarter(state_dir=tmp)
        restarter.save_state({"test": True})
        assert os.path.exists(os.path.join(tmp, "state.json"))
        restarter.clear_state()
        assert not os.path.exists(os.path.join(tmp, "state.json"))
