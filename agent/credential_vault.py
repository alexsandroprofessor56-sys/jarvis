"""Cofre de credenciais criptografado usando Fernet (symmetric encryption)"""
import os
import json
import base64
import stat
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


VAULT_DIR = os.path.expanduser("~/.jarvis")
VAULT_KEY_FILE = os.path.join(VAULT_DIR, ".vault_key")
VAULT_DATA_FILE = os.path.join(VAULT_DIR, "vault.json")


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def _load_or_create_key() -> bytes:
    os.makedirs(VAULT_DIR, exist_ok=True)
    if os.path.exists(VAULT_KEY_FILE):
        with open(VAULT_KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(VAULT_KEY_FILE, "wb") as f:
        f.write(key)
    os.chmod(VAULT_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    return key


def _get_cipher() -> Fernet:
    key = _load_or_create_key()
    return Fernet(key)


def _load_vault() -> dict:
    if os.path.exists(VAULT_DATA_FILE):
        with open(VAULT_DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_vault(data: dict):
    with open(VAULT_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(VAULT_DATA_FILE, stat.S_IRUSR | stat.S_IWUSR)


def credential_save(service: str, username: str, password: str, notes: str = "") -> str:
    cipher = _get_cipher()
    encrypted = cipher.encrypt(json.dumps({"username": username, "password": password, "notes": notes}).encode())
    vault = _load_vault()
    vault[service] = encrypted.decode()
    _save_vault(vault)
    return f"Credencial '{service}' salva com segurança."


def credential_get(service: str) -> dict:
    vault = _load_vault()
    encrypted = vault.get(service)
    if not encrypted:
        return {"error": f"Credencial '{service}' não encontrada."}
    cipher = _get_cipher()
    try:
        decrypted = cipher.decrypt(encrypted.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        return {"error": f"Falha ao descriptografar: {e}"}


def credential_list() -> list:
    vault = _load_vault()
    return list(vault.keys())


def credential_delete(service: str) -> str:
    vault = _load_vault()
    if service not in vault:
        return f"Credencial '{service}' não encontrada."
    del vault[service]
    _save_vault(vault)
    return f"Credencial '{service}' removida."
