import os
import tempfile
from agent.self_guard import SelfGuard
from agent.self_versioner import SelfVersioner
from agent.self_editor import SelfEditor
from agent.self_evolve import SelfAgent
from agent.self_restarter import SelfRestarter


def test_full_evolution_workflow():
    with tempfile.TemporaryDirectory() as tmp:
        guard = SelfGuard(max_changes=10, window_seconds=3600)
        ver = SelfVersioner(repo_path=tmp)
        editor = SelfEditor(versioner=ver)
        agent = SelfAgent(guard=guard, editor=editor, versioner=ver)
        restarter = SelfRestarter(state_dir=os.path.join(tmp, "state"))
        test_file = os.path.join(tmp, "test_evolve.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        ver.init_repo()
        ver.commit_all("initial")
        assert guard.acquire_lock()
        success, msg = editor.apply_patch(test_file, "x = 1\n", "x = 42\n")
        assert success, msg
        ver.commit_all("feat: evolve test")
        ver.merge_back()
        guard.release_lock()
        with open(test_file) as f:
            assert "x = 42" in f.read()


def test_guard_blocks_overflow():
    guard = SelfGuard(max_changes=1, window_seconds=3600)
    assert guard.can_evolve()
    guard.record_change()
    assert not guard.can_evolve()


def test_versioner_rollback_uncommitted():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        f = os.path.join(tmp, "a.py")
        with open(f, "w") as fh:
            fh.write("v1\n")
        ver.commit_all("v1")
        branch = ver.create_branch("feature")
        with open(f, "w") as fh:
            fh.write("v2\n")
        ver.rollback()
        with open(f) as fh:
            assert fh.read() == "v1\n"
