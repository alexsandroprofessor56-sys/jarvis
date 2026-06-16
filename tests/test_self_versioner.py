"""tests/test_self_versioner.py"""
import os
import tempfile
from pathlib import Path
from agent.self_versioner import SelfVersioner

def test_init_in_temp():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        assert os.path.exists(os.path.join(tmp, ".git"))

def test_create_branch_and_commit():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        test_file = os.path.join(tmp, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        branch = ver.create_branch("test-evolve")
        ver.commit_all("feat: test change")
        assert ver.get_current_branch() == branch

def test_rollback():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        test_file = os.path.join(tmp, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        ver.commit_all("first")
        with open(test_file, "w") as f:
            f.write("x = 2\n")
        ver.rollback()
        with open(test_file) as f:
            content = f.read()
        assert content.strip() == "x = 1"

def test_merge_to_main():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        test_file = os.path.join(tmp, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        ver.commit_all("initial")
        ver.create_branch("feature")
        with open(test_file, "a") as f:
            f.write("y = 2\n")
        ver.commit_all("feature work")
        ver.merge_back()
        assert ver.get_current_branch() in ("main", "master")
