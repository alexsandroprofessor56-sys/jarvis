"""tests/test_self_editor.py"""
import os
import tempfile
from agent.self_editor import SelfEditor
from agent.self_versioner import SelfVersioner


def test_apply_valid_diff():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        editor = SelfEditor(versioner=ver)
        test_file = os.path.join(tmp, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        ver.commit_all("initial")
        success, msg = editor.apply_patch(test_file, "x = 1\n", "x = 42\n")
        assert success
        with open(test_file) as f:
            assert "x = 42" in f.read()


def test_invalid_syntax_triggers_rollback():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        editor = SelfEditor(versioner=ver)
        test_file = os.path.join(tmp, "test.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        ver.commit_all("initial")
        success, msg = editor.apply_patch(test_file, "x = 1\n", "x = 42 ")
        assert not success
        with open(test_file) as f:
            assert "x = 1" in f.read()


def test_update_requirements():
    with tempfile.TemporaryDirectory() as tmp:
        ver = SelfVersioner(repo_path=tmp)
        ver.init_repo()
        editor = SelfEditor(versioner=ver)
        req_file = os.path.join(tmp, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests==2.31.0\n")
        ver.commit_all("initial")
        success, msg = editor.update_dependencies(tmp, {"newdep": "1.0.0"})
        assert success
        with open(req_file) as f:
            content = f.read()
        assert "newdep==1.0.0" in content


def test_editor_validates_python():
    with tempfile.TemporaryDirectory() as tmp:
        editor = SelfEditor(versioner=None)
        valid = os.path.join(tmp, "valid.py")
        with open(valid, "w") as f:
            f.write("x = 1\nprint(x)\n")
        assert editor._validate_python(valid)
