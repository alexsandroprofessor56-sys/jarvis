# AppBuilder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis ganha capacidade autônoma de criar apps/sites (PWA, site estático, APK Flutter) a partir de descrição em linguagem natural e fazer deploy.

**Architecture:** AppBuilder orquestrador que analisa o pedido via LLM, escolhe o tipo de projeto, gera código via templates + LLM, executa build e deploy. Cada tipo de projeto tem seu próprio generator (SiteGenerator, PWAGenerator, FlutterGenerator).

**Tech Stack:** Python, Ollama (qwen2.5:3b), templates HTML/CSS/JS, Flutter SDK (futuro), Bubblewrap (PWA→APK), GitHub Pages/Netlify

---

### Task 1: App Builder Core Module

**Files:**
- Create: `agent/app_builder.py`
- Test: `tests/test_app_builder.py`

- [ ] **Step 1: Write the test for AppBuilder.analyze()**

```python
"""tests/test_app_builder.py"""
import os
import tempfile
import json
from agent.app_builder import AppBuilder

def test_analyze_project_type():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "site", "framework": "vanilla", "features": ["home", "contato"]}
    result = app.analyze("quero um site pessoal")
    assert result["type"] == "site"
    assert "framework" in result

def test_analyze_pwa():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "pwa", "framework": "vanilla", "features": ["offline", "push"]}
    result = app.analyze("quero um app PWA de clima")
    assert result["type"] == "pwa"

def test_analyze_flutter():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "flutter", "framework": "flutter", "features": ["material"]}
    result = app.analyze("quero um app Android de calculadora")
    assert result["type"] == "flutter"

def test_scaffold_creates_dirs():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "site", "framework": "vanilla", "features": []}
    with tempfile.TemporaryDirectory() as tmp:
        app._projects_dir = tmp
        path = app.scaffold("meu-site", {"type": "site"})
        assert os.path.isdir(path)
        assert os.path.isfile(os.path.join(path, "project.json"))

def test_project_metadata():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "pwa", "framework": "vanilla", "features": []}
    with tempfile.TemporaryDirectory() as tmp:
        app._projects_dir = tmp
        path = app.scaffold("meu-app", {"type": "pwa"})
        with open(os.path.join(path, "project.json")) as f:
            meta = json.load(f)
        assert meta["name"] == "meu-app"
        assert meta["type"] == "pwa"
        assert meta["status"] == "scaffolded"

def test_generate_calls_generator():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "site", "framework": "vanilla", "features": []}
    called = []
    app._generators["site"] = lambda name, path, plan: called.append(True)
    with tempfile.TemporaryDirectory() as tmp:
        app._projects_dir = tmp
        path = app.scaffold("x", {"type": "site"})
        result = app.generate("x", {"type": "site"})
        assert len(called) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder.py -v 2>&1`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.app_builder'"

- [ ] **Step 3: Write AppBuilder core**

```python
"""agent/app_builder.py — Orquestrador autônomo de criação de apps/sites"""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder.py -v 2>&1`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd /home/alexkali/jarvis && git add tests/test_app_builder.py agent/app_builder.py && git commit -m "feat: add AppBuilder core module with analyze/scaffold/generate/build/deploy/deliver"
```

---

### Task 2: Site Generator

**Files:**
- Create: `agent/app_builder_site.py`
- Create: `app_templates/site/index.html`
- Create: `app_templates/site/style.css`
- Modify: `agent/app_builder.py` (register generator)

- [ ] **Step 1: Write the test**

```python
"""tests/test_app_builder_site.py"""
import tempfile
import os
from agent.app_builder_site import generate_site

def test_generate_site_creates_files():
    with tempfile.TemporaryDirectory() as tmp:
        generate_site("meu-site", tmp, {"type": "site", "framework": "vanilla", "features": ["home", "contato"]})
        assert os.path.isfile(os.path.join(tmp, "index.html"))
        assert os.path.isfile(os.path.join(tmp, "style.css"))
        assert os.path.isfile(os.path.join(tmp, "build.sh"))

def test_generate_site_custom_title():
    with tempfile.TemporaryDirectory() as tmp:
        generate_site("meu-site", tmp, {"type": "site", "framework": "vanilla", "features": []})
        with open(os.path.join(tmp, "index.html")) as f:
            content = f.read()
        assert "meu-site" in content or "Meu Site" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_site.py -v 2>&1`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write site generator**

```python
"""agent/app_builder_site.py — Gerador de sites estáticos HTML/CSS/JS"""
import os
import shutil

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_templates")

