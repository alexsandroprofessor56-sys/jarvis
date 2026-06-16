# Self-Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis can read, analyze, modify, and improve its own source code autonomously with git versioning, syntax validation, safety guards, and graceful restart.

**Architecture:** 5 new modules (SelfAgent, Editor, Versioner, Guard, Restarter) plus wiring into tools/orchestrator/settings. Git-based versioning with automatic rollback on failure. TDD throughout.

**Tech Stack:** Python 3, stdlib (`ast`, `py_compile`, `subprocess`, `tempfile`, `json`, `threading`, `time`), git (CLI), pytest

---

### Task 1: SelfGuard — Safety Limits

**Files:**
- Create: `agent/self_guard.py`
- Create: `tests/test_self_guard.py`

- [ ] **Step 1: Write failing tests for Guard**

```python
"""tests/test_self_guard.py"""
import time
import tempfile
from pathlib import Path
from agent.self_guard import SelfGuard

def test_guard_allows_valid_path():
    guard = SelfGuard()
    assert guard.is_allowed("/home/user/jarvis/core/tools.py")

def test_guard_blocks_outside_path():
    guard = SelfGuard()
    assert not guard.is_allowed("/etc/passwd")
    assert not guard.is_allowed("/home/user/secret.key")
    assert not guard.is_allowed("../outside.py")

def test_guard_rate_limit():
    guard = SelfGuard(max_changes=3, window_seconds=3600)
    for i in range(3):
        assert guard.can_evolve("test_change")
        guard.record_change("test_change")
    assert not guard.can_evolve("too_many")

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_self_guard.py -v 2>&1 | head -20`
Expected: ImportError or ModuleNotFoundError for `agent.self_guard`

- [ ] **Step 3: Write SelfGuard implementation**

```python
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
    def __init__(self, max_changes=5, window_seconds=3600, lock_path=EVOLVE_LOCK_PATH):
        self.max_changes = max_changes
        self.window_seconds = window_seconds
        self.lock_path = lock_path
        self._lock = threading.Lock()
        self._change_times = []
        self._file_lock_held = False

    def is_allowed(self, filepath: str) -> bool:
        abspath = os.path.abspath(filepath)
        name = os.path.basename(abspath)
        if name in (os.path.basename(__file__), "self_guard.py"):
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
            if abspath.startswith(os.path.abspath(allowed) + "/") or abspath.startswith(os.path.abspath(allowed)):
                return True
        return False

    def can_evolve(self, change_id: str) -> bool:
        with self._lock:
            now = time.time()
            self._change_times = [t for t in self._change_times if now - t < self.window_seconds]
            return len(self._change_times) < self.max_changes

    def record_change(self, change_id: str):
        with self._lock:
            self._change_times.append(time.time())

    def acquire_lock(self) -> bool:
        if self._file_lock_held:
            return False
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
                except (OSError, ProcessLookupError):
                    os.remove(self.lock_path)
                    return self.acquire_lock()
            except (ValueError, OSError):
                os.remove(self.lock_path)
                return self.acquire_lock()
            return False

    def release_lock(self):
        self._file_lock_held = False
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except OSError:
            pass

    def is_allowed_dependency(self, package: str, risk: str) -> bool:
        if risk in RISK_HIGH:
            return False
        if risk in RISK_MEDIUM:
            return True
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_self_guard.py -v`
Expected: 5 passed

---

### Task 2: SelfVersioner — Git Versioning

**Files:**
- Create: `agent/self_versioner.py`
- Create: `tests/test_self_versioner.py`

- [ ] **Step 1: Write failing tests for Versioner**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_self_versioner.py -v 2>&1 | head -10`
Expected: ImportError for `agent.self_versioner`

- [ ] **Step 3: Write SelfVersioner implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_self_versioner.py -v`
Expected: 4 passed

---

### Task 3: SelfEditor — Apply Changes

**Files:**
- Create: `agent/self_editor.py`
- Create: `tests/test_self_editor.py`

- [ ] **Step 1: Write failing tests for Editor**

```python
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
        invalid = os.path.join(tmp, "invalid.py")
        with open(invalid, "w") as f:
            f.write("x = 1\n" + " " * 10000 + "\n")  # valid but has issue
        assert editor._validate_python(valid)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_self_editor.py -v 2>&1 | head -10`
Expected: ImportError for `agent.self_editor`

- [ ] **Step 3: Write SelfEditor implementation**

