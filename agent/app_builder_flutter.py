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