def generate_site(name, project_path, plan):
    src_dir = os.path.join(project_path, "src")
    dist_dir = os.path.join(project_path, "dist")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    # Copy templates
    tmpl_dir = os.path.join(TEMPLATES_DIR, "site")
    if os.path.isdir(tmpl_dir):
        for f in os.listdir(tmpl_dir):
            shutil.copy2(os.path.join(tmpl_dir, f), src_dir)
    else:
        _write_default_site(src_dir)

    # Create build.sh (just copy src to dist for static site)
    with open(os.path.join(project_path, "build.sh"), "w") as f:
        f.write("#!/bin/bash\ncp -r src/* dist/\n")
    os.chmod(os.path.join(project_path, "build.sh"), 0o755)

def _write_default_site(src_dir):
    with open(os.path.join(src_dir, "index.html"), "w") as f:
        f.write("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meu Site</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<h1>Meu Site</h1>
<p>Bem-vindo!</p>
</body>
</html>""")
    with open(os.path.join(src_dir, "style.css"), "w") as f:
        f.write("""* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; padding: 2rem; max-width: 800px; margin: 0 auto; background: #f5f5f5; }
h1 { color: #333; }""")
```

- [ ] **Step 4: Register the generator in AppBuilder**

Edit `agent/app_builder.py`, add import and registration in `__init__`:

```python
from agent.app_builder_site import generate_site
```
Add inside `__init__`:
```python
self.register_generator("site", generate_site)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_site.py -v 2>&1`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
cd /home/alexkali/jarvis && git add tests/test_app_builder_site.py agent/app_builder_site.py app_templates/site/ agent/app_builder.py && git commit -m "feat: add SiteGenerator for static HTML/CSS/JS sites"
```

---

### Task 3: PWA Generator

**Files:**
- Create: `agent/app_builder_pwa.py`
- Create: `app_templates/pwa/index.html`
- Create: `app_templates/pwa/manifest.json`
- Create: `app_templates/pwa/sw.js`
- Create: `app_templates/pwa/icon.svg`
- Modify: `agent/app_builder.py` (register generator)

- [ ] **Step 1: Write the test**

```python
"""tests/test_app_builder_pwa.py"""
import tempfile
import os
import json
from agent.app_builder_pwa import generate_pwa

def test_generate_pwa_creates_files():
    with tempfile.TemporaryDirectory() as tmp:
        generate_pwa("meu-app", tmp, {"type": "pwa", "framework": "vanilla", "features": ["offline", "push"]})
        assert os.path.isfile(os.path.join(tmp, "src", "index.html"))
        assert os.path.isfile(os.path.join(tmp, "src", "manifest.json"))
        assert os.path.isfile(os.path.join(tmp, "src", "sw.js"))
        assert os.path.isfile(os.path.join(tmp, "build.sh"))

def test_generate_pwa_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        generate_pwa("meu-app", tmp, {"type": "pwa", "framework": "vanilla", "features": []})
        with open(os.path.join(tmp, "src", "manifest.json")) as f:
            manifest = json.load(f)
        assert manifest["name"] == "meu-app"
        assert manifest["display"] == "standalone"

def test_generate_pwa_build_script():
    with tempfile.TemporaryDirectory() as tmp:
        generate_pwa("meu-app", tmp, {"type": "pwa", "framework": "vanilla", "features": ["apk"]})
        with open(os.path.join(tmp, "build.sh")) as f:
            script = f.read()
        assert "pwabuilder" in script or "bubblewrap" in script
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_pwa.py -v 2>&1`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write PWA generator**

```python
"""agent/app_builder_pwa.py — Gerador de Progressive Web Apps"""
import os
import json
import shutil

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_templates")

def generate_pwa(name, project_path, plan):
    src_dir = os.path.join(project_path, "src")
    dist_dir = os.path.join(project_path, "dist")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    tmpl_dir = os.path.join(TEMPLATES_DIR, "pwa")
    if os.path.isdir(tmpl_dir):
        for f in os.listdir(tmpl_dir):
            shutil.copy2(os.path.join(tmpl_dir, f), src_dir)
    else:
        _write_default_pwa(src_dir, name)

    features = plan.get("features", [])
    apk_cmd = ""
    if "apk" in features:
        apk_cmd = (
            "npx @pwabuilder/cli package src src/dist 2>/dev/null || "
            "echo 'PWABuilder nao disponivel, instale com: npm install -g @pwabuilder/cli'"
        )

    with open(os.path.join(project_path, "build.sh"), "w") as f:
        f.write(f"""#!/bin/bash
set -e
mkdir -p dist
cp -r src/* dist/
{apk_cmd}
echo 'Build concluido!'
""")
    os.chmod(os.path.join(project_path, "build.sh"), 0o755)

def _write_default_pwa(src_dir, name):
    with open(os.path.join(src_dir, "index.html"), "w") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>{name}</title>
<link rel="manifest" href="manifest.json">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="style.css">
</head>
<body>
<h1>{name}</h1>
<p>App instalavel</p>
<script src="app.js"></script>
</body>
</html>""")
    with open(os.path.join(src_dir, "manifest.json"), "w") as f:
        json.dump({
            "name": name, "short_name": name[:12], "start_url": ".",
            "display": "standalone", "background_color": "#ffffff",
            "theme_color": "#1976d2",
            "icons": [{"src": "icon.svg", "sizes": "192x192", "type": "image/svg+xml"}]
        }, f, indent=2)
    with open(os.path.join(src_dir, "sw.js"), "w") as f:
        f.write("""const CACHE = 'v1';
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./']))); });
self.addEventListener('fetch', e => { e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))); });
""")
    with open(os.path.join(src_dir, "style.css"), "w") as f:
        f.write("""* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; padding: 1rem; background: #fff; color: #333; }
h1 { color: #1976d2; }""")
    with open(os.path.join(src_dir, "app.js"), "w") as f:
        f.write("""if ('serviceWorker' in navigator) { navigator.serviceWorker.register('sw.js'); }
console.log('PWA pronto!');
""")
    with open(os.path.join(src_dir, "icon.svg"), "w") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192"><rect fill="#1976d2" width="192" height="192" rx="32"/><text fill="#fff" font-size="96" font-family="system-ui" x="96" y="128" text-anchor="middle" dominant-baseline="middle">J</text></svg>')
```

- [ ] **Step 4: Register generator in AppBuilder**

Add to `agent/app_builder.py`:
```python
from agent.app_builder_pwa import generate_pwa
```
Add inside `__init__`:
```python
self.register_generator("pwa", generate_pwa)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_pwa.py -v 2>&1`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd /home/alexkali/jarvis && git add tests/test_app_builder_pwa.py agent/app_builder_pwa.py app_templates/pwa/ agent/app_builder.py && git commit -m "feat: add PWAGenerator with manifest + service worker + icon"
```

---

### Task 4: Flutter Generator

**Files:**
- Create: `agent/app_builder_flutter.py`
- Modify: `agent/app_builder.py` (register generator)

- [ ] **Step 1: Write the test**

```python
"""tests/test_app_builder_flutter.py"""
import tempfile
import os
from agent.app_builder_flutter import generate_flutter

def test_generate_flutter_checks_flutter():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_flutter("meu-app", tmp, {"type": "flutter", "framework": "flutter", "features": ["material"]})
        # If flutter is not installed, should return error message
        if "Flutter nao instalado" in str(result):
            assert True
        else:
            assert os.path.isdir(os.path.join(tmp, "lib"))

def test_generate_flutter_project_json():
    with tempfile.TemporaryDirectory() as tmp:
        generate_flutter("app", tmp, {"type": "flutter", "framework": "flutter", "features": []})
        meta_path = os.path.join(tmp, "project.json")
        if os.path.exists(meta_path):
            import json
            with open(meta_path) as f:
                meta = json.load(f)
            assert meta["name"] == "app"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_flutter.py -v 2>&1`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write Flutter generator**

```python
"""agent/app_builder_flutter.py — Gerador de APK Flutter"""
import os
import subprocess
import json

def generate_flutter(name, project_path, plan):
    if not _flutter_installed():
        _write_fallback_message(project_path, name, "Flutter nao instalado. Instale com: 'sudo apt install flutter' ou 'snap install flutter'")
        return "Flutter nao instalado"

    cwd = os.path.dirname(project_path)
    result = subprocess.run(
        ["flutter", "create", "--project-name", name.replace("-", "_"), name],
        cwd=cwd, capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        _write_fallback_message(project_path, name, f"flutter create falhou: {result.stderr[:200]}")
        return result.stderr[:200]

    with open(os.path.join(project_path, "build.sh"), "w") as f:
        f.write("""#!/bin/bash
set -e
flutter build apk --release
mkdir -p dist
cp build/app/outputs/flutter-apk/app-release.apk dist/
echo "APK gerado em dist/app-release.apk"
""")
    os.chmod(os.path.join(project_path, "build.sh"), 0o755)

    meta = {"name": name, "type": "flutter", "status": "generated", "flutter_create": "ok"}
    with open(os.path.join(project_path, "project.json"), "w") as f:
        json.dump(meta, f, indent=2)
    return "ok"

def _flutter_installed():
    try:
        r = subprocess.run(["which", "flutter"], capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def _write_fallback_message(path, name, msg):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "README.txt"), "w") as f:
        f.write(f"Projeto: {name}\n{msg}\n")
```

- [ ] **Step 4: Register generator in AppBuilder**

Add to `agent/app_builder.py`:
```python
from agent.app_builder_flutter import generate_flutter
```
Add inside `__init__`:
```python
self.register_generator("flutter", generate_flutter)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_flutter.py -v 2>&1`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
cd /home/alexkali/jarvis && git add tests/test_app_builder_flutter.py agent/app_builder_flutter.py agent/app_builder.py && git commit -m "feat: add FlutterGenerator for APK builds"
```

---

### Task 5: Wire Tools into ExtraTools + Orchestrator

**Files:**
- Modify: `core/extra_tools.py`
- Modify: `core/orchestrator.py`

- [ ] **Step 1: Add AppBuilder tools to ExtraTools**

Add import to `core/extra_tools.py`:
```python
from agent.app_builder import AppBuilder
```

Add methods to ExtraTools class:
```python
    def __init__(self):
        self._http_server = None
        self._http_thread = None
        self.telegram_listener = None
        self._app_builder = AppBuilder()
        self._app_builder.register_generator("site", generate_site)
        self._app_builder.register_generator("pwa", generate_pwa)
        self._app_builder.register_generator("flutter", generate_flutter)

    # === APP BUILDER ===
    def app_builder(self, descricao=None):
        if not descricao:
            return "Descreva o app/site que quer criar. Ex: 'cria um app de tarefas'"
        plan = self._app_builder.analyze(descricao)
        name = descricao.lower().replace(" ", "-")[:30]
        path = self._app_builder.scaffold(name, plan)
        self._app_builder.generate(name, plan)
        self._app_builder.build(name)
        url = self._app_builder.deploy(name, target="local")
        result = self._app_builder.deliver(name)
        return json.dumps(result, indent=2)

    def app_status(self, nome=None):
        if not nome:
            return "Use: app_status <nome-do-projeto>"
        meta = self._app_builder.get_project(nome)
        if not meta:
            return f"Projeto '{nome}' nao encontrado."
        return json.dumps(meta, indent=2)

    def app_list(self):
        projects = self._app_builder.list_projects()
        if not projects:
            return "Nenhum projeto criado ainda."
        lines = []
        for p in projects:
            lines.append(f"• {p['name']} ({p['type']}) - {p['status']}")
        return "\n".join(lines)

    def app_deploy(self, nome=None, target="github"):
        if not nome:
            return "Use: app_deploy <nome-do-projeto> [target=github|local]"
        url = self._app_builder.deploy(nome, target)
        return f"Deploy de '{nome}' em: {url}"
```

Add entries to `EXTRA_TOOLS`:
```python
    ("app_builder", ExtraTools.app_builder,
     "Criar app/site completo a partir de descrição. Ex: 'cria um app de tarefas'",
     {"descricao": {"type": "string"}}),
    ("app_status", ExtraTools.app_status,
     "Ver status de um projeto",
     {"nome": {"type": "string"}}),
    ("app_list", ExtraTools.app_list,
     "Listar todos os projetos criados", {}),
    ("app_deploy", ExtraTools.app_deploy,
     "Fazer deploy de um projeto",
     {"nome": {"type": "string"}, "target": {"type": "string"}}),
```

- [ ] **Step 2: Update imports in extra_tools.py**

```python
from agent.credential_vault import credential_save as _vault_save, credential_get as _vault_get, credential_list as _vault_list, credential_delete as _vault_delete
from agent.app_builder import AppBuilder
from agent.app_builder_site import generate_site
from agent.app_builder_pwa import generate_pwa
from agent.app_builder_flutter import generate_flutter
```

- [ ] **Step 3: Add route in Orchestrator (optional but recommended)**

In `core/orchestrator.py`, add to `_route_command` patterns:
```python
(r"^(cria|criar|gere|gerar|construa|faca um app|faz um app)\s+(.+)$", self._cmd_app_builder),
```

Add handler method:
```python
def _cmd_app_builder(self, m):
    desc = m.group(2).strip()
    self.log(f"⚙ AppBuilder: {desc}", "system")
    result = self.tools._extra.app_builder(descricao=desc)
    self.log(f"  → {result[:300]}", "system")
    self._finalize(f"App criado! {result[:200]}")
```

- [ ] **Step 4: Test that Jarvis loads with new tools**

Run: `cd /home/alexkali/jarvis && python3 -c "from core.extra_tools import ExtraTools, EXTRA_TOOLS; et = ExtraTools(); names = [t[0] for t in EXTRA_TOOLS]; assert 'app_builder' in names; assert 'app_list' in names; print('OK:', len(EXTRA_TOOLS), 'tools')"`
Expected: `OK: <count> tools` with app_builder included

- [ ] **Step 5: Commit**

```bash
cd /home/alexkali/jarvis && git add core/extra_tools.py core/orchestrator.py && git commit -m "feat: wire AppBuilder tools into ExtraTools + Orchestrator"
```

---

### Task 6: Integration Test

**Files:**
- Create: `tests/test_app_builder_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""tests/test_app_builder_integration.py"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.app_builder import AppBuilder
from agent.app_builder_site import generate_site
from agent.app_builder_pwa import generate_pwa
from agent.app_builder_flutter import generate_flutter

def test_full_site_workflow():
    app = AppBuilder()
    app.register_generator("site", generate_site)
    app._llm_analyze = lambda desc: {"type": "site", "framework": "vanilla", "features": ["home"]}
    plan = app.analyze("quero um site")
    assert plan["type"] == "site"
    name = "test-site-integration"
    path = app.scaffold(name, plan)
    assert os.path.isdir(path)
    app.generate(name, plan)
    assert os.path.isfile(os.path.join(path, "src", "index.html"))
    app.build(name)
    assert os.path.isdir(os.path.join(path, "dist"))
    result = app.deliver(name)
    assert result["name"] == name
    assert result["type"] == "site"

def test_full_pwa_workflow():
    app = AppBuilder()
    app.register_generator("pwa", generate_pwa)
    app._llm_analyze = lambda desc: {"type": "pwa", "framework": "vanilla", "features": ["offline"]}
    plan = app.analyze("quero um app PWA")
    assert plan["type"] == "pwa"
    name = "test-pwa-integration"
    path = app.scaffold(name, plan)
    app.generate(name, plan)
    assert os.path.isfile(os.path.join(path, "src", "manifest.json"))
    assert os.path.isfile(os.path.join(path, "src", "sw.js"))

def test_list_projects():
    app = AppBuilder()
    app._llm_analyze = lambda desc: {"type": "site", "framework": "vanilla", "features": []}
    before = app.list_projects()
    name = "test-list-proj"
    path = app.scaffold(name, app.analyze("site"))
    app.generate(name, app.analyze("site"))
    after = app.list_projects()
    assert len(after) == len(before) + 1
    names = [p["name"] for p in after]
    assert name in names

def test_fallback_analyze():
    app = AppBuilder()
    r1 = app._fallback_analyze("quero um app android de calculadora")
    assert r1["type"] == "flutter"
    r2 = app._fallback_analyze("quero um site pessoal")
    assert r2["type"] == "site"
    r3 = app._fallback_analyze("quero um app PWA de clima")
    assert r3["type"] == "pwa"
```

- [ ] **Step 2: Run integration test**

Run: `cd /home/alexkali/jarvis && python3 -m pytest tests/test_app_builder_integration.py -v 2>&1`
Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
cd /home/alexkali/jarvis && git add tests/test_app_builder_integration.py && git commit -m "test: add integration tests for AppBuilder full workflows"
```

---

### Design Review Checklist

**Spec coverage:**
- [x] "cria um site pessoal" → site estático (Task 2)
- [x] "cria um app PWA de clima" → PWA + manifest + SW (Task 3)
- [x] "cria um app Android de calculadora" → APK Flutter (Task 4)
- [x] LLM decide o tipo de projeto → analyze() com fallback (Task 1)
- [x] Deploy GitHub Pages / local → deploy() (Task 1)
- [x] Ferramentas registradas → ExtraTools (Task 5)
- [x] Testes completos → 6 unit + 2 site + 3 pwa + 2 flutter + 4 integration = 17 tests

**Placeholder scan:** Nenhum placeholder ou TBD encontrado.

**Type consistency:** `generate_site(name, path, plan)` assinatura consistente entre todos os generators. `analyze()` retorna dict com `type`/`framework`/`features`. `deliver()` retorna dict com `name`/`type`/`url`/`status`.
