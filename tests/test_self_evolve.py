"""tests/test_self_evolve.py"""
import os
import tempfile
from agent.self_evolve import SelfAgent

def test_scan_python_files():
    with tempfile.TemporaryDirectory() as tmp:
        for fname in ["a.py", "b.py", "c.txt", "d.pyc"]:
            with open(os.path.join(tmp, fname), "w") as f:
                f.write("")
        agent = SelfAgent()
        py_files = agent._scan_python_files(tmp)
        names = [os.path.basename(p) for p in py_files]
        assert "a.py" in names
        assert "b.py" in names
        assert "c.txt" not in names
        assert "d.pyc" not in names

def test_analyze_ast():
    agent = SelfAgent()
    code = """
def hello(name):
    print(f"Hello, {name}")

class Test:
    def method(self):
        pass
"""
    analysis = agent._analyze_ast(code)
    assert "hello" in analysis["functions"]
    assert "Test" in analysis["classes"]
    assert len(analysis["imports"]) == 0

def test_analyze_ast_finds_imports():
    agent = SelfAgent()
    code = "import os\nfrom pathlib import Path\nos.listdir('.')"
    analysis = agent._analyze_ast(code)
    assert "os" in analysis["imports"]

def test_generate_evolve_plan_without_llm():
    agent = SelfAgent()
    with tempfile.TemporaryDirectory() as tmp:
        fpath = os.path.join(tmp, "test.py")
        with open(fpath, "w") as f:
            f.write("x = 1\n")
        analysis = agent._analyze_ast("x = 1\n")
        assert analysis["functions"] == []
        assert analysis["classes"] == []
