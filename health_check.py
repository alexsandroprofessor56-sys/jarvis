#!/usr/bin/env python3
"""JARVIS Health Check - Verificação completa de todos os subsistemas"""
import sys
import os
import json
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n--- {title} ---")

def check(name, func):
    try:
        start = time.time()
        result = func()
        elapsed = (time.time() - start) * 1000
        if result is True:
            print(f"  ✅ {name} ({elapsed:.0f}ms)")
            return True
        elif isinstance(result, str):
            print(f"  ✅ {name}: {result} ({elapsed:.0f}ms)")
            return True
        else:
            print(f"  ❌ {name}: {result}")
            return False
    except Exception as e:
        print(f"  ❌ {name}: ERRO - {e}")
        return False

def check_import(module, attr=None):
    try:
        mod = __import__(module, fromlist=[attr] if attr else [])
        return getattr(mod, attr) if attr else mod
    except ImportError as e:
        raise Exception(f"Import falhou: {e}")

# ========== TESTES ==========

def test_config():
    from config.settings import load
    cfg = load()
    required = ["stt", "llm", "tts", "vision", "memory", "mic", "evolution", "wake_word"]
    for r in required:
        if r not in cfg:
            raise Exception(f"Seção '{r}' faltando")
    return f"Config OK ({len(cfg)} seções)"

def test_orchestrator():
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    assert o.tools is not None
    assert len(o.tools.tools) > 50
    return f"Orchestrator OK ({len(o.tools.tools)} tools)"

def test_tools():
    from core.tools import ToolRegistry
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    tools = o.tools
    critical = ["open_app", "run_command", "search_web", "screenshot", "analyze_screen",
                "remember", "recall", "knowledge_query", "agent_run", "computer_use"]
    for c in critical:
        if c not in tools.tools:
            raise Exception(f"Tool crítica faltando: {c}")
    return f"Tools OK ({len(tools.tools)} registradas)"

def test_memory_semantic():
    from memory.semantic import SemanticMemory
    m = SemanticMemory()
    m.remember_fact("Teste health check", "teste", 1.0, "health")
    facts = m.recall_fact("health check", top_k=1)
    assert len(facts) > 0 and facts[0]["fact"] == "Teste health check"
    return "Memória Semântica OK"

def test_memory_episodic():
    from memory.episodic import EpisodicMemory
    m = EpisodicMemory()
    m.add_episode("test", "Health check episode", importance=0.5)
    eps = m.get_episodes(hours=1)
    assert any("Health check" in e["summary"] for e in eps)
    return "Memória Episódica OK"

def test_memory_procedural():
    from memory.procedural import ProceduralMemory
    m = ProceduralMemory()
    m.learn_procedure("test_proc", ["step1", "step2"], "Teste", "health")
    proc = m.recall_procedure("test_proc")
    assert proc and len(proc["steps"]) == 2
    return "Memória Procedural OK"

def test_knowledge_base():
    from brain.knowledge import KnowledgeBase
    kb = KnowledgeBase()
    stats = kb.stats()
    return f"Knowledge Base OK ({stats.get('total_chunks', 0)} chunks)"

def test_llm():
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    llm = o.llm
    if hasattr(llm, 'warmup'):
        ok = llm.warmup()
        return f"LLM OK ({type(llm).__name__}: {llm.model})" if ok else "LLM não aquecido"
    return f"LLM OK ({type(llm).__name__}: {llm.model})"

def test_stt():
    from stt.vad_stt import VADSTT
    stt = VADSTT(model_name="tiny")
    if not stt.available:
        return "STT: modelo não carregado (precisa faster-whisper)"
    return f"STT OK (modelo: {stt.model_name})"

def test_tts():
    from tts.engine import TTS
    tts = TTS()
    return f"TTS OK ({tts.engine}: {tts.voice})"

def test_vision():
    from vision.screen_capture import ScreenCapture
    v = ScreenCapture()
    path = v.capture()
    assert Path(path).exists() and Path(path).stat().st_size > 1000
    return f"Visão OK (screenshot: {Path(path).name})"

def test_browser():
    from browser.automator import BrowserAutomator
    b = BrowserAutomator()
    return "Browser OK (Playwright)"

def test_scheduler():
    from scheduler.scheduler import Scheduler
    s = Scheduler()
    rid = s.add_reminder("Health check test", delay_minutes=0)
    assert rid > 0
    s.cancel_reminder(rid)
    return "Scheduler OK"

def test_sandbox():
    from sandbox.sandbox import CodeSandbox
    s = CodeSandbox()
    r = s.execute_python("2 + 2")
    assert "4" in r
    return "Sandbox OK"

def test_plugins():
    from plugins.loader import PluginLoader
    p = PluginLoader()
    p.discover()
    return f"Plugins OK ({len(p.plugins)} carregados)"

