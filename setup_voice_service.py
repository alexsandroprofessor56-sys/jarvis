#!/usr/bin/env python3
"""
Script de configuração do serviço de voz JARVIS
Configura API key NVIDIA e instala systemd service
"""
import os
import sys
import subprocess
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".jarvis"
CONFIG_FILE = CONFIG_DIR / "config.json"

NVIDIA_API_KEY = "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"

DEFAULT_CONFIG = {
    "stt": {
        "engine": "whisper",
        "model": "base",
        "language": "pt"
    },
    "llm": {
        "engine": "nvidia",
        "url": "https://integrate.api.nvidia.com/v1",
        "model": "nvidia/nemotron-3-ultra",
        "api_key": NVIDIA_API_KEY,
        "temperature": 0.7,
        "max_tokens": 4096
    },
    "tts": {
        "engine": "edge",
        "voice": "pt-BR-AntonioNeural",
        "speed": 0.8
    },
    "vision": {
        "enabled": True,
        "model": "nvidia/nemotron-3-ultra"
    },
    "memory": {
        "enabled": True,
        "max_history": 100,
        "path": str(Path.home() / "jarvis_memory")
    },
    "mic": {
        "device": None,
        "sample_rate": 16000
    },
    "evolution": {
        "enabled": True,
        "max_changes_per_hour": 999999,
        "risk_limit": "high",
        "git_repo_path": str(Path.home() / "jarvis")
    },
    "wake_word": {
        "enabled": True,
        "device": None,
        "model": "tiny"
    },
    "telegram": {
        "enabled": False,
        "token": "",
        "chat_id": "",
        "poll_interval": 2
    }
}


def setup_config():
    """Configura o arquivo de configuração com a API key NVIDIA"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    else:
        config = {}
    
    # Merge com defaults
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
        elif isinstance(value, dict):
            for k, v in value.items():
                if k not in config[key]:
                    config[key][k] = v
    
    # Garante API key
    config["llm"]["api_key"] = NVIDIA_API_KEY
    config["llm"]["engine"] = "nvidia"
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuração salva em {CONFIG_FILE}")
    print(f"   Engine LLM: {config['llm']['engine']}")
    print(f"   Modelo: {config['llm']['model']}")
    print(f"   API Key: {'*' * 20}{config['llm']['api_key'][-4:]}")


def install_systemd_service():
    """Instala o systemd service"""
    service_file = Path(__file__).parent / "jarvis-daemon.service"
    target = Path("/etc/systemd/system/jarvis-daemon.service")
    
    if not service_file.exists():
        print(f"❌ Arquivo de service não encontrado: {service_file}")
        return False
    
    try:
        # Copia para /etc/systemd/system/
        subprocess.run(["sudo", "cp", str(service_file), str(target)], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", "jarvis-daemon"], check=True)
        print(f"✅ Service instalado e habilitado: {target}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar service: {e}")
        return False


def start_service():
    """Inicia o service"""
    try:
        subprocess.run(["sudo", "systemctl", "start", "jarvis-daemon"], check=True)
        print("✅ Service iniciado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar service: {e}")
        return False


def check_status():
    """Verifica status do service"""
    try:
        result = subprocess.run(["systemctl", "status", "jarvis-daemon", "--no-pager"], capture_output=True, text=True)
        print(result.stdout)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
        return False


def test_nvidia_api():
    """Testa conexão com API NVIDIA"""
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            "https://integrate.api.nvidia.com/v1/models",
            headers=headers,
            timeout=10
        )
        if response.ok:
            models = response.json()
            print(f"✅ API NVIDIA acessível. Modelos disponíveis: {len(models.get('data', []))}")
            for m in models.get('data', [])[:5]:
                print(f"   - {m.get('id', 'unknown')}")
            return True
        else:
            print(f"❌ API NVIDIA erro: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar API NVIDIA: {e}")
        return False


def test_wake_word():
    """Testa wake word detection"""
    print("🎤 Testando wake word detection...")
    print("   Diga 'jarvis' seguido de um comando")
    print("   Pressione Ctrl+C para sair")
    
    sys.path.insert(0, str(Path(__file__).parent))
    from stt.vad_stt import VADSTT
    
    stt = VADSTT(model_name="base", language="pt")
    if not stt.available:
        print("❌ STT não disponível")
        return False
    
    try:
        while True:
            text = stt.listen_for_command(timeout=10.0)
            if text:
                print(f"✅ Detectado: '{text}'")
    except KeyboardInterrupt:
        print("\n✅ Teste encerrado")
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Setup JARVIS Voice Service")
    parser.add_argument("--config", action="store_true", help="Configurar apenas config.json")
    parser.add_argument("--install-service", action="store_true", help="Instalar systemd service")
    parser.add_argument("--start", action="store_true", help="Iniciar service")
    parser.add_argument("--status", action="store_true", help="Verificar status")
    parser.add_argument("--test-api", action="store_true", help="Testar API NVIDIA")
    parser.add_argument("--test-wake", action="store_true", help="Testar wake word")
    parser.add_argument("--all", action="store_true", help="Fazer tudo: config, install, start")
    
    args = parser.parse_args()
    
    if args.all or not any(vars(args).values()):
        # Default: faz tudo
        args.config = args.install_service = args.start = args.test_api = True
    
    if args.config:
        setup_config()
    
    if args.test_api:
        test_nvidia_api()
    
    if args.install_service:
        install_systemd_service()
    
    if args.start:
        start_service()
    
    if args.status:
        check_status()
    
    if args.test_wake:
        test_wake_word()
    
    if args.all:
        print("\n🎉 Setup completo! JARVIS Voice Service configurado e rodando.")
        print("   Use 'systemctl status jarvis-daemon' para ver status")
        print("   Logs: 'journalctl -u jarvis-daemon -f'")


if __name__ == "__main__":
    main()