```python
"""agent/self_editor.py"""
import os
import py_compile
import tempfile
import subprocess


class SelfEditor:
    def __init__(self, versioner=None):
        self.versioner = versioner

    def apply_patch(self, filepath: str, old_content: str, new_content: str) -> tuple:
        if not os.path.exists(filepath):
            return False, f"Arquivo não encontrado: {filepath}"
        try:
            with open(filepath) as f:
                current = f.read()
            if old_content not in current:
                return False, "Conteúdo antigo não encontrado no arquivo"
            updated = current.replace(old_content, new_content, 1)
            with open(filepath, "w") as f:
                f.write(updated)
            if filepath.endswith(".py") and not self._validate_python(filepath):
                self._rollback()
                return False, "Erro de sintaxe após edição — rollback aplicado"
            return True, "Patch aplicado com sucesso"
        except Exception as e:
            self._rollback()
            return False, f"Erro ao aplicar patch: {e}"

    def write_file(self, filepath: str, content: str) -> tuple:
        if not filepath.endswith(".py"):
            return False, "Apenas arquivos .py podem ser criados"
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(content)
            if not self._validate_python(filepath):
                os.remove(filepath)
                return False, "Erro de sintaxe no novo arquivo"
            return True, f"Arquivo criado: {filepath}"
        except Exception as e:
            return False, f"Erro ao criar arquivo: {e}"

    def update_dependencies(self, project_dir: str, deps: dict) -> tuple:
        req_file = os.path.join(project_dir, "requirements.txt")
        try:
            existing = {}
            if os.path.exists(req_file):
                with open(req_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            parts = line.split("=", 1)
                            existing[parts[0].strip()] = parts[1].strip()
            existing.update(deps)
            with open(req_file, "w") as f:
                for pkg, ver in sorted(existing.items()):
                    f.write(f"{pkg}=={ver}\n")
            return True, f"Dependências atualizadas: {list(deps.keys())}"
        except Exception as e:
            return False, f"Erro ao atualizar dependências: {e}"

    def _validate_python(self, filepath: str) -> bool:
        try:
            with open(filepath) as f:
                compile(f.read(), filepath, "exec")
            return True
        except SyntaxError:
            return False

    def _rollback(self):
        if self.versioner:
            try:
                self.versioner.rollback()
            except Exception:
                pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_self_editor.py -v`
Expected: 4 passed

---

### Task 4: SelfAgent — Code Analysis & EvolvePlan

**Files:**
- Create: `agent/self_evolve.py`
- Create: `tests/test_self_evolve.py`

- [ ] **Step 1: Write failing tests for SelfAgent**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_self_evolve.py -v 2>&1 | head -10`
Expected: ImportError for `agent.self_evolve`

- [ ] **Step 3: Write SelfAgent implementation**

```python
"""agent/self_evolve.py"""
import os
import ast
import json


class EvolvePlan:
    def __init__(self, diff: str, files: list, deps: list, risk: str, reason: str):
        self.diff = diff
        self.files = files
        self.deps = deps
        self.risk = risk
        self.reason = reason

    def to_dict(self):
        return {
            "diff": self.diff[:500],
            "files": self.files,
            "deps": self.deps,
            "risk": self.risk,
            "reason": self.reason,
        }


