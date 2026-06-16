"""agent/app_builder.py — Orchestrador autônomo de criação de apps/sites"""
import os
import json
import re
import shutil
import subprocess
import threading
from datetime import datetime


PROJECTS_DIR = os.path.expanduser("~/.jarvis/projects")


class AppBuilder:
    def __init__(self, llm=None):
        self._llm = llm
        self._projects_dir = PROJECTS_DIR
        self._generators = {}

    def register_generator(self, project_type, generator_func):
        self._generators[project_type] = generator_func

    def _llm_analyze(self, description):
        if not self._llm:
            return self._fallback_analyze(description)
        prompt = (
            "Você é um analisador de projetos. Dada a descrição do usuário, "
            "responda APENAS com JSON contendo: type (site|pwa|flutter), "
            "framework (vanilla|react|flutter), features (array de strings). "
            f"Descrição: {description}"
        )
        resp = self._llm.chat([{"role": "user", "content": prompt}])
        try:
            return json.loads(resp)
        except Exception:
            return self._fallback_analyze(description)

    def _fallback_analyze(self, description):
        desc = description.lower()
        if re.search(r"android|apk|flutter|app nativo|mobile", desc):
            return {"type": "flutter", "framework": "flutter", "features": ["material"]}
        if re.search(r"pwa|offline|service.worker|instalável", desc):
            return {"type": "pwa", "framework": "vanilla", "features": ["offline"]}
        return {"type": "site", "framework": "vanilla", "features": ["responsive"]}

    def analyze(self, description):
        return self._llm_analyze(description)

    def scaffold(self, name, plan):
        path = os.path.join(self._projects_dir, name)
        os.makedirs(path, exist_ok=True)
        meta = {
            "name": name,
            "type": plan["type"],
            "framework": plan.get("framework", "vanilla"),
            "features": plan.get("features", []),
            "status": "scaffolded",
            "created": datetime.now().isoformat(),
            "deploy_url": "",
        }
        with open(os.path.join(path, "project.json"), "w") as f:
            json.dump(meta, f, indent=2)
        return path

    def generate(self, name, plan):
        path = os.path.join(self._projects_dir, name)
        gen = self._generators.get(plan["type"])
        if gen:
            gen(name, path, plan)
        self._update_status(name, "generated")
        return path

    def build(self, name):
        path = os.path.join(self._projects_dir, name)
        meta = self._load_meta(name)
        build_script = os.path.join(path, "build.sh")
        if os.path.exists(build_script):
            subprocess.run(["bash", build_script], cwd=path, capture_output=True, text=True)
        self._update_status(name, "built")
        return path

    def deploy(self, name, target="github"):
        path = os.path.join(self._projects_dir, name)
        meta = self._load_meta(name)
        url = ""
        if target == "github":
            result = subprocess.run(
                ["gh", "repo", "create", f"jarvis-{name}", "--public", "--source=.", "--push"],
                cwd=path, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                subprocess.run(
                    ["gh", "repo", "edit", f"jarvis-{name}", "--default-branch=main",
                     "--enable-pages=true", "--pages-branch=main", "--pages-source=./"],
                    capture_output=True, text=True, timeout=15
                )
                url = f"https://jarvis-{name}.github.io"
            else:
                url = f"Deploy via GitHub falhou: {result.stderr[:200]}"
        elif target == "local":
            url = f"http://localhost:{self._find_free_port()}"
            threading.Thread(target=self._serve_local, args=(path, url), daemon=True).start()
        self._update_meta(name, "deploy_url", url)
        self._update_status(name, "deployed")
        return url

    def deliver(self, name):
        meta = self._load_meta(name)
        out = {"name": name, "type": meta["type"], "url": meta["deploy_url"], "status": meta["status"]}
        apk_path = os.path.join(self._projects_dir, name, "dist", "app-release.apk")
        if os.path.exists(apk_path):
            out["apk"] = apk_path
        return out

    def list_projects(self):
        if not os.path.isdir(self._projects_dir):
            return []
        projects = []
        for name in os.listdir(self._projects_dir):
            meta = self._load_meta(name)
            if meta:
                projects.append(meta)
        return projects

    def get_project(self, name):
        return self._load_meta(name)

    def _load_meta(self, name):
        path = os.path.join(self._projects_dir, name, "project.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def _update_status(self, name, status):
        self._update_meta(name, "status", status)

    def _update_meta(self, name, key, value):
        meta = self._load_meta(name)
        if meta:
            meta[key] = value
            path = os.path.join(self._projects_dir, name, "project.json")
            with open(path, "w") as f:
                json.dump(meta, f, indent=2)

    def _find_free_port(self):
        import socket
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def _serve_local(self, path, url):
        import http.server
        port = int(url.split(":")[-1])
        os.chdir(os.path.join(path, "dist"))
        http.server.HTTPServer(("0.0.0.0", port), http.server.SimpleHTTPRequestHandler).serve_forever()
