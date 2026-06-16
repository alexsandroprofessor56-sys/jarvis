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

def test_deliver_always_has_apk_key():
    app = AppBuilder()
    with tempfile.TemporaryDirectory() as tmp:
        app._projects_dir = tmp
        os.makedirs(os.path.join(tmp, "x", "dist"), exist_ok=True)
        with open(os.path.join(tmp, "x", "project.json"), "w") as f:
            json.dump({"name": "x", "type": "site", "url": "", "status": "built", "deploy_url": ""}, f)
        result = app.deliver("x")
        assert "apk" in result
        assert result["apk"] is None

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