def test_face_auth():
    from auth.face import FaceAuth
    f = FaceAuth()
    return f"Face Auth OK (cv2: {f.face_cascade is not None})"

def test_agent():
    from agent.agent import AutonomousAgent
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    a = AutonomousAgent(llm=o.llm, tool_registry=o.tools)
    return "Agente Autônomo OK"

def test_computer_use():
    from agent.computer_use import ComputerUse
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    cu = ComputerUse(llm=o.llm, orchestrator=o)
    return "Computer Use OK"

def test_self_evolve():
    from agent.self_evolve import SelfAgent
    from core.orchestrator import Orchestrator
    o = Orchestrator()
    sa = SelfAgent(llm=o.llm)
    analysis = sa.analyze_codebase(str(Path(__file__).parent / "core"))
    assert isinstance(analysis, dict) and len(analysis) > 0
    return f"Auto-Evolução OK ({len(analysis)} arquivos analisados)"

def test_system_deps():
    deps = [
        ("python3", "python3 --version"),
        ("ffmpeg", "ffmpeg -version"),
        ("tesseract", "tesseract --version"),
        ("git", "git --version"),
    ]
    missing = []
    for name, cmd in deps:
        try:
            subprocess.run(cmd.split(), capture_output=True, timeout=2, check=True)
        except:
            missing.append(name)
    if missing:
        raise Exception(f"Faltando: {', '.join(missing)}")
    return f"Deps sistema OK ({len(deps)} verificados)"

def test_python_packages():
    required = [
        "PyQt6", "numpy", "sounddevice", "soundfile", "PIL",
        "requests", "ddgs", "sentence_transformers", "chromadb",
        "pytesseract", "pdf2image", "playwright", "cv2",
        "psutil", "pyautogui", "pyperclip", "mss",
        "apscheduler", "watchdog", "docker",
    ]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        raise Exception(f"Faltando: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}")
    return f"Pacotes Python OK ({len(required)} verificados)"

def test_directories():
    dirs = [
        Path.home() / ".jarvis",
        Path.home() / ".jarvis" / "memory",
        Path.home() / ".jarvis" / "faces",
        Path.home() / ".jarvis" / "plugins",
        Path.home() / ".jarvis" / "chroma_db",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        if not d.exists():
            raise Exception(f"Diretório não criado: {d}")
    return f"Diretórios OK ({len(dirs)} criados)"

def test_config_file():
    cfg_path = Path.home() / ".jarvis" / "config.json"
    if not cfg_path.exists():
        raise Exception("config.json não existe - rode config_wizard.py")
    with open(cfg_path) as f:
        cfg = json.load(f)
    if not cfg.get("llm", {}).get("api_key") and cfg.get("llm", {}).get("engine") == "nvidia":
        return "⚠️ Config OK mas NVIDIA_API_KEY não definida"
    return "Config file OK"

# ========== MAIN ==========

def main():
    print_header("JARVIS HEALTH CHECK v1.0")
    
    all_checks = [
        ("Sistema", test_system_deps),
        ("Pacotes Python", test_python_packages),
        ("Diretórios", test_directories),
        ("Config File", test_config_file),
        ("Config Loader", test_config),
        ("Orchestrator", test_orchestrator),
        ("Tools Registry", test_tools),
        ("Memória Semântica", test_memory_semantic),
        ("Memória Episódica", test_memory_episodic),
        ("Memória Procedural", test_memory_procedural),
        ("Knowledge Base", test_knowledge_base),
        ("LLM", test_llm),
        ("STT", test_stt),
        ("TTS", test_tts),
        ("Visão", test_vision),
        ("Browser", test_browser),
        ("Scheduler", test_scheduler),
        ("Sandbox", test_sandbox),
        ("Plugins", test_plugins),
        ("Face Auth", test_face_auth),
        ("Agente Autônomo", test_agent),
        ("Computer Use", test_computer_use),
        ("Auto-Evolução", test_self_evolve),
    ]
    
    passed = 0
    failed = 0
    
    for name, func in all_checks:
        if check(name, func):
            passed += 1
        else:
            failed += 1
    
    print_header("RESULTADO FINAL")
    print(f"\n  ✅ Passou: {passed}")
    print(f"  ❌ Falhou: {failed}")
    print(f"  📊 Total:  {passed + failed}")
    
    if failed == 0:
        print(f"\n  🎉 TODOS OS SISTEMAS OPERACIONAIS!")
        print(f"  JARVIS está pronto para uso.")
        return 0
    else:
        print(f"\n  ⚠️  {failed} verificação(ões) falharam.")
        print(f"  Revise os erros acima antes de usar.")
        return 1

if __name__ == "__main__":
    sys.exit(main())