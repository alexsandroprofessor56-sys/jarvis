import json
import os

CONFIG_DIR = os.path.expanduser("~/.jarvis")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")

DEFAULT_CONFIG = {
    "stt": {
        "engine": "whisper",
        "model": "base",
        "language": "pt"
    },
    "llm": {
        "engine": "ollama",
        "url": "http://127.0.0.1:11434",
        "model": "qwen2.5:3b"
    },
    "tts": {
        "engine": "edge",
        "voice": "pt-BR-AntonioNeural",
        "speed": 1.0
    },
    "vision": {
        "enabled": True,
        "model": "qwen2.5:3b"
    },
    "memory": {
        "enabled": True,
        "max_history": 100,
        "path": "/media/cartao_memoria/jarvis_memory"
    },
    "mic": {
        "device": None,
        "sample_rate": 16000
    },
    "evolution": {
        "enabled": True,
        "max_changes_per_hour": 5,
        "risk_limit": "medium",
        "git_repo_path": os.path.expanduser("~/jarvis")
    },
    "telegram": {
        "enabled": False,
        "token": "",
        "chat_id": "",
        "poll_interval": 2
    }
}

DEFAULT_MEMORY_DIR = os.path.join(CONFIG_DIR, "memory")


def ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(DEFAULT_MEMORY_DIR, exist_ok=True)
    custom = _load_custom_memory_path()
    if custom:
        try:
            os.makedirs(custom, exist_ok=True)
        except Exception:
            pass


def _load_custom_memory_path():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            return cfg.get("memory", {}).get("path", "")
    except Exception:
        return ""
    return ""


def get_memory_dir():
    custom = _load_custom_memory_path()
    if custom and os.path.isdir(custom):
        return custom
    return DEFAULT_MEMORY_DIR


MEMORY_DIR = get_memory_dir()


def load():
    ensure_dirs()
    if not os.path.exists(CONFIG_FILE):
        save(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save(cfg):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key, default=None):
    cfg = load()
    parts = key.split(".")
    val = cfg
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return default
        if val is None:
            return default
    return val


def set_key(key, value):
    cfg = load()
    parts = key.split(".")
    target = cfg
    for p in parts[:-1]:
        target = target.setdefault(p, {})
    target[parts[-1]] = value
    save(cfg)
