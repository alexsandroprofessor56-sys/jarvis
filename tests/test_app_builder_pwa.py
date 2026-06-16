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
