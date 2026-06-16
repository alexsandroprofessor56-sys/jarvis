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
            return False, f"Arquivo n\u00e3o encontrado: {filepath}"
        try:
            with open(filepath) as f:
                current = f.read()
            if old_content not in current:
                return False, "Conte\u00fado antigo n\u00e3o encontrado no arquivo"
            updated = current.replace(old_content, new_content, 1)
            with open(filepath, "w") as f:
                f.write(updated)
            if filepath.endswith(".py") and not self._validate_python(filepath):
                self._rollback()
                return False, "Erro de sintaxe ap\u00f3s edi\u00e7\u00e3o \u2014 rollback aplicado"
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
            return True, f"Depend\u00eancias atualizadas: {list(deps.keys())}"
        except Exception as e:
            return False, f"Erro ao atualizar depend\u00eancias: {e}"

    def _validate_python(self, filepath: str) -> bool:
        try:
            with open(filepath) as f:
                content = f.read()
            compile(content, filepath, "exec")
            if not content.endswith("\n"):
                return False
            return True
        except SyntaxError:
            return False

    def _rollback(self):
        if self.versioner:
            try:
                self.versioner.rollback()
            except Exception:
                pass
