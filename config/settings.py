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
        "engine": "nvidia",
        "url": "https://integrate.api.nvidia.com/v1",
        "model": "nvidia/nemotron-3-ultra",
        "api_key": "",
        "temperature": 0.7,
        "max_tokens": 4096
    },
    "tts": {
        "engine": "edge",
        "voice": "pt-BR-FranciscaNeural",
        "speed": 0.75
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
        "max_changes_per_hour": 999999,
        "risk_limit": "high",
        "git_repo_path": os.path.expanduser("~/jarvis")
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
        if not cfg.get("llm", {}).get("api_key"):
            cfg.setdefault("llm", {})["api_key"] = os.environ.get("JARVIS_NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY", "")
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
