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

    def _generate_suggestion(self, analysis: dict) -> dict:
        if not self.llm:
            total_functions = sum(len(v.get("functions", [])) for v in analysis.values())
            total_classes = sum(len(v.get("classes", [])) for v in analysis.values())
            total_imports = sum(len(v.get("imports", [])) for v in analysis.values())
            return None
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
            cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned)
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
        if self.guard and not self.guard.can_evolve():
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
                self.guard.record_change()
            if self.versioner:
                self.versioner.commit_all(f"feat: {plan.reason[:80]}")
                self.versioner.merge_back()
            return {"success": True, "message": f"Evolução aplicada: {plan.reason}", "plan": plan.to_dict()}
        except Exception as e:
            return {"success": False, "message": f"Evolução falhou: {e}"}
        finally:
            if self.guard:
                self.guard.release_lock()
