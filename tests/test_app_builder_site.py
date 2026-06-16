"""tests/test_app_builder_site.py"""
import tempfile
import os
from agent.app_builder_site import generate_site

def test_generate_site_creates_files():
    with tempfile.TemporaryDirectory() as tmp:
        generate_site("meu-site", tmp, {"type": "site", "framework": "vanilla", "features": ["home", "contato"]})
        assert os.path.isfile(os.path.join(tmp, "src", "index.html"))
        assert os.path.isfile(os.path.join(tmp, "src", "style.css"))
        assert os.path.isfile(os.path.join(tmp, "build.sh"))

def test_generate_site_custom_title():
    with tempfile.TemporaryDirectory() as tmp:
        generate_site("meu-site", tmp, {"type": "site", "framework": "vanilla", "features": []})
        with open(os.path.join(tmp, "src", "index.html")) as f:
            content = f.read()
        assert "meu-site" in content or "Meu Site" in content
