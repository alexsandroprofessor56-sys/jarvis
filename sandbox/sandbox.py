import sys
import io
import ast
import json
import traceback


class CodeSandbox:
    def __init__(self):
        self._globals = {"__builtins__": __builtins__}
        self._allowed_modules = {
            "math", "random", "json", "datetime", "re", "collections",
            "itertools", "functools", "statistics", "string", "typing",
        }

    def execute_python(self, code, timeout=5):
        if not code.strip():
            return ""

        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    name = node.func.id
                else:
                    name = ""
                if name in ("__import__", "exec", "eval", "open", "compile"):
                    return f"[BLOQUEADO] {name} não é permitido"
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "os":
                        return "[BLOQUEADO] os não é permitido"
                    if node.func.value.id == "subprocess":
                        return "[BLOQUEADO] subprocess não é permitido"
                    if node.func.value.id == "shutil":
                        return "[BLOQUEADO] shutil não é permitido"

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        local_scope = self._globals.copy()

        try:
            if isinstance(tree, ast.Module) and len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
                compiled = compile(ast.Expression(tree.body[0].value), '<sandbox>', 'eval')
                result = eval(compiled, local_scope)
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                return (output + str(result)).strip() if output else str(result)
            else:
                compiled = compile(code, '<sandbox>', 'exec')
                exec(compiled, local_scope)
                output = sys.stdout.getvalue()
                err = sys.stderr.getvalue()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                result = output or err or "Código executado sem saída."
                return result.strip()
        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            return f"[ERRO] {traceback.format_exc()}"

    def execute_javascript(self, code, timeout=5):
        try:
            import subprocess
            result = subprocess.run(
                ["node", "-e", code],
                capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout or result.stderr
            return output.strip()[:2000] if output else "Sem saída"
        except FileNotFoundError:
            return "Node.js não instalado"
        except subprocess.TimeoutExpired:
            return "Timeout de execução"
        except Exception as e:
            return f"[ERRO] {e}"

    def execute_bash(self, code, timeout=10):
        try:
            import subprocess
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout or result.stderr
            return output.strip()[:2000] if output else "Comando executado"
        except subprocess.TimeoutExpired:
            return "Timeout de execução"
        except Exception as e:
            return f"[ERRO] {e}"

    def repl(self, code, language="python"):
        if language == "python":
            return self.execute_python(code)
        elif language == "javascript":
            return self.execute_javascript(code)
        elif language == "bash":
            return self.execute_bash(code)
        else:
            return f"Linguagem não suportada: {language}"
