import sys
import io
import ast
import json
import traceback


class CodeSandbox:
    def __init__(self):
        self._globals = {"__builtins__": __builtins__}

    def execute_python(self, code, timeout=5):
        if not code.strip():
            return ""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        local_scope = self._globals.copy()
        try:
            tree = ast.parse(code)
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
