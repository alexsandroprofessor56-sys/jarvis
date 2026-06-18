#!/usr/bin/env python3
"""JARVIS Configuration Wizard - Configuração interativa completa"""
import os
import json
import sys
import subprocess
from pathlib import Path

CONFIG_DIR = Path.home() / ".jarvis"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "stt": {"engine": "whisper", "model": "base", "language": "pt"},
    "llm": {"engine": "nvidia", "url": "https://integrate.api.nvidia.com/v1", "model": "nvidia/nemotron-3-ultra", "api_key": "", "temperature": 0.7, "max_tokens": 4096},
    "tts": {"engine": "edge", "voice": "pt-BR-AntonioNeural", "speed": 0.8},
    "vision": {"enabled": True, "model": "qwen2.5:3b"},
    "memory": {"enabled": True, "max_history": 100, "path": str(CONFIG_DIR / "memory")},
    "mic": {"device": None, "sample_rate": 16000},
    "evolution": {"enabled": True, "max_changes_per_hour": 5, "risk_limit": "medium", "git_repo_path": str(Path.home() / "jarvis")},
    "wake_word": {"enabled": True, "device": None, "model": "tiny"},
    "telegram": {"enabled": False, "token": "", "chat_id": "", "poll_interval": 2}
}

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"\n✅ Configuração salva em {CONFIG_FILE}")

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n--- {title} ---")

def get_input(prompt, current="", required=False, validator=None):
    while True:
        if current:
            val = input(f"{prompt} [{current}]: ").strip()
            if not val:
                val = current
        else:
            val = input(f"{prompt}: ").strip()
        if not val and required:
            print("❌ Campo obrigatório!")
            continue
        if validator and not validator(val):
            print("❌ Valor inválido!")
            continue
        return val

def choose_option(prompt, options, current=""):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        mark = " ← atual" if opt == current else ""
        print(f"  {i}. {opt}{mark}")
    while True:
        choice = input(f"Escolha [1-{len(options)}] [{options.index(current)+1 if current in options else 1}]: ").strip()
        if not choice and current in options:
            return current
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except:
            pass
        print("❌ Opção inválida!")

