"""agent/app_builder_pwa.py — Gerador de Progressive Web Apps"""
import os
import json

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_templates")

def generate_pwa(name, project_path, plan):
    src_dir = os.path.join(project_path, "src")
    dist_dir = os.path.join(project_path, "dist")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    tmpl_dir = os.path.join(TEMPLATES_DIR, "pwa")
    if os.path.isdir(tmpl_dir):
        for f in os.listdir(tmpl_dir):
            src_path = os.path.join(tmpl_dir, f)
            with open(src_path) as fh:
                content = fh.read()
            content = content.replace("{{NAME}}", name)
            with open(os.path.join(src_dir, f), "w") as fh:
                fh.write(content)
    else:
        _write_default_pwa(src_dir, name)

    features = plan.get("features", [])
    apk_cmd = ""
    if "apk" in features:
        apk_cmd = (
            "npx @pwabuilder/cli package src src/dist 2>/dev/null || "
            "echo 'PWABuilder nao disponivel'"
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