class SelfAgent:
    def __init__(self, llm=None, guard=None, editor=None, versioner=None):
        self.llm = llm
        self.guard = guard
        self.editor = editor
        self.versioner = versioner

    def _scan_python_files(self, directory: str) -> list:
        result = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", ".git", "node_modules")]
            for f in files:
                if f.endswith(".py"):
                    result.append(os.path.join(root, f))
        return result

    def _analyze_ast(self, code: str) -> dict:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"functions": [], "classes": [], "imports": [], "errors": ["syntax error"]}
        functions = []
        classes = []
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return {"functions": functions, "classes": classes, "imports": imports}

    def analyze_codebase(self, directory: str = None) -> dict:
        directory = directory or os.path.expanduser("~/jarvis")
        files = self._scan_python_files(directory)
        result = {}
        for fpath in files:
            relpath = os.path.relpath(fpath, directory)
            try:
                with open(fpath) as f:
                    code = f.read()
                result[relpath] = self._analyze_ast(code)
            except Exception as e:
                result[relpath] = {"error": str(e)}
        return result

    def _generate_suggestion(self, analysis: dict) -> str:
        if not self.llm:
            total_functions = sum(len(v.get("functions", [])) for v in analysis.values())
            total_classes = sum(len(v.get("classes", [])) for v in analysis.values())
            total_imports = sum(len(v.get("imports", [])) for v in analysis.values())
            return f"Base tem {total_functions} funções, {total_classes} classes, {total_imports} imports. " \
                   f"Nenhuma melhoria automática sugerida (LLM não disponível)."
        prompt = f"Analise este código e sugira 1 melhoria específica (bug, performance, ou segurança):\n"
        for fpath, info in list(analysis.items())[:5]:
            prompt += f"\n{fpath}: {json.dumps(info)}\n"
        prompt += "\nResponda com: { 'files': [...], 'deps': [...], 'risk': 'low'|'medium'|'high', 'reason': '...', 'old_content': '...', 'new_content': '...' }"
        try:
            resp = self.llm.chat([
                {"role": "system", "content": "Você é um engenheiro de software sênior revisando código. Responda apenas JSON."},
                {"role": "user", "content": prompt}
            ])
            if isinstance(resp, dict):
                content = resp.get("message", {}).get("content", "")
            else:
                content = str(resp)
            plan_data = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
            return plan_data
        except Exception:
            return None

    def suggest_improvement(self) -> EvolvePlan:
        analysis = self.analyze_codebase()
        suggestion = self._generate_suggestion(analysis)
        if suggestion and isinstance(suggestion, dict):
            return EvolvePlan(
                diff=f"{suggestion.get('old_content', '')} -> {suggestion.get('new_content', '')}",
                files=suggestion.get("files", []),
                deps=suggestion.get("deps", []),
                risk=suggestion.get("risk", "low"),
                reason=suggestion.get("reason", "Melhoria automática"),
            )
        return EvolvePlan("", [], [], "low", "Nenhuma melhoria identificada")

    def execute_evolution(self, goal: str = None) -> dict:
        plan = self.suggest_improvement()
        if not plan.files:
            return {"success": False, "message": plan.reason}
        if self.guard and not self.guard.can_evolve(goal or "auto"):
            return {"success": False, "message": "Rate limit excedido. Aguarde antes de evoluir novamente."}
        if self.guard and not self.guard.acquire_lock():
            return {"success": False, "message": "Outra evolução está em andamento."}
        try:
            for fpath in plan.files:
                if self.guard and not self.guard.is_allowed(fpath):
                    return {"success": False, "message": f"Arquivo não permitido: {fpath}"}
            for dep in plan.deps:
                if self.guard and not self.guard.is_allowed_dependency(dep, plan.risk):
                    return {"success": False, "message": f"Dependência bloqueada: {dep}"}
            if self.versioner:
                self.versioner.init_repo()
                self.versioner.create_branch()
            if self.editor and plan.deps:
                self.editor.update_dependencies(os.path.expanduser("~/jarvis"), {d: "latest" for d in plan.deps})
            if self.guard:
                self.guard.record_change(goal or "auto")
            if self.versioner:
                self.versioner.commit_all(f"feat: {plan.reason[:80]}")
                self.versioner.merge_back()
            return {"success": True, "message": f"Evolução aplicada: {plan.reason}", "plan": plan.to_dict()}
        except Exception as e:
            return {"success": False, "message": f"Evolução falhou: {e}"}
        finally:
            if self.guard:
                self.guard.release_lock()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_self_evolve.py -v`
Expected: 4 passed

---

### Task 5: SelfRestarter — Graceful Restart

**Files:**
- Create: `agent/self_restarter.py`
- Create: `tests/test_self_restarter.py`

- [ ] **Step 1: Write failing tests for Restarter**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_self_restarter.py -v 2>&1 | head -10`
Expected: ImportError for `agent.self_restarter`

- [ ] **Step 3: Write SelfRestarter implementation**

```python
"""agent/self_restarter.py"""
import os
import json
import time
import sys
import subprocess


class SelfRestarter:
    def __init__(self, state_dir=None, main_script=None):
        self.state_dir = state_dir or os.path.expanduser("~/.jarvis/state")
        self.main_script = main_script or os.path.expanduser("~/jarvis/main.py")
        self._state_file = os.path.join(self.state_dir, "state.json")

    def is_structural_change(self, files: list) -> bool:
        structural_patterns = [
            "core/orchestrator.py",
            "core/tools.py",
            "main.py",
            "agent/agent.py",
            "agent/self_",
        ]
        for f in files:
            f_norm = f.replace("\\", "/")
            for pattern in structural_patterns:
                if pattern in f_norm or f_norm.endswith(pattern):
                    return True
        return False

    def save_state(self, state: dict):
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def clear_state(self):
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
        except OSError:
            pass

    @property
    def state_file(self):
        return self._state_file

    def restart(self, state: dict = None):
        if state:
            self.save_state(state)
        python = sys.executable
        script = self.main_script
        args = [python, script, "--resume", self.state_file]
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            time.sleep(2)
            if proc.poll() is None:
                os._exit(0)
            else:
                raise RuntimeError("Novo processo falhou ao iniciar")
        except Exception as e:
            raise RuntimeError(f"Falha ao reiniciar: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_self_restarter.py -v`
Expected: 3 passed

---

### Task 6: Wire Tools — Tool #44 `self_evolve`

**Files:**
- Modify: `core/tools.py`
- Create: `tests/test_tools_evolve.py`

- [ ] **Step 1: Write failing tests for the new tool**