def test_nvidia_key(key):
    if not key:
        return False, "Chave vazia"
    try:
        import requests
        r = requests.get("https://integrate.api.nvidia.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=10)
        return r.ok, "OK" if r.ok else f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def test_ollama(url):
    try:
        import requests
        r = requests.get(f"{url}/api/tags", timeout=5)
        return r.ok, "OK" if r.ok else f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def configure_stt(cfg):
    print_section("🎤 Speech-to-Text (STT)")
    print("Engine: whisper (local) ou vosk (local)")
    cfg["stt"]["engine"] = choose_option("Engine STT:", ["whisper", "vosk"], cfg["stt"]["engine"])
    if cfg["stt"]["engine"] == "whisper":
        cfg["stt"]["model"] = choose_option("Modelo Whisper:", ["tiny", "base", "small", "medium", "large-v3"], cfg["stt"]["model"])
    cfg["stt"]["language"] = get_input("Idioma (código ISO)", cfg["stt"]["language"])

def configure_llm(cfg):
    print_section("🧠 Large Language Model (LLM)")
    engine = choose_option("Engine LLM:", ["nvidia", "ollama", "lm_studio"], cfg["llm"]["engine"])
    cfg["llm"]["engine"] = engine
    
    if engine == "nvidia":
        print("\n🔑 NVIDIA API Key necessária para Nemotron-3-Ultra")
        print("   Obtenha em: https://build.nvidia.com/explore/discover")
        key = get_input("NVIDIA_API_KEY", cfg["llm"]["api_key"])
        if key != cfg["llm"]["api_key"]:
            print("   Testando chave...")
            ok, msg = test_nvidia_key(key)
            if ok:
                print("   ✅ Chave válida!")
            else:
                print(f"   ⚠️  Falha no teste: {msg}")
                if input("   Continuar mesmo assim? (s/N): ").lower() != 's':
                    key = cfg["llm"]["api_key"]
        cfg["llm"]["api_key"] = key
        cfg["llm"]["model"] = get_input("Modelo", cfg["llm"]["model"])
        
    elif engine == "ollama":
        cfg["llm"]["url"] = get_input("URL Ollama", cfg["llm"]["url"])
        print("   Testando conexão...")
        ok, msg = test_ollama(cfg["llm"]["url"])
        if ok:
            print("   ✅ Ollama acessível!")
            try:
                import requests
                r = requests.get(f"{cfg['llm']['url']}/api/tags", timeout=5)
                models = [m["name"] for m in r.json().get("models", [])]
                if models:
                    cfg["llm"]["model"] = choose_option("Modelo disponível:", models, cfg["llm"]["model"])
            except:
                pass
        else:
            print(f"   ⚠️  Ollama não acessível: {msg}")
        cfg["llm"]["model"] = get_input("Modelo", cfg["llm"]["model"])

def configure_tts(cfg):
    print_section("🔊 Text-to-Speech (TTS)")
    cfg["tts"]["engine"] = choose_option("Engine TTS:", ["edge", "kokoro", "espeak"], cfg["tts"]["engine"])
    if cfg["tts"]["engine"] == "edge":
        voices = ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural", "en-US-AriaNeural", "en-US-GuyNeural"]
        cfg["tts"]["voice"] = choose_option("Voz:", voices, cfg["tts"]["voice"])
    elif cfg["tts"]["engine"] == "kokoro":
        cfg["tts"]["voice"] = get_input("Voz Kokoro (ex: af_heart)", cfg["tts"]["voice"])
    cfg["tts"]["speed"] = float(get_input("Velocidade (0.5-2.0)", str(cfg["tts"]["speed"])))

def configure_vision(cfg):
    print_section("👁️ Visão Computacional")
    cfg["vision"]["enabled"] = input("Ativar visão? (S/n): ").lower() != 'n'
    if cfg["vision"]["enabled"]:
        cfg["vision"]["model"] = get_input("Modelo Ollama para visão (ex: llava, qwen2.5:3b)", cfg["vision"]["model"])

def configure_memory(cfg):
    print_section("🧠 Memória")
    cfg["memory"]["enabled"] = input("Ativar memória persistente? (S/n): ").lower() != 'n'
    if cfg["memory"]["enabled"]:
        path = get_input("Diretório de dados", cfg["memory"]["path"])
        cfg["memory"]["path"] = str(Path(path).expanduser())
        Path(cfg["memory"]["path"]).mkdir(parents=True, exist_ok=True)

def configure_mic(cfg):
    print_section("🎙️ Microfone")
    print("Use 'arecord -l' ou 'pactl list sources' para ver dispositivos")
    device = get_input("Device ID (Enter=padrão)", str(cfg["mic"]["device"] or ""))
    cfg["mic"]["device"] = int(device) if device.isdigit() else None
    cfg["mic"]["sample_rate"] = int(get_input("Sample rate", str(cfg["mic"]["sample_rate"])))

def configure_evolution(cfg):
    print_section("⚡ Auto-Evolução")
    cfg["evolution"]["enabled"] = input("Ativar auto-evolução de código? (S/n): ").lower() != 'n'
    if cfg["evolution"]["enabled"]:
        cfg["evolution"]["max_changes_per_hour"] = int(get_input("Máx mudanças/hora", str(cfg["evolution"]["max_changes_per_hour"])))
        cfg["evolution"]["risk_limit"] = choose_option("Limite de risco:", ["low", "medium", "high"], cfg["evolution"]["risk_limit"])
        cfg["evolution"]["git_repo_path"] = get_input("Repo Git para versionamento", cfg["evolution"]["git_repo_path"])

def configure_wake(cfg):
    print_section("🗣️ Wake Word")
    cfg["wake_word"]["enabled"] = input("Ativar wake word 'jarvis'? (S/n): ").lower() != 'n'
    if cfg["wake_word"]["enabled"]:
        cfg["wake_word"]["model"] = choose_option("Modelo whisper para wake:", ["tiny", "base", "small"], cfg["wake_word"]["model"])

def configure_telegram(cfg):
    print_section("📱 Telegram Bot (opcional)")
    enable = input("Ativar bot Telegram? (s/N): ").lower() == 's'
    cfg["telegram"]["enabled"] = enable
    if enable:
        print("   Crie bot com @BotFather no Telegram")
        cfg["telegram"]["token"] = get_input("Bot Token", cfg["telegram"]["token"], required=True)
        cfg["telegram"]["chat_id"] = get_input("Chat ID (seu user ID)", cfg["telegram"]["chat_id"], required=True)

def check_dependencies():
    print_section("🔍 Verificando Dependências")
    checks = [
        ("python3", "python3 --version"),
        ("pip", "pip --version"),
        ("ffmpeg", "ffmpeg -version"),
        ("tesseract", "tesseract --version"),
        ("ollama", "ollama --version"),
        ("docker", "docker --version"),
        ("nvidia-smi", "nvidia-smi"),
    ]
    for name, cmd in checks:
        try:
            r = subprocess.run(cmd.split(), capture_output=True, timeout=3)
            status = "✅" if r.returncode == 0 else "❌"
            version = r.stdout.decode().split('\n')[0][:50] if r.stdout else ""
            print(f"  {status} {name}: {version}")
        except:
            print(f"  ❌ {name}: não encontrado")

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              JARVIS CONFIGURATION WIZARD v1.0                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    check_dependencies()
    
    cfg = load_config()
    print(f"\n📁 Config atual: {CONFIG_FILE}")
    
    if input("\n🔄 Reconfigurar tudo? (s/N): ").lower() == 's':
        cfg = DEFAULT_CONFIG.copy()
    
    configure_stt(cfg)
    configure_llm(cfg)
    configure_tts(cfg)
    configure_vision(cfg)
    configure_memory(cfg)
    configure_mic(cfg)
    configure_evolution(cfg)
    configure_wake(cfg)
    configure_telegram(cfg)
    
    save_config(cfg)
    
    print_header("🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("\nPróximos passos:")
    print("  1. export NVIDIA_API_KEY='sua-chave'  (se usar NVIDIA)")
    print("  2. ollama serve && ollama pull qwen2.5:3b  (se usar Ollama)")
    print("  3. python main.py          # Interface gráfica")
    print("  4. python jarvis_daemon.py # Daemon voz (wake word 'jarvis')")
    print("\n📖 Documentação: ~/jarvis/README.md")

if __name__ == "__main__":
    main()
