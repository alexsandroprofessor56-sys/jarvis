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
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        app._projects_dir = tmp
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
