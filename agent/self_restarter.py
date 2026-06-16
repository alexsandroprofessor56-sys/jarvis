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
