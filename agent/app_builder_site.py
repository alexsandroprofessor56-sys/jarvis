"""agent/app_builder_site.py — Gerador de sites estáticos HTML/CSS/JS"""
import os
import shutil

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_templates")

def generate_site(name, project_path, plan):
    src_dir = os.path.join(project_path, "src")
    dist_dir = os.path.join(project_path, "dist")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    tmpl_dir = os.path.join(TEMPLATES_DIR, "site")
    if os.path.isdir(tmpl_dir):
        for f in os.listdir(tmpl_dir):
            shutil.copy2(os.path.join(tmpl_dir, f), src_dir)
    else:
        _write_default_site(src_dir)

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