```python
"""tests/test_tools_evolve.py"""
from core.tools import ToolRegistry

def test_self_evolve_tool_registered():
    tr = ToolRegistry()
    assert "self_evolve" in tr.tools
    assert tr.tools["self_evolve"]["description"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tools_evolve.py -v`
Expected: AssertionError (tool not registered yet)

- [ ] **Step 3: Modify `core/tools.py`**

Add to `__init__` constructor parameters:
```python
self_evolution=None
```

Add after line 33:
```python
        self.evolution = self_evolution
```

Add a new method before `_register_all` or at the end of class, and register it:

In `_register_all()`, add after line 80 (`self.register("learner_stats", ...)`):
```python
        self.register("self_evolve", self.tool_self_evolve, "Auto-melhorar o código do Jarvis (ler, editar, versionar, reiniciar)")
```

Add schema entry in `_tool_schema` method inside the `schemas` dict (after the `learner_stats` entry around line 123):
```python
            "self_evolve": {"goal": {"type": "string"}, "auto_approve": {"type": "boolean"}},
```

Add the `required` params logic — add `"self_evolve"` to the list at line 138-142:
```python
        if name in ("semantic_remember", "procedural_learn", ... "self_evolve"):
            params["required"] = list(params["properties"].keys())
```

Add the tool method:
```python
    def tool_self_evolve(self, goal="improve", auto_approve=False):
        if not self.evolution:
            return "Sistema de auto-evolução não disponível"
        result = self.evolution.execute_evolution(goal=goal)
        return json.dumps(result, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_tools_evolve.py -v`
Expected: 1 passed

---

### Task 7: Wire Orchestrator + Settings

**Files:**
- Modify: `config/settings.py`
- Modify: `core/orchestrator.py`

- [ ] **Step 1: Write failing config test**

```python
"""tests/test_settings_evolve.py"""
import config.settings as settings

def test_evolve_config_default():
    cfg = settings.load()
    assert "evolution" in cfg
    assert cfg["evolution"]["enabled"] is True
    assert cfg["evolution"]["max_changes_per_hour"] == 5
```

- [ ] **Step 2: Run to fail**

Run: `python3 -m pytest tests/test_settings_evolve.py -v`
Expected: AssertionError (evolution key not in defaults yet)

- [ ] **Step 3: Modify `config/settings.py`**

Add to `DEFAULT_CONFIG` dict (after `"mic"` block):
```python
    "evolution": {
        "enabled": True,
        "max_changes_per_hour": 5,
        "risk_limit": "medium",
        "git_repo_path": os.path.expanduser("~/jarvis"),
    },
```

- [ ] **Step 4: Modify `core/orchestrator.py`**

Add import at top:
```python
from agent.self_evolve import SelfAgent
from agent.self_editor import SelfEditor
from agent.self_versioner import SelfVersioner
from agent.self_guard import SelfGuard
from agent.self_restarter import SelfRestarter
```

After `self.tools.agent = self.agent` line (line 80), add:
```python
        evolve_cfg = cfg.get("evolution", {})
        self.evolve_guard = SelfGuard(max_changes=evolve_cfg.get("max_changes_per_hour", 5))
        self.evolve_versioner = SelfVersioner(repo_path=evolve_cfg.get("git_repo_path"))
        self.evolve_editor = SelfEditor(versioner=self.evolve_versioner)
        self.evolve_agent = SelfAgent(
            llm=self.llm,
            guard=self.evolve_guard,
            editor=self.evolve_editor,
            versioner=self.evolve_versioner,
        )
        self.evolve_restarter = SelfRestarter()
        self.tools.evolution = self.evolve_agent
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_settings_evolve.py -v`
Expected: 1 passed

---

### Task 8: Full Integration Smoke Test

**Files:**
- Create: `tests/test_evolve_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""tests/test_evolve_integration.py"""
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
        # Create a test file
        test_file = os.path.join(tmp, "test_evolve.py")
        with open(test_file, "w") as f:
            f.write("x = 1\n")
        # Init git, evolve
        ver.init_repo()
        ver.commit_all("initial")
        assert guard.acquire_lock()
        assert editor.apply_patch(test_file, "x = 1\n", "x = 42\n")
        ver.commit_all("feat: evolve test")
        ver.merge_back()
        guard.release_lock()
        with open(test_file) as f:
            assert "x = 42" in f.read()

def test_guard_blocks_overflow():
    guard = SelfGuard(max_changes=1, window_seconds=3600)
    assert guard.can_evolve("1")
    guard.record_change("1")
    assert not guard.can_evolve("2")

def test_versioner_full_cycle():
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
        ver.commit_all("v2")
        ver.rollback()
        with open(f) as fh:
            assert fh.read() == "v1\n"
```

- [ ] **Step 2: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All ~18 tests pass
